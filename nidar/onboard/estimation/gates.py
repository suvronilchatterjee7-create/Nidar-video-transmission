"""GNSS / LiDAR measurement gates. Two incompatible Paper 2 gate forms exist (OQ-05d); both are
named here, neither is the default. [P2 §9.2 Eq. 256] [P2 §13.2.2]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


def gnss_gate_3sigma(innovation: np.ndarray, sigma: np.ndarray, consecutive: int) -> bool:
    """Gnss gate 3sigma. [P2 §9.2 Eq. 256 (variant A)]"""
    raise stub(
        "nidar/onboard/estimation/gates.py:gnss_gate_3sigma",
        "P2 §9.2 Eq. 256 (variant A)",
        WAITS_FOR,
    )


def gnss_gate_chi2(innovation: np.ndarray, S: np.ndarray, threshold: float) -> bool:
    """Gnss gate chi2. [P2 §13.2.2 chi2(3, 0.999) = 16.27 (variant B)]"""
    raise stub(
        "nidar/onboard/estimation/gates.py:gnss_gate_chi2",
        "P2 §13.2.2 chi2(3, 0.999) = 16.27 (variant B)",
        WAITS_FOR,
    )
