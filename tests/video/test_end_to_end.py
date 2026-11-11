"""End-to-end Paper 1 link on test video: H1 (floor holds), H2 (model ~ measurement), graceful degradation,
floor loss handling, Rem. 5 fallback (CT-13), fading + pilots, GCS video service, loopback radio, H5 vs
H.264. [P1 §D.1, §5.1, Rem. 5, Table 13 ph. 1-2] Results are on synthetic video, not our camera (OQ-12)."""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from nidar.gcs.services.video_service import VideoService, yuv420_to_rgb
from nidar.link.radio import LoopbackRadio
from nidar.video.config import paper_pilot_profile
from nidar.video.encoder import HybridEncoder
from nidar.video.receiver import HybridDecoder
from sim.video.end_to_end import run, transmit
from sim.video.test_video import ffmpeg_available, ffmpeg_source, moving_scene, psnr

HW = (176, 320)


@pytest.fixture(scope="module")
def frames():
    return moving_scene(*HW, 32, seed=1)


@pytest.fixture(scope="module")
def sweep(frames):
    return {snr: run(paper_pilot_profile(HW, snr_db=snr), frames, snr, seed=0) for snr in (4, 8, 12)}


def test_h1_full_reconstruction_never_below_floor_only(sweep) -> None:
    for res in sweep.values():
        for r in res:
            assert r.floor_ok
            assert r.psnr_db >= r.floor_only_psnr_db - 0.05


def test_h2_model_predicts_measured_quality(sweep) -> None:
    """Paper: within 0.4 dB on its clip. We measured up to ~0.6 dB at 288x352; tolerance 1.0 dB."""
    for res in sweep.values():
        gap = np.mean([r.model_psnr_db - r.psnr_db for r in res])
        assert abs(gap) < 1.0


def test_graceful_degradation_with_snr(sweep) -> None:
    mean = {s: np.mean([r.psnr_db for r in res]) for s, res in sweep.items()}
    assert mean[4] < mean[8] < mean[12]
    teq = {s: np.mean([r.teq_equiv_mbps for r in res]) for s, res in sweep.items()}
    assert teq[4] >= 2.0 - 1e-6 and teq[4] < teq[8] < teq[12]            # floor credited 2 Mbps-eq


def test_floor_loss_holds_last_picture_and_counts(frames) -> None:
    cfg = paper_pilot_profile(HW, snr_db=10)
    res = run(cfg, frames, [10, -5, -5, 10], seed=0)        # floor cannot be delivered at -5 dB
    assert [r.floor_ok for r in res] == [True, False, False, True]
    assert res[1].floor_only_psnr_db is None and res[1].psnr_db < res[0].psnr_db


def test_infeasible_floor_is_reported_not_sent(frames) -> None:
    cfg = dataclasses.replace(paper_pilot_profile(HW, snr_db=10), symbol_rate_hz=1e4)
    enc = HybridEncoder(cfg)
    e = enc.encode_gop(frames[:8])
    assert not e.feasible
    d = HybridDecoder(cfg).decode_gop(transmit(e, cfg, enc.code, 10, None, np.random.default_rng(0)))
    assert not d.report.floor_ok and "OQ-24" in d.report.design_id


def test_ct13_fallback_to_floor_on_mismatch(frames) -> None:
    """Corrupt the decoder's side information; the normalised-innovation test must fall back to the floor."""
    cfg = dataclasses.replace(paper_pilot_profile(HW, snr_db=10), mismatch_threshold=3.0)
    enc, dec = HybridEncoder(cfg), HybridDecoder(cfg)
    rng = np.random.default_rng(0)
    for g in range(2):
        gop = frames[8 * g:8 * g + 8]
        rx = transmit(enc.encode_gop(gop), cfg, enc.code, 10, None, rng)
        if g == 1:
            dec.prev_recon = [p + rng.normal(0, 0.3, p.shape) for p in dec.prev_recon]
        out = dec.decode_gop(rx)
    assert out.report.fallback_floor_only and out.extras["nis"] > 3.0
    assert psnr(gop, out.frames) == pytest.approx(psnr(gop, out.floor_only_frames), abs=1e-9)


def test_block_fading_with_pilots_runs(frames) -> None:
    from nidar.video.certificates.outage import outage_rate
    cfg = dataclasses.replace(paper_pilot_profile(HW, snr_db=10, fading_blocks=8),
                              floor_rate_bits_per_use=outage_rate(8, 10, 1e-2))
    res = run(cfg, frames, 10, seed=3)
    ok = [r for r in res if r.floor_ok]
    assert ok and all(r.psnr_db >= r.floor_only_psnr_db - 0.05 for r in ok)


def test_limiter_path(frames) -> None:
    res = run(dataclasses.replace(paper_pilot_profile(HW, snr_db=10), limiter_backoff_db=4.4), frames[:16], 10)
    assert all(r.floor_ok and r.psnr_db >= r.floor_only_psnr_db - 0.05 for r in res)


def test_video_service_and_rgb(frames) -> None:
    grey = yuv420_to_rgb(np.full((4, 4), 128, np.uint8), np.full((2, 2), 128, np.uint8), np.full((2, 2), 128, np.uint8))
    assert np.all(grey == 128)
    svc = VideoService()
    cfg = paper_pilot_profile(HW, snr_db=10)
    enc, dec = HybridEncoder(cfg), HybridDecoder(cfg, drone_id=2)
    d = dec.decode_gop(transmit(enc.encode_gop(frames[:8]), cfg, enc.code, 10, None, np.random.default_rng(0)))
    svc.source(2).push(d.frames[-1], d.report.gop_index, 0.0, d.report, t_received=1.0)
    frame, rep = svc.source(2).latest()
    assert frame.image.shape == (*HW, 3) and rep.floor_ok
    assert svc.stale(now=1.5, max_age_s=1.0) == {2: False} and svc.stale(now=3.0, max_age_s=1.0) == {2: True}
    assert svc.floor_status() == {2: (0, 1)}


def test_loopback_radio() -> None:
    a, b = LoopbackRadio.pair()
    assert a.send("telemetry", b"x").error_message is None
    assert b.receive(0.0).payload == ("telemetry", b"x")
    assert not b.receive(0.0).ok
    a.send_symbols(np.array([1 + 1j, 2 - 1j]))
    assert np.allclose(b.receive_symbols(2, 0.0).payload, [1 + 1j, 2 - 1j])
    lossy_a, lossy_b = LoopbackRadio.pair(loss_ratio=0.5, seed=1)
    for i in range(1000):
        lossy_a.send("t", bytes([i % 256]))
    got = sum(1 for _ in iter(lambda: lossy_b.receive(0).ok or None, None))
    assert 400 < got < 600
    with pytest.raises(ValueError):
        LoopbackRadio(loss_ratio=1.0)


@pytest.mark.slow
@pytest.mark.skipif(not ffmpeg_available(), reason="ffmpeg not on PATH")
def test_h5_digital_codec_still_wins_on_test_video() -> None:
    """Paper H5 'not supported': zero-latency H.264 + ideal code beats the hybrid. Measured on our test videos:
    -7.5..-11.2 dB (synthetic) and -18.5..-26.9 dB (testsrc2) at 6..12 dB; see docs/VIDEO_PIPELINE.md §6."""
    from sim.video import h264_baseline as h264
    frames = ffmpeg_source(*HW, 16, "testsrc2")
    cfg = paper_pilot_profile(HW, snr_db=10)
    hybrid = np.mean([r.psnr_db for r in run(cfg, frames, 10)])
    dec = h264.encode_decode(frames, h264.capacity_matched_kbps(cfg.channel_uses(), 10, cfg.t_g), cfg.fps, cfg.G)
    assert psnr(frames, dec) > hybrid + 3.0
