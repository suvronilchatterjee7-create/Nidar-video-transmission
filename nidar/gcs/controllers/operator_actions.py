"""Operator-action gate: the ONLY way operator input enters the system.

Exactly four actions exist [BRIEF §3, §4, §8]; which are enabled depends on the mission phase
(docs/INTERFACES.md §8, docs/ARCHITECTURE.md §7). Any other input would be manual intervention
[BRIEF §3]. P2 lists three buttons [P2 §12.3.2]; EMERGENCY_RECALL is added per the Brief (OQ-16).
This module is UI wiring only; it holds no mission logic. [ADIAT-inspired: ADIAT-standards §2.1]
"""
from __future__ import annotations

from nidar.common.contracts import MissionPhase, OperatorAction

_A = OperatorAction
_P = MissionPhase

# Phase -> enabled actions. Derived from docs/INTERFACES.md §8:
#   LOAD in IDLE/BLOCKED; START in READY only; ABORT and RECALL from READY onward until COMPLETE.
_ALLOWED: dict[str, frozenset[str]] = {
    _P.IDLE: frozenset({_A.LOAD_MISSION_FILE}),
    _P.MISSION_LOADED: frozenset(),
    _P.PREFLIGHT: frozenset(),
    _P.BLOCKED: frozenset({_A.LOAD_MISSION_FILE}),
    _P.READY: frozenset({_A.START_MISSION, _A.SAFETY_ABORT, _A.EMERGENCY_RECALL}),
    _P.RUNNING: frozenset({_A.SAFETY_ABORT, _A.EMERGENCY_RECALL}),
    _P.RETURNING: frozenset({_A.SAFETY_ABORT, _A.EMERGENCY_RECALL}),
    _P.RECALLING: frozenset({_A.SAFETY_ABORT, _A.EMERGENCY_RECALL}),
    _P.ABORTING: frozenset({_A.SAFETY_ABORT, _A.EMERGENCY_RECALL}),
    _P.COMPLETE: frozenset(),
}


class ActionNotPermitted(PermissionError):
    """Raised when an action is unknown or not enabled in the current phase."""


def allowed_actions(phase: str) -> frozenset[str]:
    if phase not in _ALLOWED:
        raise ValueError(f"unknown mission phase {phase!r}")
    return _ALLOWED[phase]


def check_action(action: str, phase: str) -> None:
    """Raise ActionNotPermitted unless ``action`` is one of the 4 Brief actions and enabled in ``phase``."""
    if action not in OperatorAction.ALL:
        raise ActionNotPermitted(f"{action!r} is not one of the four permitted operator actions [BRIEF §3]")
    if action not in allowed_actions(phase):
        raise ActionNotPermitted(f"{action!r} is not enabled in phase {phase}")
