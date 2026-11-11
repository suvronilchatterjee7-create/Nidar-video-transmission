"""Pilot-based channel estimation and pilot-count optimisation. [P1 §C.1 Eq. 35, Table 18]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.contracts import PilotPlan
from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


def rate_with_pilots(m: int, n_p: int, snr_db: float, draws: int, seed: int) -> float:
    """Rate with pilots. [P1 Eq. 35]"""
    raise stub(
        "nidar/video/pilots.py:rate_with_pilots",
        "P1 Eq. 35",
        WAITS_FOR,
    )


def optimal_pilots(m: int, snr_db: float, draws: int, seed: int) -> PilotPlan:
    """Optimal pilots. [P1 Table 18]"""
    raise stub(
        "nidar/video/pilots.py:optimal_pilots",
        "P1 Table 18",
        WAITS_FOR,
    )
