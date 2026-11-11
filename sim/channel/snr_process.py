"""Large-scale SNR process with delayed, noisy reports, and a margin-rule outage simulator.

A7: s_g - mu_s = rho (s_{g-1} - mu_s) + w_g, stationary std sigma_s; reports s_hat_{g-d} = s_{g-d} + eps,
eps ~ N(0, sigma_m^2), arriving d groups late [P1 §C.2 A7]. ``margin_rule_outage`` checks Theorem 3's
prediction part by simulation: the fraction of groups with s_g below the design point gamma_d should be
about eta [P1 Thm 3, Lemma 8].
"""
from __future__ import annotations

import math

import numpy as np

from nidar.common.contracts import SnrReport
from nidar.video.control.snr_predictor import KalmanSnrPredictor


def simulate(gops: int, mean_db: float, rho: float, sigma_s: float, sigma_m: float, delay: int,
             seed: int) -> tuple[np.ndarray, np.ndarray]:
    """(true s_g, report available at group g) in dB; reports[g] = s_{g-d} + noise, NaN for g < d."""
    rng = np.random.default_rng(seed)
    s = np.empty(gops)
    s[0] = mean_db + sigma_s * rng.standard_normal()
    innov = sigma_s * math.sqrt(1.0 - rho * rho)
    for g in range(1, gops):
        s[g] = mean_db + rho * (s[g - 1] - mean_db) + innov * rng.standard_normal()
    reports = np.full(gops, np.nan)
    reports[delay:] = s[: gops - delay] + sigma_m * rng.standard_normal(gops - delay)
    return s, reports


def margin_rule_outage(gops: int, mean_db: float, rho: float, sigma_s: float, sigma_m: float, delay: int,
                       eta: float, seed: int, burn_in: int = 50) -> float:
    """Empirical P[s_g < gamma_d] with gamma_d from the Kalman predictor and the margin rule [P1 Thm 3]."""
    s, reports = simulate(gops, mean_db, rho, sigma_s, sigma_m, delay, seed)
    pred = KalmanSnrPredictor(mean_db, rho, sigma_s, sigma_m, delay)
    below = 0
    counted = 0
    for g in range(gops):
        if g >= delay:
            pred.update(SnrReport(1, 1, g - delay, 0.0, float(reports[g]), 1))
        if g >= burn_in:
            counted += 1
            below += s[g] < pred.design_snr_db(eta)
    return below / counted
