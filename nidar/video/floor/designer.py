"""Floor water level theta_F, reference / intra rates, firewall price, floor payload.

D(theta) = k^-1 sum min{theta, lambda_i}; R_ref(D) = sum 1/2 log2+((omega_i + a_i^2 theta) / theta)
[P1 Def. 5 Eq. 12]; R_intra = sum 1/2 log2+(lambda_i / theta) [Eq. 13]; firewall price
pi_g = R_intra - R_ref [P1 Prop. 6 Eq. 15]; theta_F solves R_ref(D(theta)) = T_min T_g [P1 Def. 7, E3];
B_F = R_intra(D_F) + |F| Delta_q + B_meta [P1 Eq. 16-17]. All rates in bits per GoP.
Optional ``counts``: the arrays are per chunk and each entry stands for ``counts`` identical coefficients
(exactly equivalent to expanding them; used by the GoP pipeline for speed).
"""
from __future__ import annotations

import numpy as np

HIGH_RES_DELTA_Q = 0.5 * np.log2(np.pi * np.e / 6.0)   # ~0.2546 bit [P1 §5.2]


def _arr(x: np.ndarray | float) -> np.ndarray:
    return np.asarray(x, dtype=float)


def _w(lam: np.ndarray, counts: np.ndarray | None) -> np.ndarray:
    return np.ones_like(lam) if counts is None else _arr(counts)


def distortion_level(theta: float, lam: np.ndarray, counts: np.ndarray | None = None) -> float:
    """D(theta) = k^-1 sum min{theta, lambda_i} [P1 §4.5]."""
    lam = _arr(lam)
    w = _w(lam, counts)
    return float((np.minimum(theta, lam) * w).sum() / w.sum())


def water_level_for_distortion(d: float, lam: np.ndarray, counts: np.ndarray | None = None) -> float:
    """theta(D): unique solution of sum min{theta, lambda_i} = k D, for 0 < D <= mean(lambda) [P1 §4.5]."""
    lam = _arr(lam)
    mean = distortion_level(float(lam.max()), lam, counts)
    if not 0 < d <= mean * (1 + 1e-12):
        raise ValueError(f"D={d} must be in (0, mean(lambda)={mean}]")
    lo, hi = 0.0, float(lam.max())
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if distortion_level(mid, lam, counts) < d else (lo, mid)
    return hi


def reference_rate_bits(theta: float, lam: np.ndarray, omega: np.ndarray, a: np.ndarray,
                        counts: np.ndarray | None = None) -> float:
    """R_ref at water level theta [P1 Eq. 12]. Terms with lambda_i <= theta vanish (Corollary 2)."""
    lam, omega, a = _arr(lam), _arr(omega), _arr(a)
    w = _w(lam, counts)
    coded = lam > theta
    return float((0.5 * np.log2((omega[coded] + a[coded] ** 2 * theta) / theta) * w[coded]).sum())


def intra_rate_bits(theta: float, lam: np.ndarray, counts: np.ndarray | None = None) -> float:
    """R_intra at water level theta [P1 Eq. 13]."""
    lam = _arr(lam)
    return float((0.5 * np.log2(np.maximum(lam / theta, 1.0)) * _w(lam, counts)).sum())


def firewall_price_bits(theta: float, lam: np.ndarray, omega: np.ndarray, a: np.ndarray,
                        counts: np.ndarray | None = None) -> float:
    """pi_g = sum_{lambda_i > theta} 1/2 log2(lambda_i / (omega_i + a_i^2 theta)) [P1 Prop. 6 Eq. 15]."""
    lam, omega, a = _arr(lam), _arr(omega), _arr(a)
    w = _w(lam, counts)
    coded = lam > theta
    return float((0.5 * np.log2(lam[coded] / (omega[coded] + a[coded] ** 2 * theta)) * w[coded]).sum())


def water_level(lam: np.ndarray, omega: np.ndarray, a: np.ndarray, t_min_bps: float, t_g: float,
                counts: np.ndarray | None = None) -> float:
    """theta_F with R_ref(D(theta_F)) = T_min T_g, theta_F in (0, max lambda] [P1 Def. 7, E3].
    R_ref is non-increasing in theta, so bisection in log(theta) is exact to float precision."""
    target = t_min_bps * t_g
    lam = _arr(lam)
    hi = float(lam.max())
    lo = hi * 1e-15
    if reference_rate_bits(lo, lam, omega, a, counts) < target:
        raise ValueError("T_min T_g exceeds the rate available from this variance field")
    for _ in range(300):
        mid = float(np.sqrt(lo * hi))
        lo, hi = (mid, hi) if reference_rate_bits(mid, lam, omega, a, counts) > target else (lo, mid)
    return float(np.sqrt(lo * hi))


def floor_payload_bits(theta: float, lam: np.ndarray, omega: np.ndarray, a: np.ndarray, delta_q: float,
                       b_meta: int, counts: np.ndarray | None = None) -> float:
    """B_F = R_intra(D_F) + |F| Delta_q + B_meta [P1 Eq. 16]."""
    lam = _arr(lam)
    coded = float(((lam > theta) * _w(lam, counts)).sum())
    return intra_rate_bits(theta, lam, counts) + coded * delta_q + b_meta
