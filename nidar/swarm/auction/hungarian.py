"""Min-cost assignment by the Hungarian (Munkres) algorithm at the GCS. Reports infeasibility when
survivors exceed kit-holding drones instead of failing silently (OQ-01). [P2 §7.3 Eq. 183, 125]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.contracts import ProcessResult
from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


class HungarianAuction:
    """HungarianAuction."""

    def assign(self, costs: np.ndarray, drone_ids: list, survivor_ids: list) -> ProcessResult:
        """[P2 Eq. 183]"""
        raise stub(
            "nidar/swarm/auction/hungarian.py:HungarianAuction.assign",
            "P2 Eq. 183",
            WAITS_FOR,
        )
