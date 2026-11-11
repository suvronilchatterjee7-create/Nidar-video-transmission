"""Bayesian survivor confirmation: belief grid prior 0.01, K = 10 frames, multi-drone fusion, promote
at P > 0.95. Runs onboard; fusion topology OQ-28. [P2 §9.3 Eq. 258-265]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.contracts import GeotagObservation, SurvivorTrack
from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


class BayesianConfirmer:
    """Implements ``SurvivorConfirmer``."""

    def observe(self, obs: GeotagObservation) -> SurvivorTrack | None:
        """[P2 Eq. 260-265]"""
        raise stub(
            "nidar/swarm/confirmation.py:BayesianConfirmer.observe",
            "P2 Eq. 260-265",
            WAITS_FOR,
        )

    def merge_remote(self, track: SurvivorTrack) -> None:
        """[P2 Eq. 263]"""
        raise stub(
            "nidar/swarm/confirmation.py:BayesianConfirmer.merge_remote",
            "P2 Eq. 263",
            WAITS_FOR,
        )
