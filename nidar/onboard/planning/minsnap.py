"""Minimum-snap quartic B-spline QP with waypoint, kinematic, terrain and landing-zone constraints.
[P2 §8.1 / §10.1 Eq. 188-198] [P2 §12.3.1 terminal constraint]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.contracts import ProcessResult
from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


class MinSnapGenerator:
    """Implements ``TrajectoryGenerator`` (OSQP-class QP solver)."""

    def generate(self, waypoints: np.ndarray, v_max: float, a_max: float, terrain: object) -> ProcessResult:
        """[P2 Eq. 193-198]"""
        raise stub(
            "nidar/onboard/planning/minsnap.py:MinSnapGenerator.generate",
            "P2 Eq. 193-198",
            WAITS_FOR,
        )
