"""Hybrid encoder, one GoP at a time: E1-E7 [P1 §5.1].

E1 transform (Def. 4) -> E2 variance field + metadata (A3, A5, §D.3) -> E3 water level (Def. 7)
-> E4 quantise F, static-model entropy code, metadata, CRC; nothing from earlier GoPs (Prop. 7)
-> E5 residual -> E6 gains (Prop. 8, open loop, gop_model) -> E7 orthogonal spreading, map to n_A uses,
optional hard limiter (Lemma 6). The only cross-GoP state is the previous ORIGINAL last frame used to
measure a_j (open loop, [P1 §D.3]); it never enters the floor.
"""
from __future__ import annotations

import struct
import time
from dataclasses import dataclass

import numpy as np

from nidar.common.contracts import ProcessResult, run_isolated
from nidar.video import gop_model, variance_field
from nidar.video.config import VideoLinkConfig
from nidar.video.floor import crc, entropy, quantiser
from nidar.video.floor.code import FloorCode, IdealOutageFloorCode
from nidar.video.refinement import spreader
from nidar.video.transform import forward

PIXEL_SCALE = 255.0


def to_signal(plane_u8: np.ndarray) -> np.ndarray:
    """Pixels -> zero-mean signal x/255 - 1/2 (choice documented in variance_field)."""
    return np.asarray(plane_u8, dtype=float) / PIXEL_SCALE - 0.5


def from_signal(x: np.ndarray) -> np.ndarray:
    return np.clip(np.rint((np.asarray(x) + 0.5) * PIXEL_SCALE), 0, 255).astype(np.uint8)


@dataclass(frozen=True)
class EncodedGop:
    gop_index: int
    feasible: bool                 # False: no floor fits the GoP (OQ-24); nothing is sent
    floor_block: bytes             # metadata + entropy-coded floor + CRC
    floor_payload_bits: int
    n_floor: int
    analog_uses: np.ndarray        # complex, length n_analog
    n_analog: int
    encode_seconds: float


def gop_planes(frames: list[tuple[np.ndarray, np.ndarray, np.ndarray]]) -> list[np.ndarray]:
    """[(Y, U, V)] * G -> [Y(G,H,W), U(G,H/2,W/2), V(...)] as signals."""
    return [np.stack([to_signal(f[p]) for f in frames]) for p in range(3)]


class HybridEncoder:
    """Implements ``VideoEncoder`` (docs/INTERFACES.md §7)."""

    def __init__(self, cfg: VideoLinkConfig, floor_code: FloorCode | None = None) -> None:
        self.cfg = cfg
        self.layout = variance_field.ChunkLayout.build(cfg.G, cfg.luma_hw, cfg.regions_luma)
        self.code = floor_code or IdealOutageFloorCode(cfg.floor_rate_bits_per_use)
        self.prev_last_original: list[np.ndarray] | None = None
        self.gop_index = 0

    def encode_gop(self, frames: list[tuple[np.ndarray, np.ndarray, np.ndarray]]) -> EncodedGop:
        t0 = time.perf_counter()
        cfg, layout = self.cfg, self.layout
        if len(frames) != cfg.G:
            raise ValueError(f"GoP needs {cfg.G} frames, got {len(frames)}")
        planes = gop_planes(frames)
        coeffs = np.concatenate([forward(p, cfg.temporal).ravel() for p in planes])          # E1
        z_orig = variance_field.dc_side_information(self.prev_last_original, cfg.G, cfg.temporal, layout)
        lam, omega, a = variance_field.estimate(coeffs, z_orig, layout)                         # E2
        meta = variance_field.quantise_metadata(lam, omega, a, layout.is_dc)
        lam_q, omega_q, a_q = variance_field.dequantise_metadata(meta)
        theta_f = gop_model.water_level_for(cfg, layout, lam_q, omega_q, a_q)                  # E3
        lab = layout.flat_labels()
        steps_chunk = quantiser.step_sizes(lam_q, theta_f)
        coded = np.isfinite(steps_chunk[lab])
        idx = quantiser.quantise(coeffs[coded], steps_chunk[lab][coded])                      # E4
        body = (variance_field.pack_metadata(meta, layout.is_dc)
                + entropy.encode(idx, lab[coded], lam_q, steps_chunk))
        # theta_F travels as 8 raw bytes so both ends build bit-identical entropy models (a recomputed float
        # could differ in the last ulp on another CPU and desynchronise the arithmetic decoder).
        block = crc.append_crc(struct.pack(">d", theta_f) + body, cfg.crc_bits)
        payload_bits = 8 * len(block)
        n_floor = self.code.uses_for(payload_bits)
        self.prev_last_original = [p[-1] for p in planes]
        self.gop_index += 1
        n_avail = cfg.channel_uses() - cfg.n_telemetry - cfg.fading_blocks * cfg.pilots_per_block
        if n_floor > n_avail:
            return EncodedGop(self.gop_index - 1, False, b"", payload_bits, n_floor, np.zeros(0, complex), 0,
                              time.perf_counter() - t0)
        des = gop_model.design(cfg, layout, lam_q, omega_q, a_q, theta_f, n_floor)            # E6
        c_floor = np.zeros_like(coeffs)
        c_floor[coded] = quantiser.floor_estimate(quantiser.dequantise(idx, steps_chunk[lab][coded]),
                                                  des.lam[coded], theta_f)
        resid = coeffs - c_floor                                                               # E5
        act = des.active_index
        values = np.sqrt(des.x[act]) * resid[act]
        uses = spreader.to_complex(spreader.spread(values, cfg.spreading))                     # E7
        uses = np.concatenate([uses, np.zeros(max(0, des.n_analog - uses.size), complex)])[: des.n_analog]
        if cfg.limiter_backoff_db is not None and uses.size:                                  # [P1 Lemma 6]
            amp = np.sqrt(10.0 ** (cfg.limiter_backoff_db / 10.0) * des.analog_energy / des.n_analog)
            mag = np.abs(uses)
            uses = np.where(mag > amp, amp * uses / np.maximum(mag, 1e-300), uses)
        return EncodedGop(self.gop_index - 1, True, block, payload_bits, n_floor, uses, des.n_analog,
                          time.perf_counter() - t0)

    def encode(self, frames, plan=None, design=None) -> ProcessResult:   # VideoEncoder protocol
        return run_isolated("video.encoder", "encode_gop", lambda: self.encode_gop(frames), gop_index=self.gop_index)
