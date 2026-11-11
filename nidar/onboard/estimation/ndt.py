"""Normal Distributions Transform scan matching. [P2 §4.2 Eq. 77-81]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


def match_scan(points: np.ndarray, submap: object, initial: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Match scan. [P2 Eq. 78-81 (Gauss-Newton on the NDT objective; returns delta_x and R = I^-1)]"""
    raise stub(
        "nidar/onboard/estimation/ndt.py:match_scan",
        "P2 Eq. 78-81 (Gauss-Newton on the NDT objective; returns delta_x and R = I^-1)",
        WAITS_FOR,
    )
