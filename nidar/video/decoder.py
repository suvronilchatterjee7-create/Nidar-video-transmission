"""Decoder closed forms: scalar Kalman steady state, posterior after the floor, conditional mean.

Notation follows Paper 1: mu_i side-information variance [P1 Lemma 3 Eq. 9], kappa_i posterior after the
floor [Eq. 18], nu_i per-dimension noise, g_i analogue gain, theta_F floor water level.
Steady state D_inf(eta) [P1 Prop. 3 Eq. 10]; conditional mean [P1 Prop. 9 Eq. 20].
The D1-D5 pipeline (``HybridDecoder``) lives in ``nidar.video.receiver`` so that this module stays free of
pipeline imports (``gop_model`` depends on the closed forms here).
"""
from __future__ import annotations

import numpy as np


def kalman_steady_state(a: float | np.ndarray, omega: float | np.ndarray, eta: float | np.ndarray) -> np.ndarray:
    """Fixed point of D -> (1/(omega + a^2 D) + eta)^-1:
    D_inf = (-B + sqrt(B^2 + 4 eta a^2 omega)) / (2 eta a^2), B = 1 + eta omega - a^2;
    D_inf = omega / (1 + eta omega) for a = 0 [P1 Prop. 3 Eq. 10]."""
    a, omega, eta = (np.asarray(v, dtype=float) for v in (a, omega, eta))
    a2 = a * a
    b = 1.0 + eta * omega - a2
    # Same positive root written as 2 omega / (B + sqrt(B^2 + 4 eta a^2 omega)): no cancellation, and it
    # reduces to omega / (1 + eta omega) when a = 0 (B = 1 + eta omega).
    out = 2.0 * omega / (b + np.sqrt(b * b + 4.0 * eta * a2 * omega))
    return out[()] if out.ndim == 0 else out


def kalman_iterate(a: float, omega: float, eta: float, d0: float, steps: int) -> float:
    """The recursion of Lemma 3 / Prop. 3 iterated ``steps`` times (used to cross-check Eq. 10)."""
    d = d0
    for _ in range(steps):
        d = 1.0 / (1.0 / (omega + a * a * d) + eta)
    return d


def posterior_after_floor(mu: np.ndarray, theta_f: float, lam: np.ndarray) -> np.ndarray:
    """kappa_i = (1/mu_i + [1/theta_F - 1/lambda_i]^+)^-1 <= vartheta_i [P1 Eq. 18]."""
    mu, lam = np.asarray(mu, dtype=float), np.asarray(lam, dtype=float)
    return 1.0 / (1.0 / mu + np.maximum(1.0 / theta_f - 1.0 / lam, 0.0))


def transmitted_variance(lam: np.ndarray, theta_f: float) -> np.ndarray:
    """vartheta_i = min{lambda_i, theta_F} [P1 §5.3]."""
    return np.minimum(np.asarray(lam, dtype=float), theta_f)


def conditional_mean(z: np.ndarray, c_floor: np.ndarray, y: np.ndarray, g: np.ndarray, nu: np.ndarray,
                     mu: np.ndarray, theta_f: float, lam: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """c_hat_i = D_i [ z_i/mu_i + (1/theta_F + g_i^2/nu_i) c_hat_i^F + (g_i/nu_i) y_i ],
    1/D_i = 1/kappa_i + g_i^2/nu_i; the 1/theta_F term is absent for i not in F [P1 Prop. 9 Eq. 20].
    Returns (c_hat, D)."""
    z, c_floor, y, g, nu, mu, lam = (np.asarray(v, dtype=float) for v in (z, c_floor, y, g, nu, mu, lam))
    in_f = lam > theta_f
    kappa = posterior_after_floor(mu, theta_f, lam)
    d = 1.0 / (1.0 / kappa + g * g / nu)
    floor_weight = np.where(in_f, 1.0 / theta_f, 0.0) + g * g / nu
    return d * (z / mu + floor_weight * np.where(in_f, c_floor, 0.0) + g * y / nu), d

