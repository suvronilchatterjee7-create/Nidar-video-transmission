"""Floor-power stationarity and the damped controller restricted to the certified grid.

f(gamma) = (1 + gamma) ln(1 + gamma) - gamma; stationary point f(gamma_F) = 2 zeta / (xi nu_c)
[P1 Prop. 14 Eq. 32]. Gamma(gamma_F) = f^-1(2 zeta(gamma_F) / (xi(gamma_F) nu_c)); damped iteration
gamma_F+ = (1 - beta) gamma_F + beta Gamma(gamma_F) [P1 Eq. 40], locally convergent iff
0 < beta < 2 / (1 + |s|) [P1 Prop. 17]. Every iterate is rounded to a certified design not below the
requested power, so the floor guarantee holds for any trajectory [P1 Prop. 18, Thm 4].
Iteration is in dB (the paper reports gamma_F in dB).
"""
from __future__ import annotations

import math
from typing import Callable

from nidar.common.contracts import CertifiedFloorDesign
from nidar.video.certificates.grid import CertifiedGrid


def stationarity_lhs(gamma_f: float) -> float:
    """f(gamma) = (1 + gamma) ln(1 + gamma) - gamma, linear gamma [P1 Eq. 32 left side]."""
    return (1.0 + gamma_f) * math.log1p(gamma_f) - gamma_f


def f_inverse(y: float) -> float:
    """f^-1 on [0, inf): f is strictly increasing from 0 [P1 Prop. 14]."""
    if y <= 0:
        return 0.0
    lo, hi = 0.0, 1.0
    while stationarity_lhs(hi) < y:
        hi *= 2.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if stationarity_lhs(mid) < y else (lo, mid)
    return 0.5 * (lo + hi)


def damped_step_db(gamma_db: float, gamma_map_db: Callable[[float], float], beta: float) -> float:
    """One step of [P1 Eq. 40] in dB."""
    return (1.0 - beta) * gamma_db + beta * gamma_map_db(gamma_db)


class DampedFloorController:
    """Implements ``FloorController``.

    ``grids`` maps the design mean SNR (dB) a grid was certified for to that grid. Under A8 (certificate
    non-increasing in the actual SNR [P1 §C.2]) a grid certified for a lower design SNR stays valid at a
    higher one, so the controller uses the grid with the largest certified SNR not above the requested one.
    """

    def __init__(self, grids: dict[float, CertifiedGrid], gamma_map_db: Callable[[float], float], beta: float,
                 gamma0_db: float) -> None:
        if not grids:
            raise ValueError("at least one certified grid is required [P1 Prop. 18]")
        self.grids = dict(sorted(grids.items()))
        self.gamma_map_db = gamma_map_db
        self.beta = beta
        self.gamma_db = gamma0_db

    def step(self, design_snr_db: float, n_available: int) -> CertifiedFloorDesign | None:
        """Advance Eq. 40 once and return a certified design, or None if none fits (OQ-24)."""
        usable = [s for s in self.grids if s <= design_snr_db]
        if not usable:
            return None
        self.gamma_db = damped_step_db(self.gamma_db, self.gamma_map_db, self.beta)
        return self.grids[max(usable)].nearest_not_below(self.gamma_db, n_available)
