"""Hybrid decoder pipeline D1-D5 for one GoP [P1 §5.1].

D1 channel estimation from pilots (MMSE, [P1 §C.1]) and zero-forcing equalisation; per-dimension noise
   includes the estimation-error term sigma_e^2 |s|^2 [P1 Prop. 16] and clipping distortion [P1 §B.1].
D2 floor: delivered (code abstraction, OQ-23) -> CRC [Rem. 7] -> theta_F, metadata, entropy decode.
D3 side information z = a * sqrt(G) DCT2(prediction of the last frame) in the temporal-DC band [P1 §D.3]:
   "zero" = previous reconstruction (pilot); "block" = decoder-side block motion compensation guided by the
   decoded floor, no motion vectors sent [P1 §5.1 D3, Table 13 ph. 3]. Variance by Lemma 9 Eq. 41.
D4 conditional mean [P1 Prop. 9 Eq. 20]; fallback to the floor reconstruction on detected mismatch
   [P1 Rem. 5] (test: normalised innovation of the analogue observations vs a threshold, OQ-32).
D5 inverse transform; distortion state for the next GoP [P1 Lemma 3].
Floor lost: the metadata (and so the gains and the analogue layer) is lost with it. The decoder holds the
last good reconstruction and reports floor_ok = False (OQ-24 decides what the GCS shows).
"""
from __future__ import annotations

import struct
import time
from dataclasses import dataclass, field

import numpy as np

from nidar.common.contracts import ProcessResult, VideoQualityReport, run_isolated
from nidar.video import gop_model, variance_field
from nidar.video.config import VideoLinkConfig
from nidar.video.decoder import conditional_mean, posterior_after_floor
from nidar.video.encoder import from_signal
from nidar.video.floor import crc, entropy, quantiser
from nidar.video.floor.designer import reference_rate_bits, water_level_for_distortion
from nidar.video.refinement import spreader
from nidar.video.transform import inverse

T_MIN_EQUIV_MBPS = 2.0     # the credited bits per sample are 2 Mbps-equivalent by definition [P1 §D.2]
MOTION_RADIUS = 16         # search range in luma pixels (decoder-side search, no vectors sent)


@dataclass(frozen=True)
class ReceivedGop:
    """What the radio delivers for one GoP (built by the channel simulator, later by the SDR front end)."""

    gop_index: int
    sent: bool
    floor_delivered: bool
    floor_block: bytes
    n_floor: int
    analog_rx: np.ndarray          # complex received analogue uses
    analog_block: np.ndarray       # fading block index of each analogue use
    pilot_rx: np.ndarray           # (L, N_p) complex received pilots (pilot symbol = 1); empty for AWGN
    noise_var: float               # complex noise variance nu_c (measured by the receiver)


@dataclass
class DecodedGop:
    frames: list[tuple[np.ndarray, np.ndarray, np.ndarray]]
    floor_only_frames: list[tuple[np.ndarray, np.ndarray, np.ndarray]] | None
    report: VideoQualityReport
    model_mse: float | None        # predicted per-sample MSE (mean D) in the signal domain
    decode_seconds: float
    extras: dict = field(default_factory=dict)


def block_motion_compensate(prev: np.ndarray, guide: np.ndarray, block: int,
                            radius: int) -> tuple[np.ndarray, np.ndarray]:
    """Full-search block matching of ``guide`` blocks in ``prev`` (SAD), returns (prediction, vectors)."""
    h, w = prev.shape
    nby, nbx = h // block, w // block
    pad = np.pad(prev, radius, mode="edge")
    best = np.full((nby, nbx), np.inf)
    vecs = np.zeros((nby, nbx, 2), dtype=np.int64)
    for dy in range(-radius, radius + 1):              # vectorised over blocks: one full-frame SAD per shift
        for dx in range(-radius, radius + 1):
            shifted = pad[radius + dy:radius + dy + h, radius + dx:radius + dx + w]
            sad = np.abs(shifted - guide).reshape(nby, block, nbx, block).sum(axis=(1, 3))
            sad = sad + 1e-9 * (dy * dy + dx * dx)     # prefer small vectors on ties
            better = sad < best
            best = np.where(better, sad, best)
            vecs[better] = (dy, dx)
    pred = np.empty_like(prev)
    for by in range(nby):
        for bx in range(nbx):
            dy, dx = (int(v) for v in vecs[by, bx])
            y0, x0 = by * block, bx * block
            pred[y0:y0 + block, x0:x0 + block] = pad[y0 + radius + dy:y0 + radius + dy + block,
                                                     x0 + radius + dx:x0 + radius + dx + block]
    return pred, vecs


def _apply_vectors(prev: np.ndarray, vecs: np.ndarray, block: int) -> np.ndarray:
    """Chroma prediction from luma vectors halved (4:2:0)."""
    h, w = prev.shape
    r = int(np.abs(vecs).max()) + 1 if vecs.size else 1
    pad = np.pad(prev, r, mode="edge")
    out = np.empty_like(prev)
    for by in range(h // block):
        for bx in range(w // block):
            v = vecs[min(by * 2, vecs.shape[0] - 1), min(bx * 2, vecs.shape[1] - 1)]
            dy, dx = (int(np.round(c / 2)) for c in v)
            y0, x0 = by * block, bx * block
            out[y0:y0 + block, x0:x0 + block] = pad[y0 + r + dy:y0 + r + dy + block,
                                                    x0 + r + dx:x0 + r + dx + block]
    return out


class HybridDecoder:
    """Implements ``VideoDecoder`` (docs/INTERFACES.md §7)."""

    def __init__(self, cfg: VideoLinkConfig, drone_id: int = 1) -> None:
        self.cfg = cfg
        self.drone_id = drone_id
        self.layout = variance_field.ChunkLayout.build(cfg.G, cfg.luma_hw, cfg.regions_luma)
        self.prev_recon: list[np.ndarray] | None = None        # last frame of the previous reconstruction
        self.prev_frames: list[tuple[np.ndarray, np.ndarray, np.ndarray]] | None = None
        self.prev_d_chunk: np.ndarray | None = None             # previous GoP distortion per chunk
        self.failures = 0
        self.gops = 0
        self.w_last = variance_field.last_frame_weights(cfg.G, cfg.temporal)

    # ---------- helpers ----------
    def _planes_from_coeffs(self, c: np.ndarray) -> list[np.ndarray]:
        out, pos = [], 0
        for lab in self.layout.labels:
            n = lab.size
            out.append(inverse(c[pos:pos + n].reshape(lab.shape), self.cfg.temporal))
            pos += n
        return out

    def _frames(self, planes: list[np.ndarray]) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
        return [tuple(from_signal(p[t]) for p in planes) for t in range(self.cfg.G)]

    def _side_information(self, c_floor: np.ndarray, floor_ok: bool) -> tuple[np.ndarray, dict]:
        cfg, lay = self.cfg, self.layout
        if self.prev_recon is None:
            return np.zeros(sum(lab.size for lab in lay.labels)), {"motion": "none"}
        prev = self.prev_recon
        info = {"motion": cfg.motion_search}
        if cfg.motion_search == "block" and floor_ok:
            guide = self._planes_from_coeffs(c_floor)
            dc_y = guide[0].mean(axis=0)          # floor-only temporal mean of the current GoP (luma)
            pred_y, vecs = block_motion_compensate(prev[0], dc_y, 8, MOTION_RADIUS)
            prev = [pred_y, _apply_vectors(prev[1], vecs, 8), _apply_vectors(prev[2], vecs, 8)]
            info["mean_abs_vector"] = float(np.abs(vecs).mean())
        elif cfg.motion_search not in ("zero", "block"):
            raise ValueError(f"motion_search must be 'zero' or 'block', got {cfg.motion_search!r}")
        return variance_field.dc_side_information(prev, cfg.G, cfg.temporal, lay), info

    def _mu(self, lam_c: np.ndarray, omega_c: np.ndarray, a_c: np.ndarray) -> np.ndarray:
        """Per-chunk side-information variance: Lemma 9 Eq. 41 on DC chunks, lambda elsewhere / first GoP."""
        lay = self.layout
        mu = lam_c.copy()
        if self.prev_d_chunk is None:
            return mu
        per_t = {}
        offset = 0
        for lab in lay.labels:                      # chunk index = offset + t * per_t + local
            n_plane_chunks = int(lab.max()) + 1 - offset
            per_t[offset] = n_plane_chunks // self.cfg.G
            offset += n_plane_chunks
        offset = 0
        for _ in lay.labels:
            pt = per_t[offset]
            dc = np.arange(offset, offset + pt)
            bands = np.stack([self.prev_d_chunk[dc + t * pt] for t in range(self.cfg.G)])
            mu[dc] = variance_field.side_info_variance_dc(omega_c[dc], a_c[dc], self.w_last, bands, self.cfg.G)
            offset += pt * self.cfg.G
        return mu

    def _hold(self, rx: ReceivedGop, t0: float, reason: str) -> DecodedGop:
        self.failures += 1
        self.gops += 1
        h, w = self.cfg.luma_hw
        grey = (np.full((h, w), 128, np.uint8), np.full((h // 2, w // 2), 128, np.uint8),
                np.full((h // 2, w // 2), 128, np.uint8))
        frames = [self.prev_frames[-1]] * self.cfg.G if self.prev_frames else [grey] * self.cfg.G
        rep = VideoQualityReport(self.drone_id, rx.gop_index, False, 0.0, 1.0, False, reason, 0.0, 0,
                                 self.failures, 0.0)
        return DecodedGop(frames, None, rep, None, time.perf_counter() - t0, {"held": True})

    # ---------- main ----------
    def decode_gop(self, rx: ReceivedGop, eps_f: float = 0.0) -> DecodedGop:
        t0 = time.perf_counter()
        cfg, lay = self.cfg, self.layout
        if not rx.sent:
            return self._hold(rx, t0, "infeasible: no floor fits (OQ-24)")
        ok, body = (False, b"")
        if rx.floor_delivered:                                                 # D2
            ok, body = crc.check_crc(rx.floor_block, cfg.crc_bits)
        if not ok:
            return self._hold(rx, t0, "floor lost")
        theta_f = struct.unpack(">d", body[:8])[0]
        meta, used = variance_field.unpack_metadata(body[8:], lay.n_chunks, lay.is_dc)
        lam_c, omega_c, a_c = variance_field.dequantise_metadata(meta)
        lab = lay.flat_labels()
        steps_chunk = quantiser.step_sizes(lam_c, theta_f)
        coded = np.isfinite(steps_chunk[lab])
        idx = entropy.decode(body[8 + used:], lab[coded], lam_c, steps_chunk)
        des = gop_model.design(cfg, lay, lam_c, omega_c, a_c, theta_f, rx.n_floor)
        c_floor = np.zeros(lab.size)
        c_floor[coded] = quantiser.floor_estimate(quantiser.dequantise(idx, steps_chunk[lab][coded]),
                                                  des.lam[coded], theta_f)
        # D1: estimation + equalisation of the analogue uses
        act = des.active_index
        y = np.zeros(lab.size)
        nu = np.ones(lab.size)
        if act.size and rx.analog_rx.size:
            nu_c = rx.noise_var
            if rx.pilot_rx.size:
                n_p = rx.pilot_rx.shape[1]
                h_hat = rx.pilot_rx.sum(axis=1) / (n_p + nu_c)                     # MMSE, pilot symbol 1
                s_e2 = nu_c / (n_p + nu_c)                                       # = 1/(1 + N_p gamma) [P1 §C.1]
                hu = h_hat[rx.analog_block]
            else:
                hu, s_e2 = np.ones(rx.analog_rx.size, complex), 0.0
            p_use = des.analog_energy / max(des.n_analog, 1)
            eq = rx.analog_rx / hu / des.alpha
            nd = (nu_c / 2.0 + s_e2 * p_use / 2.0 + des.clip_dist * p_use / 2.0) / (np.abs(hu) ** 2 * des.alpha**2)
            real = spreader.to_real(eq, 2 * eq.size)
            nd_real = np.repeat(nd, 2)
            n_vals = act.size
            n_pad = spreader.padded_length(n_vals, cfg.spreading)
            real = np.concatenate([real, np.zeros(max(0, n_pad - real.size))])[:n_pad]
            nd_real = np.concatenate([nd_real, np.full(max(0, n_pad - nd_real.size), nd_real.mean())])[:n_pad]
            y[act] = spreader.despread(real, cfg.spreading, n_vals)
            nu[act] = spreader.despread_noise(nd_real, cfg.spreading, n_vals)
        g = np.sqrt(des.x)
        # D3: side information
        z_raw, si_info = self._side_information(c_floor, True)
        mu_c = self._mu(lam_c, omega_c, a_c)
        mu = lay.expand(mu_c)
        z = des.a * z_raw
        # D4: conditional mean, with the Rem. 5 mismatch test
        c_hat, d = conditional_mean(z, c_floor, y, g, nu, mu, theta_f, des.lam)
        fallback = False
        if cfg.mismatch_threshold is not None and act.size:
            kappa = posterior_after_floor(mu, theta_f, des.lam)
            prior_c = kappa * (z / mu + np.where(des.coded, c_floor / theta_f, 0.0))
            innov = y[act] - g[act] * (prior_c[act] - c_floor[act])
            ratio = innov**2 / (g[act] ** 2 * kappa[act] + nu[act])
            uses_si = des.a[act] > 0               # side information only enters the temporal-DC band
            nis_all = float(np.mean(ratio))
            nis_si = float(np.mean(ratio[uses_si])) if uses_si.any() else 0.0
            nis = max(nis_all, nis_si)               # a corrupt prediction must not be diluted by other bands
            si_info.update({"nis": nis, "nis_all": nis_all, "nis_si": nis_si})
            if nis > cfg.mismatch_threshold:
                fallback = True
                c_hat, d = c_floor.copy(), np.minimum(des.lam, theta_f)
        # D5
        planes = self._planes_from_coeffs(c_hat)
        floor_planes = self._planes_from_coeffs(c_floor)
        frames, floor_frames = self._frames(planes), self._frames(floor_planes)
        self.prev_recon = [p[-1] for p in planes]
        self.prev_frames = frames
        self.prev_d_chunk = np.bincount(lab, d, lay.n_chunks) / lay.counts
        self.gops += 1
        d_chunk = self.prev_d_chunk
        theta_ref = water_level_for_distortion(float(d.mean()), lam_c, lay.counts)
        r_ref = reference_rate_bits(theta_ref, lam_c, omega_c, a_c, lay.counts)
        teq = r_ref / (cfg.credited_bits_per_sample * cfg.samples_per_gop()) * T_MIN_EQUIV_MBPS
        inactive = ~des.active
        beta = float(d[inactive].sum() / d.sum()) if d.sum() > 0 else 0.0
        rep = VideoQualityReport(self.drone_id, rx.gop_index, True, teq, beta, fallback,
                                 f"n_F={rx.n_floor}", 0.0, 0, self.failures, eps_f * self.gops)
        return DecodedGop(frames, floor_frames, rep, float(d.mean()), time.perf_counter() - t0,
                          {"theta_f": theta_f, "active": int(act.size), "coded": int(coded.sum()),
                           "d_chunk_mean": float(d_chunk.mean()), **si_info})

    def decode(self, rx_symbols: ReceivedGop, plan=None) -> ProcessResult:    # VideoDecoder protocol
        return run_isolated("video.decoder", "decode_gop", lambda: self.decode_gop(rx_symbols),
                            gop_index=getattr(rx_symbols, "gop_index", None))
