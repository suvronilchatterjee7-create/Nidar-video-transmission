"""Declarative preflight gate table run during the 300 s setup window; a missing gate fails visibly.
[P2 §12.4] [BRIEF §3] [P1 Prop. 18, Cor. 6 video gates] [ADIAT-inspired: failure isolation]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.contracts import MissionDefinition
from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


class PreflightRunner:
    """PreflightRunner."""

    def run(self, mission: MissionDefinition, statuses: dict) -> dict:
        """[P2 §12.4 steps 1-5]"""
        raise stub(
            "nidar/gcs/preflight.py:PreflightRunner.run",
            "P2 §12.4 steps 1-5",
            WAITS_FOR,
        )
