"""Control barrier functions: inter-agent (d_safe = 3.0 m), terrain, geofence; ghost buffer for stale
neighbour state. Geofence normal sign is OQ-05i; ghost-buffer formula is OQ-05h.
[P2 §8.3 / §11.1 Eq. 209-226] [P2 §14.1]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.contracts import DroneState, GeoPolygon
from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


def inter_agent_constraint(xi: DroneState, xj: DroneState, d_safe: float, alpha: float) -> tuple[np.ndarray, float]:
    """Inter agent constraint. [P2 Eq. 216-220]"""
    raise stub(
        "nidar/onboard/control/cbf.py:inter_agent_constraint",
        "P2 Eq. 216-220",
        WAITS_FOR,
    )


def terrain_constraint(x: DroneState, terrain: object, z_min: float, alpha: float) -> tuple[np.ndarray, float]:
    """Terrain constraint. [P2 Eq. 221-223]"""
    raise stub(
        "nidar/onboard/control/cbf.py:terrain_constraint",
        "P2 Eq. 221-223",
        WAITS_FOR,
    )


def geofence_constraints(x: DroneState, fence: GeoPolygon, alpha: float, dt: float) -> tuple[np.ndarray, np.ndarray]:
    """Geofence constraints. [P2 Eq. 224-225 (sign OQ-05i)]"""
    raise stub(
        "nidar/onboard/control/cbf.py:geofence_constraints",
        "P2 Eq. 224-225 (sign OQ-05i)",
        WAITS_FOR,
    )


def ghost_buffer(d_safe: float, age_s: float, v_max: float, a_max: float) -> float:
    """Ghost buffer. [P2 §14.1 (OQ-05h)]"""
    raise stub(
        "nidar/onboard/control/cbf.py:ghost_buffer",
        "P2 §14.1 (OQ-05h)",
        WAITS_FOR,
    )
