"""Hard amplitude limiter: Bussgang gain and distortion, SNDR, optimal back-off.

For x ~ CN(0, sigma^2) and Lambda = A^2 / sigma^2: alpha = 1 - e^-Lambda + (sqrt(pi)/2) sqrt(Lambda)
erfc(sqrt(Lambda)), sigma_d^2 = sigma^2 (1 - e^-Lambda - alpha^2) [P1 Lemma 6 Eq. 29];
SNDR(Lambda) = alpha^2 rho_pk / ((1 - e^-Lambda - alpha^2) rho_pk + Lambda) [P1 Eq. 30]; Table 15.
"""
from __future__ import annotations

import math

import numpy as np


def bussgang(lam: float) -> tuple[float, float]:
    """(alpha, sigma_d^2 / sigma^2) for back-off Lambda (linear) [P1 Eq. 29]."""
    alpha = 1.0 - math.exp(-lam) + 0.5 * math.sqrt(math.pi) * math.sqrt(lam) * math.erfc(math.sqrt(lam))
    return alpha, 1.0 - math.exp(-lam) - alpha * alpha


def sndr(lam: float, peak_snr: float) -> float:
    """[P1 Eq. 30], linear."""
    alpha, dist = bussgang(lam)
    return alpha * alpha * peak_snr / (dist * peak_snr + lam)


def optimal_backoff(peak_snr_db: float) -> tuple[float, float, float]:
    """(Lambda* dB, SNDR* dB, shortfall dB vs a distortion-free amplifier at the same back-off) [P1 Table 15],
    by golden-section search on Lambda in dB (SNDR is unimodal in Lambda)."""
    rho = 10.0 ** (peak_snr_db / 10.0)

    def f(lam_db: float) -> float:
        return sndr(10.0 ** (lam_db / 10.0), rho)

    a, b = -20.0, peak_snr_db + 10.0
    gr = (math.sqrt(5.0) - 1.0) / 2.0
    c, d = b - gr * (b - a), a + gr * (b - a)
    for _ in range(200):
        if f(c) > f(d):
            b, d = d, c
            c = b - gr * (b - a)
        else:
            a, c = c, d
            d = a + gr * (b - a)
    lam_db = 0.5 * (a + b)
    sndr_db = 10.0 * math.log10(f(lam_db))
    return lam_db, sndr_db, (peak_snr_db - lam_db) - sndr_db


def optimal_backoff_db(peak_snr_db: float) -> float:
    return optimal_backoff(peak_snr_db)[0]


def monte_carlo_bussgang(lam: float, draws: int, seed: int) -> tuple[float, float]:
    """Monte-Carlo check of Eq. 29 (sigma = 1): alpha = E[x* y], sigma_d^2 = E|y|^2 - alpha^2 [P1 Table 20]."""
    rng = np.random.default_rng(seed)
    x = (rng.standard_normal(draws) + 1j * rng.standard_normal(draws)) * math.sqrt(0.5)
    r = np.abs(x)
    a = math.sqrt(lam)
    y = np.where(r <= a, x, a * x / np.maximum(r, 1e-300))
    alpha = float(np.mean(np.conj(x) * y).real)
    return alpha, float(np.mean(np.abs(y) ** 2)) - alpha * alpha
