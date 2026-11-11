"""Nonlinear MPC at 50 Hz, N_h = 20, RK4, SQP-RTI (acados/CasADi binding in flight builds).
The 8-12 ms solve time is an unvalidated TARGET. [P2 §8.2 / §10.2 Eq. 199-208]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.contracts import DroneState, GeoPolygon, ProcessResult
from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


class NmpcController:
    """Implements ``SafetyController`` together with cbf.py and lexicographic.py."""

    def step(
        self, x_hat: DroneState, ref: object, neighbours: dict, geofence: GeoPolygon, terrain: object
    ) -> ProcessResult:
        """[P2 Eq. 200-206]"""
        raise stub(
            "nidar/onboard/control/nmpc.py:NmpcController.step",
            "P2 Eq. 200-206",
            WAITS_FOR,
        )

    def on_payload_release(self, dm_kg: float, dI: np.ndarray, dr_cg: np.ndarray) -> None:
        """[P2 Eq. 231-234, 272]"""
        raise stub(
            "nidar/onboard/control/nmpc.py:NmpcController.on_payload_release",
            "P2 Eq. 231-234, 272",
            WAITS_FOR,
        )
