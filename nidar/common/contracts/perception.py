"""Detection, geotag and survivor contracts. docs/INTERFACES.md §4.

Detections are always in SOURCE-frame pixels, top-left origin. [ADIAT-inspired: StreamDetection]
Geotag with covariance [P2 §4.3 Eq. 88-100]; Bayesian confirmation [P2 §9.3 Eq. 258-265].
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from nidar.common.contracts.base import DroneId, as_array, require


@dataclass(frozen=True)
class Detection:
    """Normalised detector output. [ADIAT-inspired: StreamDetection] [P2 §4.3]"""

    drone_id: DroneId
    t_source: float
    frame_size_wh: tuple[int, int]
    bbox_xyxy: tuple[float, float, float, float]
    centroid_uv: tuple[float, float]       # pixel used for the ray cast [P2 Eq. 88]
    confidence: float                      # C_cnn in [0,1] [P2 Eq. 260]; calibration OQ-25
    class_name: str
    keypoints: Optional[np.ndarray] = None # (17,3) COCO x,y,v [DATASET: annotations/coco]
    posture: Optional[str] = None          # carried only; used by no decision (IDEA-01 pending)

    def __post_init__(self) -> None:
        w, h = self.frame_size_wh
        require(w > 0 and h > 0, "frame_size_wh must be positive")
        x0, y0, x1, y1 = self.bbox_xyxy
        require(0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h,
                f"bbox {self.bbox_xyxy} must lie inside the source frame {w}x{h} (source-frame pixels)")
        u, v = self.centroid_uv
        require(x0 <= u <= x1 and y0 <= v <= y1, "centroid_uv must lie inside bbox")
        require(0.0 <= self.confidence <= 1.0, "confidence must be in [0, 1]")
        if self.keypoints is not None:
            object.__setattr__(self, "keypoints", as_array("Detection.keypoints", self.keypoints, (17, 3)))


@dataclass(frozen=True)
class GeotagObservation:
    """Single-view 3-D geotag. [P2 Eq. 92, 96, 99, 100]"""

    detection: Detection
    p_surv: np.ndarray        # (3,) F_I
    sigma_surv: np.ndarray    # (3,3)
    low_confidence: bool      # gate form OQ-05k
    ray_depth_m: float        # s* [P2 Eq. 92]

    def __post_init__(self) -> None:
        object.__setattr__(self, "p_surv", as_array("GeotagObservation.p_surv", self.p_surv, (3,)))
        s = as_array("GeotagObservation.sigma_surv", self.sigma_surv, (3, 3))
        require(np.allclose(s, s.T, atol=1e-9), "sigma_surv must be symmetric")
        object.__setattr__(self, "sigma_surv", s)
        require(self.ray_depth_m > 0, "ray_depth_m must be > 0 (s > 0, [P2 Eq. 91])")


class SurvivorStatus:
    """Lifecycle of a survivor hypothesis. UNSERVICEABLE exists because of OQ-01."""

    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"          # P > 0.95 [P2 Eq. 264-265]
    ASSIGNED = "assigned"
    DELIVERED = "delivered"
    UNSERVICEABLE = "unserviceable"
    ALL = frozenset({CANDIDATE, CONFIRMED, ASSIGNED, DELIVERED, UNSERVICEABLE})


@dataclass(frozen=True)
class SurvivorTrack:
    """Fused survivor hypothesis. [P2 §9.3]"""

    schema_version: int
    survivor_id: str
    p_surv: np.ndarray
    sigma_surv: np.ndarray
    belief: float                         # P(S | D_1:m) [P2 Eq. 260, 264]
    consistent_frames: int                # K [P2 Eq. 261]
    observing_drones: frozenset[DroneId]  # [P2 Eq. 263]
    status: str
    t_first_seen: float
    t_confirmed: Optional[float] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "p_surv", as_array("SurvivorTrack.p_surv", self.p_surv, (3,)))
        object.__setattr__(self, "sigma_surv", as_array("SurvivorTrack.sigma_surv", self.sigma_surv, (3, 3)))
        require(0.0 <= self.belief <= 1.0, "belief must be a probability")
        require(self.consistent_frames >= 0, "consistent_frames must be >= 0")
        require(self.status in SurvivorStatus.ALL, f"unknown survivor status {self.status!r}")
        require(len(self.observing_drones) >= 1, "at least one observing drone")
        require((self.t_confirmed is None) == (self.status == SurvivorStatus.CANDIDATE),
                "t_confirmed is set exactly when status is past CANDIDATE")
