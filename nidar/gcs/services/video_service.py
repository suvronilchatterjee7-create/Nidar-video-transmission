"""GCS video service: one ``VideoSource`` per drone for the video panel [BRIEF §4 "live video feed display"].

Holds the latest decoded frame and ``VideoQualityReport`` per drone, converts 4:2:0 to RGB for display
(BT.601 full range), and reports staleness so the view can dim a stale tile [ADIAT-inspired: HUD dims when
stale]. Neutral to OQ-02: anything that yields (VideoFrame, report) can be registered. Number of tiles
shown at once is OQ-09. The panel widget itself waits for the GCS UI-toolkit decision (docs §10).
[P1 §5.1 D1-D5]
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from nidar.common.contracts import VideoFrame, VideoQualityReport


def yuv420_to_rgb(y: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """BT.601 full-range conversion with nearest-neighbour chroma upsampling -> (H, W, 3) uint8."""
    yf = y.astype(float)
    uf = np.repeat(np.repeat(u.astype(float) - 128.0, 2, axis=0), 2, axis=1)[: y.shape[0], : y.shape[1]]
    vf = np.repeat(np.repeat(v.astype(float) - 128.0, 2, axis=0), 2, axis=1)[: y.shape[0], : y.shape[1]]
    r = yf + 1.402 * vf
    g = yf - 0.344136 * uf - 0.714136 * vf
    b = yf + 1.772 * uf
    return np.clip(np.rint(np.stack([r, g, b], axis=-1)), 0, 255).astype(np.uint8)


@dataclass
class DecodedVideoSource:
    """Implements ``VideoSource`` for the Paper 1 decoder output."""

    drone_id: int
    _frame: VideoFrame | None = None
    _report: VideoQualityReport | None = None
    _t_received: float | None = None
    history: list[VideoQualityReport] = field(default_factory=list)

    def push(self, yuv: tuple[np.ndarray, np.ndarray, np.ndarray], gop_index: int, t_source: float,
             report: VideoQualityReport | None, t_received: float) -> None:
        self._frame = VideoFrame(self.drone_id, t_source, yuv420_to_rgb(*yuv), gop_index)
        self._report = report
        self._t_received = t_received
        if report is not None:
            self.history.append(report)

    def latest(self) -> tuple[VideoFrame, VideoQualityReport | None] | None:
        return None if self._frame is None else (self._frame, self._report)

    def age_s(self, now: float) -> float:
        return float("inf") if self._t_received is None else now - self._t_received


class VideoService:
    """Registry of video sources for the GCS panel."""

    def __init__(self) -> None:
        self._sources: dict[int, DecodedVideoSource] = {}

    def source(self, drone_id: int) -> DecodedVideoSource:
        if drone_id not in self._sources:
            self._sources[drone_id] = DecodedVideoSource(drone_id)
        return self._sources[drone_id]

    def drone_ids(self) -> list[int]:
        return sorted(self._sources)

    def stale(self, now: float, max_age_s: float) -> dict[int, bool]:
        """Per drone: True when no frame arrived within ``max_age_s`` (threshold is a display setting)."""
        return {d: s.age_s(now) > max_age_s for d, s in self._sources.items()}

    def floor_status(self) -> dict[int, tuple[int, int]]:
        """Per drone: (GoPs with floor lost, GoPs received), for the floor-failure counter [P1 Cor. 7]."""
        return {d: (sum(not r.floor_ok for r in s.history), len(s.history)) for d, s in self._sources.items()}
