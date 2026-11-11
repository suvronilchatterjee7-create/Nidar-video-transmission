"""Deterministic test video for the end-to-end simulation (4:2:0 planes, uint8).

``moving_scene``: textured background plus moving objects, generated in numpy (always available).
``ffmpeg_source``: ffmpeg's lavfi generators (e.g. testsrc2, mandelbrot) as raw yuv420p, if ffmpeg is on PATH.
Neither is real drone footage; results on them say nothing about our camera (OQ-12) [P1 §D.6 limits].
[USER-PROMPT §6.1 D9]
"""
from __future__ import annotations

import shutil
import subprocess

import numpy as np

Frame = tuple[np.ndarray, np.ndarray, np.ndarray]


def moving_scene(h: int, w: int, n_frames: int, seed: int = 0, speed: tuple[float, float] = (0.7, 1.3),
                 cut_at: int | None = None) -> list[Frame]:
    """Smooth gradient + fixed texture + two moving shapes; optional scene cut (new texture) at ``cut_at``."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)

    def background(r: np.random.Generator) -> np.ndarray:
        tex = r.normal(0, 1, (h // 4 + 2, w // 4 + 2))
        tex = np.kron(tex, np.ones((4, 4)))[:h, :w]
        tex = (tex + np.roll(tex, 1, 0) + np.roll(tex, 1, 1) + np.roll(tex, (1, 1), (0, 1))) / 4
        return 90 + 50 * (xx / w) + 30 * np.sin(yy / h * np.pi) + 18 * tex

    bg = background(rng)
    frames: list[Frame] = []
    for t in range(n_frames):
        if cut_at is not None and t == cut_at:
            bg = background(np.random.default_rng(seed + 1000)) * 0.7 + 60
        y = bg.copy()
        cy, cx = (h * 0.3 + speed[0] * t) % h, (w * 0.2 + speed[1] * t) % w
        y[(np.abs(yy - cy) < h * 0.12) & (np.abs(xx - cx) < w * 0.1)] = 220
        y[(yy - (h - cy)) ** 2 + (xx - (w - cx)) ** 2 < (min(h, w) * 0.12) ** 2] = 40
        u = 128 + 20 * np.sin(xx[::2, ::2] / w * 2 * np.pi + 0.05 * t)
        v = 128 + 20 * np.cos(yy[::2, ::2] / h * 2 * np.pi - 0.03 * t)
        frames.append(tuple(np.clip(np.rint(p), 0, 255).astype(np.uint8) for p in (y, u, v)))
    return frames


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def ffmpeg_source(h: int, w: int, n_frames: int, pattern: str = "testsrc2", fps: int = 25) -> list[Frame]:
    """Raw yuv420p frames from an ffmpeg lavfi generator (local process; no network)."""
    cmd = ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"{pattern}=size={w}x{h}:rate={fps}",
           "-frames:v", str(n_frames), "-pix_fmt", "yuv420p", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return split_yuv420(raw, h, w)


def split_yuv420(raw: bytes, h: int, w: int) -> list[Frame]:
    size = h * w * 3 // 2
    buf = np.frombuffer(raw, np.uint8)
    out = []
    for f in range(len(buf) // size):
        b = buf[f * size:(f + 1) * size]
        y = b[: h * w].reshape(h, w)
        u = b[h * w: h * w + h * w // 4].reshape(h // 2, w // 2)
        v = b[h * w + h * w // 4:].reshape(h // 2, w // 2)
        out.append((y.copy(), u.copy(), v.copy()))
    return out


def psnr(a: list[Frame], b: list[Frame]) -> float:
    """PSNR jointly over Y, U, V of all frames, as in the paper's pilot [P1 §D.4]."""
    se, n = 0.0, 0
    for fa, fb in zip(a, b, strict=True):
        for pa, pb in zip(fa, fb, strict=True):
            d = pa.astype(float) - pb.astype(float)
            se += float((d * d).sum())
            n += d.size
    mse = se / n
    return float("inf") if mse == 0 else 10 * np.log10(255.0**2 / mse)
