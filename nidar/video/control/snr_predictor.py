"""Delayed, noisy SNR prediction and the chance-constrained margin rule.

A7: s_g - mu_s = rho (s_{g-1} - mu_s) + w_g (dB), stationary std sigma_s; report s_hat_{g-d} = s_{g-d} + eps,
eps ~ N(0, sigma_m^2), delivered d groups late [P1 §C.2 A7].
P_pred(d) = rho^{2d} P_f + sigma_s^2 (1 - rho^{2d}), P_f = D_inf(1/sigma_m^2) of Eq. 10 with a = rho,
omega = sigma_s^2 (1 - rho^2) [P1 Lemma 8 Eq. 38]. Design gamma_d = s_pred - z_eta sqrt(P_pred(d)), failure
<= eta + eps_core under A7-A8 [P1 Thm 3]. Cost of a margin [P1 Eq. 39, Table 19].
"""
from __future__ import annotations

import math

from nidar.common.contracts import SnrReport
from nidar.video.certificates.sizing import q_inv
from nidar.video.decoder import kalman_steady_state


def filtered_variance(rho: float, sigma_s: float, sigma_m: float) -> float:
    """P_f [P1 Eq. 38]."""
    return float(kalman_steady_state(rho, sigma_s**2 * (1.0 - rho**2), 1.0 / sigma_m**2))


def prediction_variance(d: int | None, rho: float, sigma_s: float, sigma_m: float) -> float:
    """P_pred(d) in dB^2; ``d = None`` means no feedback (P_pred = sigma_s^2) [P1 Lemma 8, Table 19 'none']."""
    if d is None:
        return sigma_s**2
    r2d = rho ** (2 * d)
    return r2d * filtered_variance(rho, sigma_s, sigma_m) + sigma_s**2 * (1.0 - r2d)


def margin_db(d: int | None, rho: float, sigma_s: float, sigma_m: float, eta: float) -> float:
    """z_eta sqrt(P_pred(d)) [P1 Thm 3, Table 19]."""
    return q_inv(eta) * math.sqrt(prediction_variance(d, rho, sigma_s, sigma_m))


def floor_increase(snr_db: float, margin: float) -> float:
    """Fractional increase of floor channel uses, C(gamma)/C(gamma/10^{M/10}) - 1 (first order) [P1 §C.2]."""
    g = 10.0 ** (snr_db / 10.0)
    return math.log2(1.0 + g) / math.log2(1.0 + g / 10.0 ** (margin / 10.0)) - 1.0


def sensitivity_per_db(snr_db: float) -> float:
    """|d ln n_F / d gamma_dB| = gamma ln10/10 / ((1+gamma) ln(1+gamma)) [P1 Eq. 39]."""
    g = 10.0 ** (snr_db / 10.0)
    return g * math.log(10.0) / 10.0 / ((1.0 + g) * math.log1p(g))


def time_constant_to_rho(t_g: float, correlation_time: float) -> float:
    """rho = exp(-T_g / tau): consistent with Table 19 (T_g = 8/30 s, tau = 2 s -> 0.875)."""
    return math.exp(-t_g / correlation_time)


class KalmanSnrPredictor:
    """Implements ``SnrPredictor``: scalar Kalman filter on delayed reports, predicted d groups ahead.
    The A7 parameters must be measured on the real link (OQ-03); none has a default."""

    def __init__(self, mean_db: float, rho: float, sigma_s: float, sigma_m: float, delay: int) -> None:
        self.mu, self.rho, self.sigma_s, self.sigma_m, self.delay = mean_db, rho, sigma_s, sigma_m, delay
        self._m = mean_db                # posterior mean at the latest reported group
        self._p = sigma_s**2             # posterior variance there
        self._last_g: int | None = None

    def update(self, report: SnrReport) -> None:
        """[P1 Lemma 3 / Lemma 8 recursion]: propagate to the reported group, then fuse the report."""
        steps = 1 if self._last_g is None else max(1, report.gop_index - self._last_g)
        for _ in range(steps):
            self._m = self.mu + self.rho * (self._m - self.mu)
            self._p = self.rho**2 * self._p + self.sigma_s**2 * (1.0 - self.rho**2)
        k = self._p / (self._p + self.sigma_m**2)
        self._m = self._m + k * (report.mean_snr_db - self._m)
        self._p = (1.0 - k) * self._p
        self._last_g = report.gop_index

    def predicted(self) -> tuple[float, float]:
        """(mean, variance) of s for the group ``delay`` steps after the latest report."""
        r = self.rho**self.delay
        return self.mu + r * (self._m - self.mu), r * r * self._p + self.sigma_s**2 * (1.0 - r * r)

    def design_snr_db(self, eps: float) -> float:
        """gamma_d = s_pred - z_eps sqrt(P_pred) [P1 Thm 3]."""
        mean, var = self.predicted()
        return mean - q_inv(eps) * math.sqrt(var)
