"""Outage rates for L independent Rayleigh blocks; ideal fixed-rate, rateless and ergodic floor shares.

R_eps(L, gamma_bar) = eps-quantile of L^-1 sum_l log2(1 + gamma_bar X_l), X_l ~ Exp(1); an ideal code
needs n_F = B_F / R_eps [P1 §6.4, Table 9]. Ideal rateless code with deadline n_max = B_F / R_eps stops at
B_F / R(X) [P1 §6.6].
"""
from __future__ import annotations

import math

import numpy as np

_LAG_X, _LAG_W = np.polynomial.laguerre.laggauss(80)   # 80 nodes: exact to ~1e-12 here, no overflow


def ergodic_rate(mean_snr_db: float) -> float:
    """E log2(1 + gamma_bar X), X ~ Exp(1), by Gauss-Laguerre quadrature."""
    g = 10.0 ** (mean_snr_db / 10.0)
    return float(np.dot(_LAG_W, np.log2(1.0 + g * _LAG_X)))


def _block_rates(L: int, mean_snr_db: float, draws: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    g = 10.0 ** (mean_snr_db / 10.0)
    out = np.empty(draws)
    step = max(1, 2_000_000 // L)
    for s in range(0, draws, step):
        e = min(draws, s + step)
        out[s:e] = np.log2(1.0 + g * rng.exponential(size=(e - s, L))).mean(axis=1)
    return out


def _outage_rate_two_blocks(mean_snr_db: float, eps: float) -> float:
    """Exact R_eps for L = 2 by quadrature of P[log2(1+gX1) + log2(1+gX2) <= 2r] over X1, then bisection."""
    g = 10.0 ** (mean_snr_db / 10.0)
    x = np.linspace(0.0, 60.0, 400_001)
    w = np.exp(-x)

    def cdf(r: float) -> float:
        t = (2.0 ** (2.0 * r) / (1.0 + g * x) - 1.0) / g
        return float(np.trapz(np.where(t > 0, -np.expm1(-np.maximum(t, 0.0)), 0.0) * w, x))

    lo, hi = 0.0, math.log2(1.0 + g) * 2
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if cdf(mid) < eps else (lo, mid)
    return lo


def outage_rate(L: int, mean_snr_db: float, eps: float, draws: int = 4_000_000, seed: int = 0) -> float:
    """R_eps(L, gamma_bar) in bit per channel use. Exact for L = 1 (Exp quantile) and L = 2 (quadrature);
    Monte Carlo for L >= 3."""
    g = 10.0 ** (mean_snr_db / 10.0)
    if L == 1:
        return math.log2(1.0 + g * -math.log1p(-eps))
    if L == 2:
        return _outage_rate_two_blocks(mean_snr_db, eps)
    return float(np.quantile(_block_rates(L, mean_snr_db, draws, seed), eps))


def ideal_floor_fraction(b_bits: float, n_total: float, L: int, mean_snr_db: float, eps: float,
                         draws: int = 4_000_000, seed: int = 0) -> float:
    """n_F / n for an ideal outage-limited code [P1 Table 9]; L = 0 means ergodic (L -> infinity)."""
    rate = ergodic_rate(mean_snr_db) if L == 0 else outage_rate(L, mean_snr_db, eps, draws, seed)
    return b_bits / rate / n_total


def ideal_rateless_mean_fraction(b_bits: float, n_total: float, L: int, mean_snr_db: float, eps: float,
                                 draws: int = 4_000_000, seed: int = 0) -> float:
    """Mean floor share of an ideal rateless code with deadline n_max = B_F / R_eps [P1 §6.6]."""
    rates = _block_rates(L, mean_snr_db, draws, seed)
    n_max = b_bits / float(np.quantile(rates, eps))
    return float(np.minimum(b_bits / rates, n_max).mean()) / n_total
