"""Boustrophedon cellular decomposition of a Voronoi cell, sweep spacing <= W_FOV (1 - overlap).
[P2 §5.2 / §7.2 Eq. 169-173]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.contracts import PartitionCell, ProcessResult
from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


class BoustrophedonPlanner:
    """Implements ``CoveragePlanner``."""

    def plan(self, cell: PartitionCell, altitude_m: float, fov_h_rad: float, overlap: float) -> ProcessResult:
        """[P2 Eq. 170-173]"""
        raise stub(
            "nidar/onboard/planning/coverage_bcd.py:BoustrophedonPlanner.plan",
            "P2 Eq. 170-173",
            WAITS_FOR,
        )
