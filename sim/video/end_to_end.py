"""End-to-end simulation of the Paper 1 video link: encoder -> block-fading channel -> decoder.

Channel per GoP: L independent Rayleigh blocks (or AWGN with L = 0), unit transmit power per data use,
complex noise nu_c = 10^(-SNR/10); N_p unit pilots per block; uses interleaved across blocks [P1 §6.1, §C.1].
Floor delivery by the ideal-outage abstraction (real code: OQ-23). Telemetry uses are reserved and not
simulated here. Measures PSNR of the full and floor-only reconstructions, the model prediction (H1, H2 of
[P1 §D.1]), T_eq, beta_up, floor share, and encode/decode time (latency, VT-20).
[P1 Table 13 phases 1-2] [USER-PROMPT §6.1 D9]
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from nidar.video.config import VideoLinkConfig
from nidar.video.encoder import EncodedGop, HybridEncoder
from nidar.video.receiver import HybridDecoder, ReceivedGop
from sim.video.test_video import Frame, psnr


def transmit(enc: EncodedGop, cfg: VideoLinkConfig, code, snr_db: float, gains: np.ndarray | None,
             rng: np.random.Generator) -> ReceivedGop:
    nu_c = 10.0 ** (-snr_db / 10.0)
    if not enc.feasible:
        return ReceivedGop(enc.gop_index, False, False, b"", enc.n_floor, np.zeros(0, complex), np.zeros(0, int),
                           np.zeros((0, 0), complex), nu_c)
    L = cfg.fading_blocks

    def noise(n: int) -> np.ndarray:
        return (rng.standard_normal(n) + 1j * rng.standard_normal(n)) * np.sqrt(nu_c / 2.0)

    if L == 0:
        h = np.ones(1, complex)
        floor_block = np.zeros(enc.n_floor, int)
        analog_block = np.zeros(enc.n_analog, int)
        pilots = np.zeros((0, 0), complex)
    else:
        h = gains if gains is not None else (rng.standard_normal(L) + 1j * rng.standard_normal(L)) * np.sqrt(0.5)
        floor_block = np.arange(enc.n_floor) % L
        analog_block = (enc.n_floor + np.arange(enc.n_analog)) % L
        n_p = cfg.pilots_per_block
        pilots = h[:, None] * np.ones((L, n_p)) + noise(L * n_p).reshape(L, n_p)
    floor_snr = np.abs(h[floor_block]) ** 2 * cfg.floor_power_ratio / nu_c
    delivered = code.delivered(enc.floor_payload_bits, floor_snr)
    rx = h[analog_block] * enc.analog_uses + noise(enc.n_analog)
    return ReceivedGop(enc.gop_index, True, delivered, enc.floor_block if delivered else b"", enc.n_floor, rx,
                       analog_block, pilots, nu_c)


@dataclass
class GopResult:
    gop_index: int
    snr_db: float
    floor_ok: bool
    psnr_db: float
    floor_only_psnr_db: float | None
    model_psnr_db: float | None
    teq_equiv_mbps: float
    beta_up: float
    floor_share: float
    fallback: bool
    encode_s: float
    decode_s: float
    extras: dict


def run(cfg: VideoLinkConfig, frames: list[Frame], snr_db: float | list[float], seed: int = 0,
        gains_per_gop: np.ndarray | None = None) -> list[GopResult]:
    """Run consecutive GoPs. ``snr_db`` may be a per-GoP list (e.g. from sim.channel.snr_process)."""
    enc, dec = HybridEncoder(cfg), HybridDecoder(cfg)
    rng = np.random.default_rng(seed)
    n_gops = len(frames) // cfg.G
    snrs = [snr_db] * n_gops if np.isscalar(snr_db) else list(snr_db)
    out = []
    for g in range(n_gops):
        gop = frames[g * cfg.G:(g + 1) * cfg.G]
        e = enc.encode_gop(gop)
        gains = None if gains_per_gop is None else gains_per_gop[g]
        rx = transmit(e, cfg, enc.code, snrs[g], gains, rng)
        d = dec.decode_gop(rx)
        out.append(GopResult(
            g, snrs[g], d.report.floor_ok, psnr(gop, d.frames),
            psnr(gop, d.floor_only_frames) if d.floor_only_frames else None,
            None if d.model_mse is None else -10 * np.log10(d.model_mse),
            d.report.teq_model_mbps, d.report.beta_up, e.n_floor / cfg.channel_uses(),
            d.report.fallback_floor_only, e.encode_seconds, d.decode_seconds, d.extras))
    return out
