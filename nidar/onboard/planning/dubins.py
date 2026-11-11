"""Curvature-bounded turns between sweep lines. [P2 §7.2 Eq. 174-175]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


def min_turn_radius(v_cruise: float, phi_max_rad: float) -> float:
    """Min turn radius. [P2 Eq. 174: R_min = v^2 / (g tan phi_max)]"""
    raise stub(
        "nidar/onboard/planning/dubins.py:min_turn_radius",
        "P2 Eq. 174: R_min = v^2 / (g tan phi_max)",
        WAITS_FOR,
    )


def turn(p0: np.ndarray, h0: float, p1: np.ndarray, h1: float, r_min: float) -> np.ndarray:
    """Turn. [P2 Eq. 175]"""
    raise stub(
        "nidar/onboard/planning/dubins.py:turn",
        "P2 Eq. 175",
        WAITS_FOR,
    )
