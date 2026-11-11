"""Analogue refinement power allocation with side information, channel-estimation error and an
active-set limit. [P1 Eq. 18, Prop. 8 Eq. 19, Prop. 16 Eq. 36-37, Rem. 6, Lemma 7 Eq. 31]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


def allocate(sigma: np.ndarray, sigma_tilde: np.ndarray, nu: np.ndarray, power: float) -> tuple[np.ndarray, np.ndarray]:
    """Allocate. [P1 Prop. 8 Eq. 19]"""
    raise stub(
        "nidar/video/refinement/allocator.py:allocate",
        "P1 Prop. 8 Eq. 19",
        WAITS_FOR,
    )


def allocate_with_estimation_error(
    sigma: np.ndarray, nu: np.ndarray, eps2: np.ndarray, power: float
) -> tuple[np.ndarray, np.ndarray]:
    """Allocate with estimation error. [P1 Prop. 16 Eq. 36]"""
    raise stub(
        "nidar/video/refinement/allocator.py:allocate_with_estimation_error",
        "P1 Prop. 16 Eq. 36",
        WAITS_FOR,
    )


def component_saving(sigma: float, nu: float, mu: float) -> float:
    """Component saving. [P1 Lemma 7 Eq. 31]"""
    raise stub(
        "nidar/video/refinement/allocator.py:component_saving",
        "P1 Lemma 7 Eq. 31",
        WAITS_FOR,
    )
