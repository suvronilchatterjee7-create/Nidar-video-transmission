"""Variance field per chunk, metadata quantisation, and the temporal-DC side-information variance.

Chunk = temporal band x frequency zone (u + v) x spatial region (4 x 4 luma, 2 x 2 chroma) [P1 Table 21].
Per chunk j, measured from the source only (open loop) [P1 §5.1 E2, §D.3]:
  lambda_j = mean c^2;  a_j = regression of the chunk on the temporal-DC prediction from the previous
  ORIGINAL last frame (temporal-DC chunks only; 0 elsewhere);  omega_j = mean (c - a_j z)^2.
Metadata quantised to 1 dB (lambda, omega) and 1/32 (a): 12 bits per chunk + 5 bits per temporal-DC chunk
[P1 §D.3]. Pixel scaling x/255 - 1/2 and the 6-bit code below are implementation choices that make
"12 bits per chunk" concrete (docs/VIDEO_PIPELINE.md §2): code 0 = negligible (< -41.5 dB, modelled as
NEGLIGIBLE), codes 1..63 = -41..+21 dB in 1 dB steps (the largest possible chunk variance is ~21 dB).
Temporal-DC prediction variance [P1 Lemma 9 Eq. 41].
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from nidar.common.contracts import MetadataBlock
from nidar.video.transform import BLOCK, forward, temporal_matrix, zone_map

DB_MIN, DB_LEVELS = -42, 64          # code c >= 1 means (c + DB_MIN) dB; code 0 means negligible
NEGLIGIBLE = 1e-12                   # variance used for code 0 (keeps every formula finite)
A_LEVELS = 32                         # a in {0, 1/32, ..., 31/32}: 5 bits
N_ZONES = 2 * BLOCK - 1               # 15


@dataclass(frozen=True)
class ChunkLayout:
    """Chunk labels for the three planes of a 4:2:0 GoP (Y, U, V)."""

    G: int
    labels: tuple[np.ndarray, np.ndarray, np.ndarray]   # per plane, shape (G, H, W), int chunk index
    n_chunks: int
    is_dc: np.ndarray                                    # (n_chunks,) temporal band 0
    counts: np.ndarray                                   # coefficients per chunk

    @staticmethod
    def build(G: int, luma_hw: tuple[int, int], regions_luma: int = 4) -> "ChunkLayout":
        h, w = luma_hw
        rc = max(1, regions_luma // 2)
        if h % (2 * BLOCK) or w % (2 * BLOCK):
            raise ValueError("luma size must be a multiple of 16 so 4:2:0 chroma planes split into 8x8 blocks")
        labels, offset, is_dc, counts = [], 0, [], []
        for ph, pw, reg in ((h, w, regions_luma), (h // 2, w // 2, rc), (h // 2, w // 2, rc)):
            zones = zone_map(ph, pw)
            ry = np.minimum(np.arange(ph) * reg // ph, reg - 1)
            rx = np.minimum(np.arange(pw) * reg // pw, reg - 1)
            region = ry[:, None] * reg + rx[None, :]
            per_t = N_ZONES * reg * reg
            lab = np.empty((G, ph, pw), dtype=np.int64)
            for t in range(G):
                lab[t] = offset + t * per_t + zones * reg * reg + region
            labels.append(lab)
            is_dc += [t == 0 for t in range(G) for _ in range(per_t)]
            offset += G * per_t
        counts = np.zeros(offset, dtype=np.int64)
        for lab in labels:
            counts += np.bincount(lab.ravel(), minlength=offset)
        return ChunkLayout(G, tuple(labels), offset, np.array(is_dc), counts)

    def expand(self, per_chunk: np.ndarray) -> np.ndarray:
        """Per-coefficient array (Y, U, V flattened and concatenated) from per-chunk values."""
        return np.concatenate([per_chunk[lab.ravel()] for lab in self.labels])

    def flat_labels(self) -> np.ndarray:
        return np.concatenate([lab.ravel() for lab in self.labels])

    def rank_in_chunk(self) -> np.ndarray:
        """Position of each coefficient among its chunk's coefficients, in flat order."""
        lab = self.flat_labels()
        order = np.argsort(lab, kind="stable")
        starts = np.concatenate([[0], np.cumsum(self.counts)[:-1]])
        rank = np.empty(lab.size, dtype=np.int64)
        rank[order] = np.arange(lab.size) - np.repeat(starts, self.counts)
        return rank


def dc_side_information(prev_last_planes: list[np.ndarray] | None, G: int, temporal: str,
                        layout: ChunkLayout) -> np.ndarray:
    """z placed in the temporal-DC band: the coefficient of a GoP that repeats the previous last frame
    G times, i.e. sqrt(G) x DCT2(x_last) for an orthonormal temporal transform (zero elsewhere)
    [P1 §D.3; the paper's 'G DCT2(x_last)' read with the orthonormal scaling]."""
    total = sum(lab.size for lab in layout.labels)
    if prev_last_planes is None:
        return np.zeros(total)
    parts = []
    for plane in prev_last_planes:
        rep = np.repeat(np.asarray(plane, dtype=float)[None], G, axis=0)
        parts.append(forward(rep, temporal).ravel())
    z = np.concatenate(parts)
    dc_mask = layout.expand(layout.is_dc.astype(float)) > 0
    return np.where(dc_mask, z, 0.0)


def estimate(coeffs: np.ndarray, z_orig: np.ndarray, layout: ChunkLayout) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(lambda, omega, a) per chunk from source coefficients (flattened, layout order) [P1 §5.1 E2]."""
    lab = layout.flat_labels()
    n = layout.n_chunks
    cnt = layout.counts.astype(float)
    lam = np.bincount(lab, coeffs * coeffs, n) / cnt
    zz = np.bincount(lab, z_orig * z_orig, n)
    cz = np.bincount(lab, coeffs * z_orig, n)
    a = np.where(layout.is_dc & (zz > 0), np.clip(cz / np.where(zz > 0, zz, 1.0), 0.0, 1.0), 0.0)
    resid = coeffs - layout.expand(a) * z_orig
    omega = np.bincount(lab, resid * resid, n) / cnt
    return lam, np.minimum(omega, lam), a


def quantise_metadata(lam: np.ndarray, omega: np.ndarray, a: np.ndarray, is_dc: np.ndarray) -> MetadataBlock:
    def q_db(x: np.ndarray) -> np.ndarray:
        db = np.round(10.0 * np.log10(np.maximum(x, 1e-30)))
        code = np.clip(db - DB_MIN, 0, DB_LEVELS - 1).astype(np.int64)
        return np.where(db - DB_MIN < 1, 0, code)

    lq = q_db(lam)
    oq = np.minimum(q_db(omega), lq)
    aq = np.where(is_dc, np.clip(np.round(a * A_LEVELS), 0, A_LEVELS - 1), 0).astype(np.int64)
    return MetadataBlock(chunk_count=len(lam), lam_db_q=lq, omega_db_q=oq, a_q=aq)


def dequantise_metadata(meta: MetadataBlock) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lam = np.where(meta.lam_db_q > 0, 10.0 ** ((meta.lam_db_q + DB_MIN) / 10.0), NEGLIGIBLE)
    omega = np.where(meta.omega_db_q > 0, 10.0 ** ((meta.omega_db_q + DB_MIN) / 10.0), NEGLIGIBLE)
    omega = np.minimum(omega, lam)
    return lam, omega, meta.a_q / A_LEVELS


def metadata_bits(meta: MetadataBlock, is_dc: np.ndarray) -> int:
    """12 bits per chunk + 5 per temporal-DC chunk [P1 §D.3]."""
    return 12 * meta.chunk_count + 5 * int(np.count_nonzero(is_dc))


def pack_metadata(meta: MetadataBlock, is_dc: np.ndarray) -> bytes:
    bits = []
    for j in range(meta.chunk_count):
        bits.append(format(int(meta.lam_db_q[j]), "06b") + format(int(meta.omega_db_q[j]), "06b"))
        if is_dc[j]:
            bits.append(format(int(meta.a_q[j]), "05b"))
    s = "".join(bits)
    s += "0" * (-len(s) % 8)
    return int(s, 2).to_bytes(len(s) // 8, "big") if s else b""


def unpack_metadata(data: bytes, n_chunks: int, is_dc: np.ndarray) -> tuple[MetadataBlock, int]:
    """Returns the block and the number of bytes consumed."""
    nbits = 12 * n_chunks + 5 * int(np.count_nonzero(is_dc))
    nbytes = (nbits + 7) // 8
    s = format(int.from_bytes(data[:nbytes], "big"), f"0{nbytes * 8}b")
    lq, oq, aq, p = [], [], [], 0
    for j in range(n_chunks):
        lq.append(int(s[p:p + 6], 2))
        oq.append(int(s[p + 6:p + 12], 2))
        p += 12
        if is_dc[j]:
            aq.append(int(s[p:p + 5], 2))
            p += 5
        else:
            aq.append(0)
    return MetadataBlock(n_chunks, np.array(lq), np.array(oq), np.array(aq)), nbytes


def last_frame_weights(G: int, temporal: str) -> np.ndarray:
    """w_t: weight of temporal coefficient t in the last frame (last row of the inverse transform),
    sum w_t^2 = 1 [P1 Lemma 9]."""
    return temporal_matrix(G, temporal).T[-1]


def side_info_variance_dc(omega: np.ndarray, a: np.ndarray, w: np.ndarray, d_prev_bands: np.ndarray,
                          G: int) -> np.ndarray:
    """mu_{0,j}(g) = omega_j + a_j^2 G sum_t w_t^2 D_{t,j}(g-1) [P1 Lemma 9 Eq. 41]; ``d_prev_bands`` has
    shape (G, ...) with the previous GoP's distortion of each temporal band in the same zone/region."""
    return omega + a * a * G * np.tensordot(w * w, d_prev_bands, axes=(0, 0))
