"""Nonlinear disturbance observer for wind feedforward. [P2 §9.4 Eq. 266-267] [P2 §14.2.1]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.contracts import DroneState
from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


class DisturbanceObserver:
    """DisturbanceObserver."""

    def update(self, x: DroneState, thrust: float, dt: float) -> np.ndarray:
        """[P2 §14.2.1]"""
        raise stub(
            "nidar/onboard/control/disturbance_observer.py:DisturbanceObserver.update",
            "P2 §14.2.1",
            WAITS_FOR,
        )
