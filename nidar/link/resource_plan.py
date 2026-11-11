"""Per-GoP channel-use split: pilots, telemetry (OQ-14), certified floor, refinement.
[P1 §3.1, §6.5] [P2 §12.1 priority order]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.contracts import CertifiedFloorDesign, DroneId, ResourcePlan
from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


def plan_gop(
    drone_id: DroneId, gop_index: int, n_total: int, n_pilot: int, n_telemetry: int, design: CertifiedFloorDesign
) -> ResourcePlan:
    """Plan gop. [P1 §3.1, §6.5; P1 Prop. 18]"""
    raise stub(
        "nidar/link/resource_plan.py:plan_gop",
        "P1 §3.1, §6.5; P1 Prop. 18",
        WAITS_FOR,
    )
