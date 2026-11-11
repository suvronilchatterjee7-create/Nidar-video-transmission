"""Decoder D1-D5: channel estimation, floor decode, decoder-side motion-compensated side information,
scalar Kalman bank, conditional mean, floor-only fallback. [P1 §5.1 D1-D5, Lemma 3, Prop. 3, Prop. 9, Rem. 5]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.contracts import ProcessResult, ResourcePlan
from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


def kalman_steady_state(a: float, omega: float, pi: float) -> float:
    """Kalman steady state. [P1 Prop. 3 Eq. 10]"""
    raise stub(
        "nidar/video/decoder.py:kalman_steady_state",
        "P1 Prop. 3 Eq. 10",
        WAITS_FOR,
    )


def posterior_after_floor(sigma_tilde: np.ndarray, theta_f: float, lam: np.ndarray) -> np.ndarray:
    """Posterior after floor. [P1 Eq. 18]"""
    raise stub(
        "nidar/video/decoder.py:posterior_after_floor",
        "P1 Eq. 18",
        WAITS_FOR,
    )


def conditional_mean(
    z: np.ndarray,
    c_floor: np.ndarray,
    y: np.ndarray,
    g: np.ndarray,
    nu: np.ndarray,
    sigma_tilde: np.ndarray,
    theta_f: float,
    lam: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Conditional mean. [P1 Prop. 9 Eq. 20]"""
    raise stub(
        "nidar/video/decoder.py:conditional_mean",
        "P1 Prop. 9 Eq. 20",
        WAITS_FOR,
    )


class HybridDecoder:
    """Implements ``VideoDecoder``."""

    def decode(self, rx_symbols: np.ndarray, plan: ResourcePlan) -> ProcessResult:
        """[P1 §5.1 D1-D5]"""
        raise stub(
            "nidar/video/decoder.py:HybridDecoder.decode",
            "P1 §5.1 D1-D5",
            WAITS_FOR,
        )
