"""One-command demo of the Paper 1 video link in simulation.

Runs synthetic test video through encoder -> simulated radio channel -> decoder at several SNRs and prints
a table: floors decoded, PSNR (full / floor-only / model prediction), equivalent throughput, floor share.
Optional: block fading with pilots, decoder-side motion search, a zero-latency H.264 comparison (needs
ffmpeg on PATH). Uses the labelled PAPER PILOT PROFILE, not our link (OQ-03, OQ-12).
[P1 §5.1, §D] [TEAM-BRIEF §6.1 D9]

Examples (from the repository root):
  python tools/demo_video_link.py
  python tools/demo_video_link.py --size 288x352 --snr 4 8 12 --gops 4
  python tools/demo_video_link.py --fading 8
  python tools/demo_video_link.py --h264
"""
from __future__ import annotations

import argparse
import dataclasses
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # run from a checkout without installing

import numpy as np  # noqa: E402

from nidar.video.certificates.outage import outage_rate  # noqa: E402
from nidar.video.config import paper_pilot_profile  # noqa: E402
from sim.video.end_to_end import run  # noqa: E402
from sim.video.test_video import ffmpeg_available, ffmpeg_source, moving_scene, psnr  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Paper 1 video link demo (simulation)")
    ap.add_argument("--size", default="176x320", help="luma HxW, multiples of 16 (default 176x320)")
    ap.add_argument("--snr", type=float, nargs="+", default=[4.0, 8.0, 12.0], help="mean SNR values in dB")
    ap.add_argument("--gops", type=int, default=3, help="GoPs per SNR point (8 frames each)")
    ap.add_argument("--fading", type=int, default=0, help="Rayleigh blocks per GoP (0 = AWGN)")
    ap.add_argument("--motion", choices=["zero", "block"], default="zero", help="decoder side information")
    ap.add_argument("--video", choices=["synthetic", "testsrc2"], default="synthetic")
    ap.add_argument("--h264", action="store_true", help="also run zero-latency H.264 at the capacity-matched rate")
    a = ap.parse_args(argv)

    h, w = (int(v) for v in a.size.lower().split("x"))
    n_frames = 8 * a.gops
    if a.video == "testsrc2":
        if not ffmpeg_available():
            print("ffmpeg not found on PATH; use --video synthetic")
            return 1
        frames = ffmpeg_source(h, w, n_frames, "testsrc2")
    else:
        frames = moving_scene(h, w, n_frames, seed=1)

    print(f"PAPER PILOT PROFILE (simulation, not our link) | {h}x{w}, 25 fps, G=8 | video={a.video} | "
          f"{'AWGN' if a.fading == 0 else f'Rayleigh L={a.fading} + pilots'} | motion={a.motion}")
    header = (f"{'SNR dB':>6} {'floors':>7} {'PSNR':>6} {'floor-only':>10} {'model':>6} "
              f"{'Teq Mbps-eq':>11} {'floor share':>11}")
    if a.h264:
        header += f" {'H.264 zl':>8}"
    print(header)
    for snr in a.snr:
        cfg = paper_pilot_profile((h, w), snr_db=snr, fading_blocks=a.fading, motion_search=a.motion)
        if a.fading:
            cfg = dataclasses.replace(cfg, floor_rate_bits_per_use=outage_rate(a.fading, snr, 1e-2))
        t0 = time.perf_counter()
        res = run(cfg, frames, snr, seed=0)
        ok = [r for r in res if r.floor_ok]

        def mean(attr: str, rows=ok) -> str:
            return f"{np.mean([getattr(r, attr) for r in rows]):.2f}" if rows else "  -  "

        share = np.mean([r.floor_share for r in res])
        line = (f"{snr:6.1f} {len(ok):>3}/{len(res):<3} {mean('psnr_db', res):>6} {mean('floor_only_psnr_db'):>10} "
                f"{mean('model_psnr_db'):>6} {mean('teq_equiv_mbps'):>11} {share:>11.3f}")
        if a.h264:
            if ffmpeg_available():
                from sim.video import h264_baseline as h264
                dec = h264.encode_decode(frames, h264.capacity_matched_kbps(cfg.channel_uses(), snr, cfg.t_g),
                                         cfg.fps, cfg.G)
                line += f" {psnr(frames, dec):8.2f}"
            else:
                line += "   no ffmpeg"
        print(line + f"   ({time.perf_counter() - t0:.1f} s)")
    print("PSNR in dB over Y, U, V. 'model' is the analytic prediction (Prop. 9). See docs/VIDEO_PIPELINE.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
