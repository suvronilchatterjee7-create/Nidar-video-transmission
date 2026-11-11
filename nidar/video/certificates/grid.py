"""Certified grid of floor designs, loaded from a versioned artefact; the controller may only pick
members of this grid. [P1 Prop. 18, Thm 4]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.contracts import CertifiedFloorDesign
from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


class CertifiedGrid:
    """CertifiedGrid."""

    def load(self, path: str) -> None:
        """[P1 Prop. 18]"""
        raise stub(
            "nidar/video/certificates/grid.py:CertifiedGrid.load",
            "P1 Prop. 18",
            WAITS_FOR,
        )

    def nearest_not_below(self, gamma_f_db: float, n_available: int) -> CertifiedFloorDesign | None:
        """[P1 Prop. 18]"""
        raise stub(
            "nidar/video/certificates/grid.py:CertifiedGrid.nearest_not_below",
            "P1 Prop. 18",
            WAITS_FOR,
        )
