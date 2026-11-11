"""Assignment cost terms. Two Paper 2 forms (Eq. 38 vs Eq. 179) are both provided; neither is the default
(OQ-05c). [P2 §2.4 Eq. 38] [P2 §7.3 Eq. 179-181]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.contracts import AssignmentCostTerms, DroneStatus
from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


def cost_eq38(status: DroneStatus, p_surv: np.ndarray, v_cruise: float, weights: dict) -> AssignmentCostTerms:
    """Cost eq38. [P2 Eq. 38-40]"""
    raise stub(
        "nidar/swarm/auction/cost.py:cost_eq38",
        "P2 Eq. 38-40",
        WAITS_FOR,
    )


def cost_eq179(
    status: DroneStatus, p_surv: np.ndarray, v_cruise: float, weights: dict, abandoned_area_frac: float
) -> AssignmentCostTerms:
    """Cost eq179. [P2 Eq. 179-181]"""
    raise stub(
        "nidar/swarm/auction/cost.py:cost_eq179",
        "P2 Eq. 179-181",
        WAITS_FOR,
    )
