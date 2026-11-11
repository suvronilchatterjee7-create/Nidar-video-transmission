"""Encoder orchestration E1-E7 for one GoP. [P1 §5.1 E1-E7]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.contracts import CertifiedFloorDesign, ProcessResult, ResourcePlan
from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


class HybridEncoder:
    """Implements ``VideoEncoder``."""

    def encode(self, frames: list, plan: ResourcePlan, design: CertifiedFloorDesign) -> ProcessResult:
        """[P1 §5.1 E1-E7]"""
        raise stub(
            "nidar/video/encoder.py:HybridEncoder.encode",
            "P1 §5.1 E1-E7",
            WAITS_FOR,
        )
