"""Phase 3: reproduce Paper 1's published numbers from our own implementation (VT-01..VT-19).

Rules [TEAM-BRIEF §8 Phase 3]: every expected value below is copied from the paper; tolerances reflect the
paper's printed precision or Monte-Carlo noise; nothing is tuned. Numbers we do NOT reproduce are
``xfail(strict=True)`` with the measured value in the reason, so a future fix shows up as XPASS.
Full results: docs/REPRODUCTION_P1.md.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from nidar.video import pilots
from nidar.video.certificates import dt_bound, info_density, kl_certificate, outage, sizing
from nidar.video.control import snr_predictor
from nidar.video.control.controller import damped_step_db, f_inverse, stationarity_lhs
from nidar.video.decoder import (
    conditional_mean,
    kalman_iterate,
    kalman_steady_state,
    posterior_after_floor,
)
from nidar.video.floor import designer
from nidar.video.refinement import allocator, limiter

N_GOP = 5e6 * 8 / 30           # W T_g at W = 5 MHz, T_g = 8/30 s [P1 Table 9]
B_F = 533_333                  # 2 Mbps x 8/30 s


# ---------------- VT-01 firewall price [P1 Table 5] ----------------
@pytest.mark.parametrize("a, ref, price", [(0.50, 3.117, 0.205), (0.80, 2.598, 0.724), (0.90, 2.154, 1.168),
                                           (0.95, 1.707, 1.615), (0.99, 0.785, 2.537)])
def test_vt01_firewall_price_table5(a, ref, price) -> None:
    lam, theta = np.array([100.0]), 1.0
    omega, av = (1 - a * a) * lam, np.array([a])
    assert designer.intra_rate_bits(theta, lam) == pytest.approx(3.322, abs=5e-4)
    assert designer.reference_rate_bits(theta, lam, omega, av) == pytest.approx(ref, abs=5e-4)
    assert designer.firewall_price_bits(theta, lam, omega, av) == pytest.approx(price, abs=5e-4)


# ---------------- VT-02 Kalman steady state [P1 Prop. 3, Table 14] ----------------
def test_vt02_kalman_steady_state() -> None:
    d = kalman_steady_state(0.9, 0.19, 3.0)
    assert d == pytest.approx(0.164001746899620, abs=1e-15)
    assert kalman_iterate(0.9, 0.19, 3.0, 0.0, 400) == pytest.approx(d, abs=1e-14)
    assert kalman_steady_state(0.0, 0.5, 2.0) == pytest.approx(0.5 / (1 + 2 * 0.5))   # a = 0 branch


# ---------------- VT-03 posterior and conditional mean [P1 Eq. 18, Prop. 9, Table 14] ----------------
def test_vt03_posterior_variance() -> None:
    assert posterior_after_floor(0.2, 0.01, 1.0) == pytest.approx(0.009615384615, abs=1e-12)


def test_vt03_conditional_mean_is_the_mmse_estimate() -> None:
    """Monte Carlo of the generative model in the proof of Prop. 9: unbiased, error variance = D."""
    rng = np.random.default_rng(5)
    n, lam, theta_f, mu, g, nu = 400_000, 1.0, 0.1, 0.3, 2.0, 0.05
    z = rng.normal(0, 1, n)
    c = z + rng.normal(0, math.sqrt(mu), n)
    u = c + rng.normal(0, math.sqrt(theta_f * lam / (lam - theta_f)), n)
    c_floor = (1 - theta_f / lam) * u
    y = g * (c - c_floor) + rng.normal(0, math.sqrt(nu), n)
    est, d = conditional_mean(z, c_floor, y, np.full(n, g), np.full(n, nu), np.full(n, mu), theta_f, np.full(n, lam))
    err = c - est
    assert abs(err.mean()) < 4 * math.sqrt(d[0] / n)
    assert err.var() == pytest.approx(d[0], rel=0.01)


# ---------------- VT-04 allocation optimality [P1 Prop. 8, Table 14] ----------------
def _instance(rng: np.random.Generator, m: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    kappa = rng.uniform(0.01, 1.0, m)
    vartheta = kappa * rng.uniform(1.0, 3.0, m)
    nu = rng.uniform(0.01, 0.2, m)
    return kappa, vartheta, nu, float(rng.uniform(0.5, 5.0))


@pytest.mark.parametrize("seed", range(20))
def test_vt04_allocation_kkt_and_no_improving_transfer(seed) -> None:
    """Paper compared with a constrained optimiser (gap 8.1e-11). Without scipy we check the KKT conditions
    and that no random power transfer between components lowers sum D."""
    rng = np.random.default_rng(seed)
    kappa, vartheta, nu, p = _instance(rng, 40)
    al = allocator.allocate(kappa, vartheta, nu, p)
    assert al.power.sum() == pytest.approx(p, rel=1e-12)
    r = np.sqrt(al.xi * nu * vartheta)
    assert np.allclose(al.d[al.active], r[al.active], rtol=1e-6)
    assert np.all(kappa[~al.active] ** 2 <= al.xi * nu[~al.active] * vartheta[~al.active] * (1 + 1e-9))
    base = al.d.sum()
    for _ in range(200):
        i, j = rng.choice(40, 2, replace=False)
        t = rng.uniform(0, al.power[i]) if al.power[i] > 0 else 0.0
        x = al.x.copy()
        x[i] -= t / vartheta[i]
        x[j] += t / vartheta[j]
        assert (1 / (1 / kappa + x / nu)).sum() >= base - 1e-12


# ---------------- VT-05 information-density sampler [P1 Lemma 4, Table 14] ----------------
def test_vt05_information_density_moments() -> None:
    x = info_density.sample(50, np.array([10.0]), 400_000, 1) * math.log(2)     # nats
    theory_mean, theory_var = 50 * math.log(11), 50 * 20 / 11
    assert theory_mean == pytest.approx(119.89, abs=0.005) and theory_var == pytest.approx(90.91, abs=0.005)
    se = math.sqrt(theory_var / 400_000)
    assert abs(x.mean() - theory_mean) < 5 * se
    assert x.var() == pytest.approx(theory_var, rel=0.01)


def test_vt05_dispersions() -> None:
    g = 10.0
    assert info_density.v_iid(g) == pytest.approx(info_density.v_equal_energy(g) + (g / (1 + g)) ** 2
                                                   * info_density.LOG2E**2)   # [P1 Rem. 8]


# ---------------- VT-06 sizing overhead [P1 Prop. 12, Table 7] ----------------
TABLE7 = {
    (66_667, 1e-3): ((1.59, 1.25), (1.34, 0.99), (1.01, 0.72)),
    (66_667, 1e-5): ((2.14, 1.68), (1.81, 1.33), (1.36, 0.96)),
    (533_333, 1e-3): ((0.56, 0.44), (0.47, 0.35), (0.36, 0.25)),
    (533_333, 1e-5): ((0.75, 0.59), (0.63, 0.47), (0.48, 0.34)),
}


@pytest.mark.parametrize("key", list(TABLE7))
def test_vt06_table7(key) -> None:
    b, eps = key
    for snr_db, (iid, ee) in zip((5, 10, 20), TABLE7[key], strict=True):
        g = 10 ** (snr_db / 10)
        assert 100 * sizing.relative_overhead(b, g, eps, "iid") == pytest.approx(iid, abs=0.005)
        assert 100 * sizing.relative_overhead(b, g, eps, "equal_energy") == pytest.approx(ee, abs=0.005)


def test_vt06_table8_block_sizes() -> None:
    assert math.ceil(sizing.n_f_normal_approx(533_333, 10, 1e-3, "iid")) == 154_897
    assert math.ceil(sizing.n_f_normal_approx(533_333, 10, 1e-3, "equal_energy")) == 154_706


# ---------------- VT-07 DT estimator + certificate [P1 Thm 1, Prop. 11, Table 8] ----------------
@pytest.mark.parametrize("n_f, b_f, expected", [(1_000, 3_300, 5.22e-3), (1_000, 3_342, 2.98e-2),
                                                 (154_897, 533_333, 5.10e-4), (154_706, 533_333, 7.48e-3)])
def test_vt07_table8_dt_estimates(n_f, b_f, expected) -> None:
    est = dt_bound.dt_estimate(b_f + 1, n_f, None, 10.0, 1_000_000, seed=2)
    se = math.sqrt(expected / 1_000_000)          # integrand in [0,1]: Var <= mean
    assert abs(est.p_hat - expected) < 5 * se + 0.01 * expected
    assert est.p_bar >= est.p_hat


def test_vt07_table8_v_rule_misses_target() -> None:
    """The V(gamma) rule misses eps_F/2 by factors 6 and 15 for i.i.d. inputs [P1 §6.3]."""
    small = dt_bound.dt_estimate(3_343, 1_000, None, 10.0, 400_000, seed=3).p_hat / 5e-3
    large = dt_bound.dt_estimate(533_334, 154_706, None, 10.0, 400_000, seed=3).p_hat / 5e-4
    assert 5.5 < small < 6.5 and 14 < large < 16


def test_vt07_kl_certificate_properties() -> None:
    assert kl_certificate.upper_bound(5.22e-3, 1_000_000, 1e-6) == pytest.approx(5.61e-3, abs=0.02e-3)
    assert kl_certificate.upper_bound(0.0, 1000, 1e-6) == pytest.approx(1 - 1e-6 ** (1 / 1000), rel=1e-6)


# ---------------- VT-08 block fading [P1 Table 9, Cor. 6] ----------------
@pytest.mark.parametrize("L, expected", [(4, 0.435), (8, 0.271), (16, 0.212), (64, 0.167), (256, 0.151),
                                         (0, 0.138)])
def test_vt08_table9_ideal(L, expected) -> None:
    """The 1e-3 quantile needs many draws for few blocks: 2e6 draws gave 0.4333 at L = 4 while 2e7 draws
    give 0.4363 +- 0.0005 (3 seeds). Tolerance 0.6 % relative covers the paper's own Monte-Carlo noise."""
    draws = 10_000_000 if 0 < L <= 16 else 2_000_000
    got = outage.ideal_floor_fraction(B_F, N_GOP, L, 10.0, 1e-3, draws=draws, seed=0)
    assert got == pytest.approx(expected, rel=0.006)


@pytest.mark.xfail(strict=True, reason="not reproduced: exact quantile gives 27.85 (paper 27.74), -0.4 %")
def test_vt08_table9_ideal_L1() -> None:
    assert outage.ideal_floor_fraction(B_F, N_GOP, 1, 10.0, 1e-3) == pytest.approx(27.74, abs=0.01)


@pytest.mark.xfail(strict=True, reason="not reproduced: exact quadrature gives 1.397 (paper 1.409), -0.9 %")
def test_vt08_table9_ideal_L2() -> None:
    assert outage.ideal_floor_fraction(B_F, N_GOP, 2, 10.0, 1e-3) == pytest.approx(1.409, abs=0.002)


def test_vt08_L_le_2_infeasible_conclusion_holds() -> None:
    """Cor. 6's conclusion is unaffected by the small L = 1, 2 mismatches: both exceed the whole GoP."""
    assert outage.ideal_floor_fraction(B_F, N_GOP, 1, 10.0, 1e-3) > 1
    assert outage.ideal_floor_fraction(B_F, N_GOP, 2, 10.0, 1e-3) > 1


def test_vt08_certified_L16_design_point_and_a8() -> None:
    """Paper's certified L = 16 design n_F = 297,376 (22.3 %) and its A8 check at 8..12 dB [P1 §C.2]."""
    paper = {8: 2.1e-2, 9: 3.2e-3, 10: 3.7e-4, 11: 4e-5}
    for snr_db, expected in paper.items():
        p = dt_bound.dt_estimate(B_F + 1, 297_376, 16, snr_db, 600_000, seed=7).p_hat
        assert abs(p - expected) < 5 * math.sqrt(expected / 600_000) + 0.05 * expected, snr_db
    assert dt_bound.dt_estimate(B_F + 1, 297_376, 16, 12, 600_000, seed=7).p_hat < 1e-5


@pytest.mark.slow
@pytest.mark.parametrize("L, expected, lo, hi", [(4, 0.521, 0.45, 0.60), (8, 0.298, 0.25, 0.36),
                                                 (16, 0.223, 0.19, 0.26), (64, 0.171, 0.15, 0.20)])
def test_vt08_table9_certified(L, expected, lo, hi) -> None:
    """Certified search (1e6 draws, delta = 1e-6). Measured 0.515 / 0.296 / 0.221 / 0.170: within ~1 %."""
    n_f, est = dt_bound.certify_floor(B_F, L, 10.0, 1e-3, int(lo * N_GOP), int(hi * N_GOP), 1_000_000, 11)
    assert n_f / N_GOP == pytest.approx(expected, rel=0.015)
    assert est.p_bar <= 5e-4


# ---------------- VT-09..11 AWGN share, segmentation, rateless [P1 Table 10, Prop. 13, §6.6] ----------------
@pytest.mark.parametrize("w_mhz, row", [(1, (97.8, 58.1, 30.1)), (5, (19.6, 11.6, 6.0)), (20, (4.9, 2.9, 1.5))])
def test_vt09_table10(w_mhz, row) -> None:
    for snr_db, expected in zip((5, 10, 20), row, strict=True):
        n = w_mhz * 1e6 * 8 / 30
        assert 100 * sizing.n_f_normal_approx(B_F, 10 ** (snr_db / 10), 1e-3) / n == pytest.approx(expected, abs=0.05)


def test_vt10_segmentation_penalty() -> None:
    assert 100 * sizing.segmentation_overhead(B_F, 10.0, 1e-3, 1) == pytest.approx(0.47, abs=0.005)
    assert 100 * sizing.segmentation_overhead(B_F, 10.0, 1e-3, 64) == pytest.approx(4.95, abs=0.005)


@pytest.mark.parametrize("L, expected", [(4, 0.146), (16, 0.139), (64, 0.138)])
def test_vt11_ideal_rateless(L, expected) -> None:
    got = outage.ideal_rateless_mean_fraction(B_F, N_GOP, L, 10.0, 1e-3, draws=2_000_000, seed=0)
    assert got == pytest.approx(expected, abs=0.0015)


# ---------------- VT-12 limiter [P1 Lemma 6, Table 15, Table 20] ----------------
@pytest.mark.parametrize("pk, lam, s, short", [(10, 0.75, 6.42, 2.83), (15, 2.85, 10.35, 1.80),
                                               (20, 4.41, 14.34, 1.25), (25, 5.63, 18.42, 0.95),
                                               (30, 6.63, 22.61, 0.76)])
def test_vt12_table15(pk, lam, s, short) -> None:
    got = limiter.optimal_backoff(pk)
    assert got == pytest.approx((lam, s, short), abs=0.006)


@pytest.mark.parametrize("lam", [1, 2, 4, 8])
def test_vt12_bussgang_monte_carlo(lam) -> None:
    """Paper: |d alpha| <= 3e-4, |d sigma_d^2| <= 2e-5 with 4e6 draws. We test against 5 standard errors
    (our worst observed |d alpha| was 9e-4 = ~2 SE: consistent, but not as tight as the paper's run)."""
    a, d = limiter.bussgang(lam)
    am, dm = limiter.monte_carlo_bussgang(lam, 4_000_000, lam)
    assert abs(a - am) < 5 * 1.0 / math.sqrt(4_000_000)
    assert abs(d - dm) < 5 * 2.0 / math.sqrt(4_000_000)


# ---------------- VT-13 floor power sweep [P1 Prop. 14, Table 16] ----------------
@pytest.fixture(scope="module")
def synthetic():
    from sim.video.synthetic_model import SyntheticModel
    return SyntheticModel()


def test_vt13_stated_intermediates(synthetic) -> None:
    assert synthetic.theta_f == pytest.approx(0.206, abs=0.0005)
    assert synthetic.credited_bits / synthetic.k == pytest.approx(0.0482, abs=5e-5)
    assert synthetic.b_f / synthetic.k == pytest.approx(0.093, abs=5e-4)


@pytest.mark.parametrize("gdb, nf, f", [(6, 0.333, 4.02), (8, 0.269, 8.23), (9, 0.244, 11.65), (10, 0.223, 16.38),
                                        (10.5, 0.214, 19.37), (11, 0.205, 22.87), (12, 0.189, 31.74),
                                        (14, 0.164, 60.10)])
def test_vt13_table16_analytic_columns(synthetic, gdb, nf, f) -> None:
    g = 10 ** (gdb / 10)
    assert synthetic.b_f / math.log2(1 + g) / synthetic.n == pytest.approx(nf, abs=0.0015)
    assert stationarity_lhs(g) == pytest.approx(f, abs=0.006)


@pytest.mark.slow
@pytest.mark.xfail(strict=True, reason="not reproduced: T_eq 10.66 Mbps at 10 dB (paper 9.776), optimum at 10 dB "
                                       "(paper 10.5), mean D 4.89e-3 (paper 5.399e-3); set-up underspecified")
def test_vt13_table16_throughput(synthetic) -> None:
    assert synthetic.evaluate(10.0)["teq_mbps"] == pytest.approx(9.776, abs=0.01)


@pytest.mark.slow
def test_vt13_stationary_point_below_sweep_optimum(synthetic) -> None:
    """Structural claim reproduced: f rises and 2 zeta/(xi nu_c) falls, so Eq. 32 has one crossing, below the
    sweep optimum, on a flat objective [P1 §B.2]."""
    rows = [synthetic.evaluate(g) for g in (8.0, 9.0, 10.0, 11.0)]
    f = [r["f_lhs"] for r in rows]
    price = [r["price_rhs"] for r in rows]
    assert all(np.diff(f) > 0) and all(np.diff(price) < 0)
    assert f[0] < price[0] and f[2] > price[2]
    teq = [r["teq_mbps"] for r in rows]
    assert max(teq) - min(teq) < 0.02 * max(teq)


# ---------------- VT-14 mismatch regret [P1 Prop. 15, Table 17] ----------------
@pytest.mark.parametrize("delta, paper_worst", [(0.10, 1.0018), (0.25, 1.0064), (0.50, 1.0238), (1.00, 1.0622)])
def test_vt14_regret_within_bound(delta, paper_worst) -> None:
    """The instance distribution is not stated, so the paper's worst values are not reproducible; the bound
    (1+delta)^2 is what Prop. 15 proves and what we check, on 300 random instances of m = 60."""
    rng = np.random.default_rng(int(delta * 100))
    worst = 1.0
    for _ in range(300):
        kappa, vartheta, nu, p = _instance(rng, 60)
        fk = (1 + delta) ** rng.uniform(-1, 1, 60)
        fn = (1 + delta) ** rng.uniform(-1, 1, 60)
        kappa_t, nu_t = np.minimum(kappa * fk, vartheta), nu * fn
        x_star = allocator.allocate(kappa, vartheta, nu, p).x
        x_true = allocator.allocate(kappa_t, vartheta, nu_t, p).x
        d_star = (1 / (1 / kappa_t + x_star / nu_t)).sum()
        d_true = (1 / (1 / kappa_t + x_true / nu_t)).sum()
        worst = max(worst, d_star / d_true)
    assert 1.0 <= worst <= (1 + delta) ** 2
    assert worst < 1 + 0.25 * ((1 + delta) ** 2 - 1)      # bound is loose, as the paper observes


# ---------------- VT-15 pilots [P1 Eq. 35, Table 18] ----------------
TABLE18 = {50: ((5, 1.361), (4, 2.421), (3, 5.155)), 100: ((8, 1.455), (6, 2.552), (4, 5.351)),
           200: ((11, 1.527), (9, 2.650), (6, 5.499)), 500: ((18, 1.593), (14, 2.741), (10, 5.636))}


@pytest.mark.parametrize("m", list(TABLE18))
def test_vt15_table18(m) -> None:
    for snr_db, (n_p, rate) in zip((5, 10, 20), TABLE18[m], strict=True):
        plan, r = pilots.optimal_pilots(m, snr_db)
        assert plan.pilots_per_block == n_p
        assert r == pytest.approx(rate, abs=0.003)          # paper: 4e5 Monte-Carlo draws


def test_vt15_perfect_csi_row() -> None:
    assert [round(pilots.perfect_csi_rate(s), 2) for s in (5, 10, 20)] == pytest.approx([1.72, 2.91, 5.88], abs=0.01)


# ---------------- VT-16 allocation under estimation error [P1 Prop. 16, Eq. 37] ----------------
@pytest.mark.parametrize("seed", range(10))
def test_vt16_estimation_error_allocation(seed) -> None:
    rng = np.random.default_rng(100 + seed)
    kappa, vartheta, nu, p = _instance(rng, 30)
    sigma2 = rng.uniform(0.01, 0.1, 30)
    al = allocator.allocate_with_estimation_error(kappa, vartheta, nu, sigma2, p)
    assert al.power.sum() == pytest.approx(p, rel=1e-9)
    assert np.all(al.d >= allocator.precision_ceiling(kappa, vartheta, sigma2) * (1 - 1e-12))
    base = al.d.sum()

    def total(u):
        return (1 / (1 / kappa + u / (vartheta * (nu + sigma2 * u)))).sum()
    for _ in range(200):
        i, j = rng.choice(30, 2, replace=False)
        t = rng.uniform(0, al.power[i]) if al.power[i] > 0 else 0.0
        u = al.power.copy()
        u[i] -= t
        u[j] += t
        assert total(u) >= base - 1e-12


def test_vt16_limit_is_prop8() -> None:
    rng = np.random.default_rng(7)
    kappa, vartheta, nu, p = _instance(rng, 30)
    a8 = allocator.allocate(kappa, vartheta, nu, p).d.sum()
    a16 = allocator.allocate_with_estimation_error(kappa, vartheta, nu, np.full(30, 1e-6), p).d.sum()
    assert a16 == pytest.approx(a8, rel=1e-4)       # paper: 3.025342 vs 3.025335 on its own instance


def test_vt16_precision_ceiling_example() -> None:
    """N_p = 4 at 10 dB: sigma_e^2 = 1/41, so no component exceeds 16.1 dB effective SNR [P1 §C.1]."""
    assert pilots.estimation_error_variance(4, 10.0) == pytest.approx(1 / 41)
    assert 10 * math.log10(41) == pytest.approx(16.1, abs=0.05)


# ---------------- VT-17 margin rule [P1 Lemma 8, Thm 3, Eq. 39, Table 19] ----------------
TABLE19 = [(0, 0.853, 3.17, 25.0, 18.5), (1, 1.632, 6.07, 60.1, 42.1), (2, 2.036, 7.57, 85.7, 58.2),
           (4, 2.480, 9.22, 122.8, 80.2), (8, 2.832, 10.53, 161.2, 101.8), (None, 3.000, 11.16, 183.2, 113.8)]


@pytest.mark.parametrize("d, sd, margin, inc15, inc20", TABLE19)
def test_vt17_table19(d, sd, margin, inc15, inc20) -> None:
    assert math.sqrt(snr_predictor.prediction_variance(d, 0.875, 3.0, 1.0)) == pytest.approx(sd, abs=0.0015)
    m = snr_predictor.margin_db(d, 0.875, 3.0, 1.0, 1e-4)
    assert m == pytest.approx(margin, abs=0.015)
    assert 100 * snr_predictor.floor_increase(15, m) == pytest.approx(inc15, abs=0.15)
    assert 100 * snr_predictor.floor_increase(20, m) == pytest.approx(inc20, abs=0.15)


def test_vt17_rho_and_sensitivity() -> None:
    assert snr_predictor.time_constant_to_rho(8 / 30, 2.0) == pytest.approx(0.875, abs=0.001)
    assert [round(100 * snr_predictor.sensitivity_per_db(s), 1) for s in (5, 10, 15, 20)] == [12.3, 8.7, 6.4, 4.9]


@pytest.mark.parametrize("delay", [0, 1, 4])
def test_vt17_margin_rule_outage_by_simulation(delay) -> None:
    """New evidence (not in the paper): with A7 true, P[s_g < gamma_d] ~ eta [P1 Thm 3]."""
    from sim.channel.snr_process import margin_rule_outage
    eta = 1e-2
    frac = margin_rule_outage(200_000, 15.0, 0.875, 3.0, 1.0, delay, eta, seed=3)
    assert abs(frac - eta) < 4 * math.sqrt(eta / 200_000 * 20)   # AR(1) correlation inflates the variance


# ---------------- VT-18 controller [P1 Eq. 40, Prop. 17] ----------------
@pytest.fixture(scope="module")
def controller_runs():
    from sim.video.synthetic_model import SyntheticModel
    model = SyntheticModel(k=8000)
    cache: dict[float, float] = {}

    def gmap(g: float) -> float:
        key = round(g, 9)
        if key not in cache:
            cache[key] = model.gamma_map_db(g)
        return cache[key]

    runs = {}
    for start in (6.0, 14.0):
        for beta in (1.0, 0.66):
            g, traj = start, [start]
            for _ in range(5):
                g = damped_step_db(g, gmap, beta)
                traj.append(g)
            runs[(start, beta)] = traj
    return runs


@pytest.mark.slow
def test_vt18_undamped_oscillates_with_slope_about_minus_half(controller_runs) -> None:
    t = np.array(controller_runs[(6.0, 1.0)])
    ratios = np.diff(t)[1:] / np.diff(t)[:-1]
    assert np.all(ratios < 0) and np.all((ratios > -0.65) & (ratios < -0.45))    # paper: -0.59 .. -0.51


@pytest.mark.slow
def test_vt18_damped_settles_in_two_steps(controller_runs) -> None:
    for start in (6.0, 14.0):
        t = controller_runs[(start, 0.66)]
        assert abs(t[2] - t[5]) < 0.1, t


@pytest.mark.slow
@pytest.mark.xfail(strict=True, reason="not reproduced: fixed point ~9.0 dB (paper 9.41 dB); same set-up gap as VT-13")
def test_vt18_fixed_point_value(controller_runs) -> None:
    assert controller_runs[(6.0, 0.66)][2] == pytest.approx(9.41, abs=0.05)


def test_f_inverse_round_trip() -> None:
    for g in (0.5, 3.0, 10.0, 25.0):
        assert f_inverse(stationarity_lhs(g)) == pytest.approx(g, rel=1e-10)


# ---------------- VT-19 violation interval [P1 Cor. 7] ----------------
def test_vt19_violation_interval() -> None:
    from nidar.video.quality import mean_violation_interval_s
    got = [mean_violation_interval_s(8 / 30, e) for e in (1e-2, 1e-3, 1e-4, 1e-5)]
    # compared at the paper's printed precision
    assert [round(got[0], 1), round(got[1]), round(got[2]), round(got[3])] == [26.7, 267, 2667, 26667]
