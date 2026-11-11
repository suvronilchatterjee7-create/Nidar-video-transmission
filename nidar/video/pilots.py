"""Pilot-based channel estimation and pilot-count optimisation.

N_p pilots per block of m uses: sigma_e^2 = 1 / (1 + N_p gamma_bar), h_hat ~ CN(0, 1 - sigma_e^2);
R(N_p) = (m - N_p)/m E log2(1 + gamma_bar |h_hat|^2 / (sigma_e^2 gamma_bar + 1)) [P1 §C.1 Eq. 35, Table 18].
The paper evaluates the expectation by 4e5 Monte-Carlo draws; here it is computed by Gauss-Laguerre
quadrature (|h_hat|^2 is exponential), so it is exact up to quadrature error.
"""
from __future__ import annotations

import numpy as np

from nidar.common.contracts import PilotPlan

_X, _W = np.polynomial.laguerre.laggauss(80)


def _mean_log2_1p_exp(c: float) -> float:
    """E log2(1 + c X), X ~ Exp(1)."""
    return float(np.dot(_W, np.log2(1.0 + c * _X)))


def estimation_error_variance(n_p: int, snr: float) -> float:
    return 1.0 / (1.0 + n_p * snr)


def rate_with_pilots(m: int, n_p: int, snr_db: float) -> float:
    """[P1 Eq. 35] in bit per channel use."""
    g = 10.0 ** (snr_db / 10.0)
    if not 0 <= n_p < m:
        raise ValueError("need 0 <= N_p < m")
    s2 = estimation_error_variance(n_p, g)
    c = g * (1.0 - s2) / (s2 * g + 1.0)
    return (m - n_p) / m * _mean_log2_1p_exp(c)


def perfect_csi_rate(snr_db: float) -> float:
    """Last row of [P1 Table 18]: perfect channel knowledge, no pilots."""
    return _mean_log2_1p_exp(10.0 ** (snr_db / 10.0))


def optimal_pilots(m: int, snr_db: float) -> tuple[PilotPlan, float]:
    """(N_p*, rate) maximising Eq. 35 over 1 <= N_p < m [P1 Table 18]."""
    rates = [rate_with_pilots(m, n, snr_db) for n in range(1, m)]
    best = int(np.argmax(rates)) + 1
    return PilotPlan(block_len_m=m, pilots_per_block=best), rates[best - 1]
