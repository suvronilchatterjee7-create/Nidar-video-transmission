"""GCS global N x 13 state matrix with timestamp reconciliation and a display-only constant-acceleration
predictor (never fed back to control). [P2 §12.1, §14.3]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.contracts import DroneId, DroneStatus
from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


class GlobalState:
    """GlobalState."""

    def ingest(self, status: DroneStatus) -> None:
        """[P2 §12.1]"""
        raise stub(
            "nidar/gcs/global_state.py:GlobalState.ingest",
            "P2 §12.1",
            WAITS_FOR,
        )

    def matrix(self) -> np.ndarray:
        """[P2 §12.1 X_GCS]"""
        raise stub(
            "nidar/gcs/global_state.py:GlobalState.matrix",
            "P2 §12.1 X_GCS",
            WAITS_FOR,
        )

    def display_position(self, drone_id: DroneId, t: float) -> np.ndarray:
        """[P2 §14.3]"""
        raise stub(
            "nidar/gcs/global_state.py:GlobalState.display_position",
            "P2 §14.3",
            WAITS_FOR,
        )
