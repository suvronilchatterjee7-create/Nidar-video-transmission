"""Payload release mechanism with hardware trigger. Mechanism design: OQ-01, OQ-20. [P2 §6.4 Exc. 4]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.contracts import ProcessResult
from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


class PayloadRelease:
    """Implements ``PayloadMechanism``."""

    def release(self) -> ProcessResult:
        """[P2 §6.4 Exc. 4]"""
        raise stub(
            "nidar/onboard/payload/release.py:PayloadRelease.release",
            "P2 §6.4 Exc. 4",
            WAITS_FOR,
        )
