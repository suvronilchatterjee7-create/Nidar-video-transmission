"""Per-GoP channel-use split: pilots, telemetry, certified floor, refinement.

n = n_pilot + n_telemetry + n_floor + n_refinement [P1 §3.1, §6.5]; telemetry is reserved before video
[P2 §12.1 priority order]; the floor size comes from the certified design and is never altered
[P1 Prop. 18]. The telemetry size is an input with no default (OQ-14, OQ-15).
"""
from __future__ import annotations

from nidar.common.contracts import CertifiedFloorDesign, DroneId, ResourcePlan


def plan_gop(drone_id: DroneId, gop_index: int, n_total: int, n_pilot: int, n_telemetry: int,
             design: CertifiedFloorDesign) -> ResourcePlan | None:
    """Return the plan, or None when the certified floor does not fit (infeasible GoP, OQ-24)."""
    n_ref = n_total - n_pilot - n_telemetry - design.n_f
    if n_ref < 0:
        return None
    return ResourcePlan(drone_id, gop_index, n_total, n_pilot, n_telemetry, design.n_f, n_ref, design.design_id)
