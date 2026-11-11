"""Block-Rayleigh fading channel for the floor block.

L blocks per GoP, gain constant within a block, power gains Exp(1) (h ~ CN(0, 1)) [P1 §6.1, §6.4].
Optional correlation across GoPs (``corr``): each block's complex gain follows
h_g = corr * h_{g-1} + sqrt(1 - corr^2) w_g, which keeps the Exp(1) marginal; corr = 0 gives the
independent blocks the paper's certificate assumes. Correlated blocks are what Table 13 phase 2 asks for
[P1 Table 13].
"""
from __future__ import annotations

import numpy as np


def complex_gains(L: int, gops: int, seed: int, corr: float = 0.0) -> np.ndarray:
    """Complex block gains, shape (gops, L)."""
    if not 0.0 <= corr < 1.0:
        raise ValueError("corr must be in [0, 1)")
    rng = np.random.default_rng(seed)
    w = (rng.standard_normal((gops, L)) + 1j * rng.standard_normal((gops, L))) * np.sqrt(0.5)
    if corr == 0.0:
        return w
    h = np.empty_like(w)
    h[0] = w[0]
    s = np.sqrt(1.0 - corr * corr)
    for g in range(1, gops):
        h[g] = corr * h[g - 1] + s * w[g]
    return h


def block_gains(L: int, gops: int, seed: int, corr: float = 0.0) -> np.ndarray:
    """Power gains |h|^2, shape (gops, L), marginally Exp(1) [P1 §6.1]."""
    return np.abs(complex_gains(L, gops, seed, corr)) ** 2


def mutual_information_bits(gains: np.ndarray, mean_snr_db: float, m: float) -> np.ndarray:
    """Per-GoP accumulated information m sum_l log2(1 + gamma_bar X_l), the quantity whose eps-quantile
    defines the outage rate [P1 §6.4]."""
    g = 10.0 ** (mean_snr_db / 10.0)
    return m * np.log2(1.0 + g * gains).sum(axis=-1)
