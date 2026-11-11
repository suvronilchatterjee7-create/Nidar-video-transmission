"""GCS service that recomputes DWVT weights and cells. [P2 §7.1] (weight law OQ-05c')

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.contracts import PartitionUpdate
from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


class PartitionService:
    """PartitionService."""

    def update(self, statuses: dict) -> PartitionUpdate:
        """[P2 Eq. 159-168]"""
        raise stub(
            "nidar/gcs/services/partition_service.py:PartitionService.update",
            "P2 Eq. 159-168",
            WAITS_FOR,
        )
