"""Paper 1's synthetic Gauss-Markov experiment (floor power sweep and controller), re-built from the text.

Stated set-up [P1 §B.2 "Numerical illustration", Table 16; §C.3]: lambda_i = 1e3 (1 + i/20)^-2, k = 2e4
(8e3 for the controller), a = 0.9, omega_i = (1 - a^2) lambda_i, W = 5 MHz, T_g = 8/30 s, mean SNR 10 dB,
theta_F set by T_min = 2 Mbps (credited 0.0482 bit/coefficient), payload B_F / k = 0.093 including the
firewall price, side-information recursion (9) iterated to convergence, throughput scaled to 720p at G = 8.

Choices the paper does NOT state, made here and reported with the results (docs/VIDEO_SUBSYSTEM.md §11):
- index i runs 0..k-1 (identified, not tuned: it is the only one of 0/1 that gives the stated
  theta_F = 0.206 and B_F/k = 0.093);
- the synthetic GoP gets the 720p30, G = 8 channel-use budget per coefficient: n = W T_g k / k_720p;
- B_F = R_intra(D_F) (credited + firewall price, no Delta_q / metadata), so B_F/k is computed, not set;
- floor uses n_F = B_F / log2(1 + gamma_F) (first order, as Prop. 14 assumes);
- energy budget n P_bar with P_bar = 10^(SNR/10), nu_c = 1; refinement gets E - n_F gamma_F spread over
  M = 2 (n - n_F) real dimensions, noise per real dimension nu = nu_c / 2;
- T_eq from the mean distortion via the reference rate [P1 Def. 6], scaled by k_720p / k.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from nidar.video.decoder import posterior_after_floor, transmitted_variance
from nidar.video.floor.designer import (
    intra_rate_bits,
    reference_rate_bits,
    water_level,
    water_level_for_distortion,
)
from nidar.video.refinement.allocator import allocate

K_720P = 1280 * 720 * 3 // 2 * 8      # 4:2:0 samples per GoP at 720p, G = 8 [P1 Table 1]


@dataclass
class SyntheticModel:
    k: int = 20_000
    a: float = 0.9
    w_hz: float = 5e6
    t_g: float = 8 / 30
    snr_db: float = 10.0
    t_min_bps: float = 2e6
    nu_c: float = 1.0
    index_start: int = 0          # i = 0..k-1 reproduces the stated theta_F = 0.206 and B_F/k = 0.093
    real_dim_noise_factor: float = 0.5   # nu = factor * nu_c per real dimension (unstated in the paper)
    lam: np.ndarray = field(init=False)
    omega: np.ndarray = field(init=False)
    theta_f: float = field(init=False)

    def __post_init__(self) -> None:
        i = np.arange(self.index_start, self.index_start + self.k, dtype=float)
        self.lam = 1e3 * (1.0 + i / 20.0) ** -2
        self.omega = (1.0 - self.a**2) * self.lam
        self.avec = np.full(self.k, self.a)
        # credited bits for THIS synthetic GoP: same bits per coefficient as 2 Mbps at 720p, G = 8
        self.credited_bits = self.t_min_bps * self.t_g * self.k / K_720P
        self.theta_f = water_level(self.lam, self.omega, self.avec, self.credited_bits / self.t_g, self.t_g)
        self.b_f = intra_rate_bits(self.theta_f, self.lam)
        self.n = self.w_hz * self.t_g * self.k / K_720P

    def teq_mbps(self, d: np.ndarray) -> float:
        """Reference throughput of mean distortion, scaled to 720p [P1 Def. 6]."""
        theta = water_level_for_distortion(float(np.mean(d)), self.lam)
        return reference_rate_bits(theta, self.lam, self.omega, self.avec) * K_720P / self.k / self.t_g / 1e6

    def evaluate(self, gamma_f_db: float, iterations: int = 200, tol: float = 1e-9) -> dict:
        """One row of Table 16 at floor SNR gamma_F: n_F/n, T_eq, f(gamma_F), 2 zeta / (xi nu_c)."""
        g = 10.0 ** (gamma_f_db / 10.0)
        n_f = self.b_f / np.log2(1.0 + g)
        energy = self.n * 10.0 ** (self.snr_db / 10.0) * self.nu_c
        p_ref = energy - n_f * g * self.nu_c
        m_dims = int(np.floor(2.0 * (self.n - n_f)))
        if p_ref <= 0 or m_dims <= 0:
            return {"gamma_f_db": gamma_f_db, "feasible": False}
        nu = np.full(self.k, self.nu_c * self.real_dim_noise_factor)
        vartheta = transmitted_variance(self.lam, self.theta_f)
        d = np.minimum(self.lam, self.theta_f)
        for _ in range(iterations):
            mu = self.omega + self.a**2 * d                      # [P1 Eq. 9]
            kappa = posterior_after_floor(mu, self.theta_f, self.lam)
            alloc = allocate(kappa, vartheta, nu, p_ref, max_active=m_dims)
            if np.max(np.abs(alloc.d - d)) < tol:
                d = alloc.d
                break
            d = alloc.d
        return {"gamma_f_db": gamma_f_db, "feasible": True, "nf_over_n": n_f / self.n,
                "teq_mbps": self.teq_mbps(d), "mean_d": float(np.mean(d)),
                "f_lhs": (1 + g) * np.log1p(g) - g, "price_rhs": 2 * alloc.zeta / (alloc.xi * self.nu_c),
                "xi": alloc.xi, "zeta": alloc.zeta}

    def gamma_map_db(self, gamma_f_db: float) -> float:
        """Gamma(gamma_F) = f^-1(2 zeta / (xi nu_c)) in dB [P1 §C.3]."""
        from nidar.video.control.controller import f_inverse
        row = self.evaluate(gamma_f_db)
        return 10.0 * np.log10(f_inverse(row["price_rhs"]))
