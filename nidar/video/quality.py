"""Quality accounting: reference throughput T_eq, pre-channel distortion fraction, violation interval.

T_eq = R_ref(D) / T_g with the water level of the mean distortion [P1 Def. 5-6 Eq. 12]; it is a model
quantity (Gaussian surrogate, an upper bound on the true information function [P1 §8]).
beta_up = sum_{i in U} D_i / sum_i D_i, U = truncated components [P1 Prop. 10 Eq. 21].
Mean interval between floor violations T_g / eps_F [P1 Cor. 7].
"""
from __future__ import annotations

import numpy as np

from nidar.video.floor.designer import reference_rate_bits, water_level_for_distortion


def teq_reference_mbps(distortions: np.ndarray, lam: np.ndarray, omega: np.ndarray, a: np.ndarray,
                       t_g: float) -> float:
    """[P1 Def. 6]: R_ref(D_g) / T_g in Mbps, D_g the mean per-coefficient distortion of the GoP."""
    theta = water_level_for_distortion(float(np.mean(distortions)), lam)
    return reference_rate_bits(theta, lam, omega, a) / t_g / 1e6


def beta_up(distortions: np.ndarray, truncated: np.ndarray) -> float:
    """[P1 Prop. 10 Eq. 21]."""
    d = np.asarray(distortions, dtype=float)
    total = d.sum()
    if total <= 0:
        raise ValueError("total distortion must be > 0 (Lemma 1)")
    return float(d[np.asarray(truncated, dtype=bool)].sum() / total)


def mean_violation_interval_s(t_g: float, eps_f: float) -> float:
    """T_g / eps_F [P1 Cor. 7] (independent channel realisations across GoPs)."""
    if not 0 < eps_f < 1:
        raise ValueError("eps_F must be in (0, 1)")
    return t_g / eps_f
