"""Uniform scalar quantiser for the firewalled floor; no state from earlier GoPs [P1 §5.1 E4, §5.2, A6].

The paper fixes the target (each coded coefficient i in F reaches D_i <= theta_F, assumption A6) and the
ideal Gaussian test channel of Prop. 4 / Prop. 9: U = c + N_f, Var N_f = theta_F lambda / (lambda - theta_F),
c_hat^F = (1 - theta_F / lambda) U. It does not give the step size. Here the step is chosen so the uniform
quantisation noise has that test-channel variance at high resolution, Delta^2 / 12 = theta_F lambda /
(lambda - theta_F), and U := Q(c). At low resolution (lambda close to theta_F) A6 can fail; the end-to-end
simulation measures how often (eps_q of Thm 4). This is an interpretation, recorded in OPEN_QUESTIONS OQ-33.
"""
from __future__ import annotations

import numpy as np


def step_sizes(lam: np.ndarray, theta_f: float) -> np.ndarray:
    """Delta_i for coded coefficients (lambda_i > theta_F); inf where the coefficient is not coded."""
    lam = np.asarray(lam, dtype=float)
    coded = lam > theta_f
    out = np.full(lam.shape, np.inf)
    out[coded] = np.sqrt(12.0 * theta_f * lam[coded] / (lam[coded] - theta_f))
    return out


def quantise(coeffs: np.ndarray, steps: np.ndarray) -> np.ndarray:
    """Mid-tread uniform quantiser indices round(c / Delta)."""
    return np.rint(np.asarray(coeffs, dtype=float) / steps).astype(np.int64)


def dequantise(indices: np.ndarray, steps: np.ndarray) -> np.ndarray:
    """U = k Delta."""
    return np.asarray(indices, dtype=float) * steps


def floor_estimate(u: np.ndarray, lam: np.ndarray, theta_f: float) -> np.ndarray:
    """c_hat^F = (1 - theta_F / lambda) U for i in F, 0 otherwise [P1 Prop. 9 proof]."""
    lam = np.asarray(lam, dtype=float)
    return np.where(lam > theta_f, (1.0 - theta_f / lam) * u, 0.0)
