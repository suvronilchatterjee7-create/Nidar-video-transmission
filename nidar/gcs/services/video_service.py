"""Holds one ``VideoSource`` per drone for the video panel; neutral to OQ-02. [BRIEF §4] [P1 §5.1 D1-D5]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.contracts import DroneId
from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


class VideoService:
    """VideoService."""

    def source(self, drone_id: DroneId) -> object:
        """[BRIEF §4]"""
        raise stub(
            "nidar/gcs/services/video_service.py:VideoService.source",
            "BRIEF §4",
            WAITS_FOR,
        )
