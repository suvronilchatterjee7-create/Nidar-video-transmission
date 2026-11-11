"""Precomputed terrain-aware safe corridor to the launch pad for link-loss RTH. Paper 2 names it but does
not say how or when it is computed (docs/ARCHITECTURE.md §6(e2)). [P2 §9.1, §14.1]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.contracts import GeoPolygon
from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


def corridor_to_pad(position: np.ndarray, pad: GeoPolygon, terrain: object) -> np.ndarray:
    """Corridor to pad. [P2 §9.1 / §14.1]"""
    raise stub(
        "nidar/onboard/planning/safe_corridor.py:corridor_to_pad",
        "P2 §9.1 / §14.1",
        WAITS_FOR,
    )
