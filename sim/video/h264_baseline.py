"""H.264 baseline via the local ffmpeg/libx264, as in Paper 1's pilot comparison (H5) [P1 §D.4 baselines].

"Zero-latency" configuration: tune zerolatency, GoP length G, no B-frames, two-pass at the bit rate an ideal
capacity-achieving code would deliver over the same channel, n C(gamma) / T_g (oracle rate, ideal code: this
favours H.264, exactly as in the paper). Runs a local ffmpeg process only; no network [BRIEF §5].
"""
from __future__ import annotations

import math
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from sim.video.test_video import Frame, split_yuv420


def capacity_matched_kbps(channel_uses_per_gop: int, snr_db: float, t_g: float) -> float:
    """n C(gamma) / T_g in kbit/s [P1 §D.4]."""
    return channel_uses_per_gop * math.log2(1 + 10 ** (snr_db / 10)) / t_g / 1e3


def encode_decode(frames: list[Frame], kbps: float, fps: float, gop: int, preset: str = "medium") -> list[Frame]:
    h, w = frames[0][0].shape
    raw = b"".join(np.concatenate([p.ravel() for p in f]).tobytes() for f in frames)
    with tempfile.TemporaryDirectory() as td:
        src, out, log = Path(td) / "in.yuv", Path(td) / "out.mp4", Path(td) / "pass"
        src.write_bytes(raw)
        common = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-s", f"{w}x{h}",
                  "-r", str(fps), "-i", str(src), "-c:v", "libx264", "-preset", preset, "-tune", "zerolatency",
                  "-g", str(gop), "-keyint_min", str(gop), "-bf", "0", "-b:v", f"{kbps:.1f}k",
                  "-passlogfile", str(log)]
        subprocess.run(common + ["-pass", "1", "-f", "null", "-"], check=True, capture_output=True)
        subprocess.run(common + ["-pass", "2", str(out)], check=True, capture_output=True)
        dec = subprocess.run(["ffmpeg", "-v", "error", "-i", str(out), "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"],
                             check=True, capture_output=True).stdout
        actual_kbps = out.stat().st_size * 8 / (len(frames) / fps) / 1e3
    decoded = split_yuv420(dec, h, w)
    encode_decode.last_actual_kbps = actual_kbps        # container overhead included; reported, not hidden
    return decoded
