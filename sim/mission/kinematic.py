"""Kinematic multi-drone mission simulator driving onboard/ and gcs/ through the contracts.
[P2 §1-§14] [TEAM-BRIEF §6.1 D9]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


class MissionSimulator:
    """MissionSimulator."""

    def run(self, scenario: dict, seed: int) -> object:
        """[P2 §1-§14]"""
        raise stub(
            "sim/mission/kinematic.py:MissionSimulator.run",
            "P2 §1-§14",
            WAITS_FOR,
        )
