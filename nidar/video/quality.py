"""Quality accounting: reference throughput T_eq, pre-channel distortion fraction, violation interval.
[P1 Def. 5-6 Eq. 12, Prop. 10 Eq. 21, Cor. 7]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


def teq_reference_mbps(distortions: np.ndarray, lam: np.ndarray, omega: np.ndarray, a: np.ndarray, t_g: float) -> float:
    """Teq reference mbps. [P1 Def. 6 Eq. 12]"""
    raise stub(
        "nidar/video/quality.py:teq_reference_mbps",
        "P1 Def. 6 Eq. 12",
        WAITS_FOR,
    )


def beta_up(distortions: np.ndarray, truncated: np.ndarray) -> float:
    """Beta up. [P1 Prop. 10 Eq. 21]"""
    raise stub(
        "nidar/video/quality.py:beta_up",
        "P1 Prop. 10 Eq. 21",
        WAITS_FOR,
    )


def mean_violation_interval_s(t_g: float, eps_f: float) -> float:
    """Mean violation interval s. [P1 Cor. 7]"""
    raise stub(
        "nidar/video/quality.py:mean_violation_interval_s",
        "P1 Cor. 7",
        WAITS_FOR,
    )
