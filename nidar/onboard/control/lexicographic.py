"""Lexicographic infeasibility handling: relax tracking before safety; then safe state.
Priority order differs between P2 Table 1 and Table 2 (OQ-05j). [P2 §8.5, §9.4, §14.2]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.contracts import ProcessResult
from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


def resolve(problem: object, priority_table: str) -> ProcessResult:
    """Resolve. [P2 Eq. 239-242]"""
    raise stub(
        "nidar/onboard/control/lexicographic.py:resolve",
        "P2 Eq. 239-242",
        WAITS_FOR,
    )
