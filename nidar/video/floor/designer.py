"""Floor water level theta_F, coded set F, floor payload B_F and the firewall price.
[P1 Def. 5, Def. 7 Eq. 12-13, 16-17, Prop. 6 Eq. 15, §5.1 E3]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


def water_level(lam: np.ndarray, omega: np.ndarray, a: np.ndarray, t_min_bps: float, t_g: float) -> float:
    """Water level. [P1 E3, Def. 7]"""
    raise stub(
        "nidar/video/floor/designer.py:water_level",
        "P1 E3, Def. 7",
        WAITS_FOR,
    )


def reference_rate_bits(theta: float, lam: np.ndarray, omega: np.ndarray, a: np.ndarray) -> float:
    """Reference rate bits. [P1 Eq. 12]"""
    raise stub(
        "nidar/video/floor/designer.py:reference_rate_bits",
        "P1 Eq. 12",
        WAITS_FOR,
    )


def intra_rate_bits(theta: float, lam: np.ndarray) -> float:
    """Intra rate bits. [P1 Eq. 13]"""
    raise stub(
        "nidar/video/floor/designer.py:intra_rate_bits",
        "P1 Eq. 13",
        WAITS_FOR,
    )


def firewall_price_bits(theta: float, lam: np.ndarray, omega: np.ndarray, a: np.ndarray) -> float:
    """Firewall price bits. [P1 Prop. 6 Eq. 15]"""
    raise stub(
        "nidar/video/floor/designer.py:firewall_price_bits",
        "P1 Prop. 6 Eq. 15",
        WAITS_FOR,
    )


def floor_payload_bits(
    theta: float, lam: np.ndarray, omega: np.ndarray, a: np.ndarray, delta_q: float, b_meta: int
) -> float:
    """Floor payload bits. [P1 Eq. 16-17]"""
    raise stub(
        "nidar/video/floor/designer.py:floor_payload_bits",
        "P1 Eq. 16-17",
        WAITS_FOR,
    )
