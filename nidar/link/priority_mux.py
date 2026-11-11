"""Priority multiplexing state > map > video. Paper 2's linear programme is degenerate (OQ-15), so rate
bounds are configuration with no default. [P2 §12.1 / §15.1.1]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


class PriorityMux:
    """PriorityMux."""

    def schedule(self, queues: dict, capacity: int) -> dict:
        """[P2 §12.1 weights 10/5/1]"""
        raise stub(
            "nidar/link/priority_mux.py:PriorityMux.schedule",
            "P2 §12.1 weights 10/5/1",
            WAITS_FOR,
        )
