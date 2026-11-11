"""Truncated Signed Distance Field terrain manifold. [P2 §4.2 Eq. 82-87]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.contracts import DroneState
from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


class TsdfMap:
    """Implements the ``TerrainMap`` protocol (docs/INTERFACES.md §9)."""

    def integrate(self, points: np.ndarray, pose: DroneState) -> None:
        """[P2 Eq. 83-84]"""
        raise stub(
            "nidar/onboard/mapping/tsdf.py:TsdfMap.integrate",
            "P2 Eq. 83-84",
            WAITS_FOR,
        )

    def sdf(self, p: np.ndarray) -> float:
        """[P2 Eq. 83]"""
        raise stub(
            "nidar/onboard/mapping/tsdf.py:TsdfMap.sdf",
            "P2 Eq. 83",
            WAITS_FOR,
        )

    def grad(self, p: np.ndarray) -> np.ndarray:
        """[P2 Eq. 87]"""
        raise stub(
            "nidar/onboard/mapping/tsdf.py:TsdfMap.grad",
            "P2 Eq. 87",
            WAITS_FOR,
        )

    def ray_intersect(self, origin: np.ndarray, direction: np.ndarray) -> float | None:
        """[P2 Eq. 92 (Brent / secant root find)]"""
        raise stub(
            "nidar/onboard/mapping/tsdf.py:TsdfMap.ray_intersect",
            "P2 Eq. 92 (Brent / secant root find)",
            WAITS_FOR,
        )
