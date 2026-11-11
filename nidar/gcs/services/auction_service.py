"""GCS service that builds the cost matrix and issues assignments. [P2 §5.3 / §7.3]
(cost form OQ-05c; kit shortfall OQ-01)

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.contracts import SurvivorTrack
from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


class AuctionService:
    """AuctionService."""

    def on_confirmed(self, track: SurvivorTrack, statuses: dict) -> list:
        """[P2 Eq. 176-187]"""
        raise stub(
            "nidar/gcs/services/auction_service.py:AuctionService.on_confirmed",
            "P2 Eq. 176-187",
            WAITS_FOR,
        )
