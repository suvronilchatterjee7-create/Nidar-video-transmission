"""Guard conditions of the mission automaton, as pure functions.

Low battery: E_i <= E_req(p_i) + E_margin -> RTH [P2 Eq. 245-246]. GCS link loss: heartbeat age > timeout
-> RTH [P2 Eq. 247-249]; the timeout value is a setting (3 s vs 5 s, OQ-05b). Operator abort / recall
[BRIEF §3, §8]; their physical meaning is the team decision of 2026-11-12 (OQ-16): recall = return and
land on the pad, abort = descend and land at the current position.
"""
from __future__ import annotations

ABORT_ACTION = "land_in_place"      # OQ-16 decision
RECALL_ACTION = "return_to_pad"     # OQ-16 decision


def energy_to_return(distance_m: float, v_cruise: float, drain_fraction_per_s: float) -> float:
    """E_req as a fraction of E_max: time to fly home x drain rate [P2 Eq. 245, E_req(p_i)]."""
    return distance_m / v_cruise * drain_fraction_per_s


def low_battery(energy_frac: float, energy_required_frac: float, margin_frac: float) -> bool:
    """[P2 Eq. 245]"""
    return energy_frac <= energy_required_frac + margin_frac


def gcs_link_lost(heartbeat_age_s: float, timeout_s: float) -> bool:
    """[P2 Eq. 247]"""
    return heartbeat_age_s > timeout_s
