"""Dynamic weighted Voronoi tessellation, Lloyd centroid tracking, boundary hysteresis.
Weight law has two Paper 2 variants (OQ-05c'). Runs at the GCS. [P2 §5.1 / §7.1 Eq. 157-168] [P2 §5.4 Eq. 126-131]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.contracts import GeoPolygon, PartitionUpdate
from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


class DwvtPartitioner:
    """DwvtPartitioner."""

    def partition(self, boundary: GeoPolygon, positions: dict, weights: dict) -> PartitionUpdate:
        """[P2 Eq. 159]"""
        raise stub(
            "nidar/swarm/dwvt.py:DwvtPartitioner.partition",
            "P2 Eq. 159",
            WAITS_FOR,
        )

    def centroids(self, update: PartitionUpdate) -> dict:
        """[P2 Eq. 165-168]"""
        raise stub(
            "nidar/swarm/dwvt.py:DwvtPartitioner.centroids",
            "P2 Eq. 165-168",
            WAITS_FOR,
        )

    def apply_hysteresis(self, previous: PartitionUpdate, proposed: PartitionUpdate, h: float) -> PartitionUpdate:
        """[P2 Eq. 127]"""
        raise stub(
            "nidar/swarm/dwvt.py:DwvtPartitioner.apply_hysteresis",
            "P2 Eq. 127",
            WAITS_FOR,
        )
