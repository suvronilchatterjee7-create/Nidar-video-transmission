"""Floor-power stationarity and the damped controller restricted to the certified grid.
[P1 Prop. 14 Eq. 32, Eq. 40, Prop. 17, Prop. 18, Thm 4]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.contracts import CertifiedFloorDesign
from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


def stationarity_lhs(gamma_f: float) -> float:
    """Stationarity lhs. [P1 Eq. 32 left side]"""
    raise stub(
        "nidar/video/control/controller.py:stationarity_lhs",
        "P1 Eq. 32 left side",
        WAITS_FOR,
    )


class DampedFloorController:
    """Implements ``FloorController``."""

    def step(self, design_snr_db: float, n_available: int) -> CertifiedFloorDesign | None:
        """[P1 Eq. 40, Prop. 18]"""
        raise stub(
            "nidar/video/control/controller.py:DampedFloorController.step",
            "P1 Eq. 40, Prop. 18",
            WAITS_FOR,
        )
