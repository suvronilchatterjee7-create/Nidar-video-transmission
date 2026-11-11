"""Dependence-testing bound estimator and certified floor sizing.

eps_DT(B; n_F, P_F) = E 2^{-[i_F - log2((M-1)/2)]^+}, M = 2^B  [P1 Eq. 25]. If
eps_DT(B_F + 1) <= eps_F / 2 a code with 2^B_F messages and maximal error <= eps_F exists [P1 Thm 1].
Monte-Carlo estimate plus the KL certificate [P1 Prop. 11]. Block fading: L independent Rayleigh blocks
of m = n_F / L uses, power gains Exp(1) [P1 §6.4]; ``L = None`` means AWGN (no fading).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from nidar.video.certificates.info_density import sample_bits
from nidar.video.certificates.kl_certificate import upper_bound


def threshold_bits(b_bits: float) -> float:
    """log2((M - 1) / 2) for M = 2^B, accurate for large B."""
    return b_bits - 1.0 + math.log2(-math.expm1(-b_bits * math.log(2.0)))


@dataclass(frozen=True)
class DtEstimate:
    p_hat: float
    n_samples: int
    p_bar: float      # KL upper bound at confidence delta [P1 Prop. 11]
    delta: float


def dt_estimate(b_bits: float, n_f: int, L: int | None, mean_snr_db: float, draws: int, seed: int,
                delta: float = 1e-6, chunk: int = 50_000) -> DtEstimate:
    """Estimate eps_DT(B) for an n_F-use floor block. Pass ``b_bits = B_F + 1`` for Theorem 1."""
    rng = np.random.default_rng(seed)
    snr = 10.0 ** (mean_snr_db / 10.0)
    blocks = 1 if L is None else L
    m = n_f / blocks
    thr = threshold_bits(b_bits)
    total, done = 0.0, 0
    while done < draws:
        k = min(chunk, draws - done)
        if L is None:
            g = np.full((k, 1), snr)
        else:
            g = snr * rng.exponential(size=(k, blocks))
        i_bits = sample_bits(m, g, rng)
        total += float(np.exp2(-np.maximum(0.0, i_bits - thr)).sum())
        done += k
    p_hat = total / draws
    return DtEstimate(p_hat, draws, upper_bound(p_hat, draws, delta), delta)


def certify_floor(b_f_bits: float, L: int | None, mean_snr_db: float, eps_f: float, n_lo: int, n_hi: int,
                  draws: int, seed: int, delta: float = 1e-6) -> tuple[int, DtEstimate]:
    """Smallest n_F (multiple of L) in [n_lo, n_hi] with p_bar(eps_DT(B_F + 1)) <= eps_F / 2, by bisection.
    Uses the same seed at every probe (common random numbers). [P1 Thm 1, Prop. 11, Table 9]"""
    step = 1 if L is None else L
    lo, hi = math.ceil(n_lo / step), math.floor(n_hi / step)

    def ok(units: int) -> tuple[bool, DtEstimate]:
        est = dt_estimate(b_f_bits + 1, units * step, L, mean_snr_db, draws, seed, delta)
        return est.p_bar <= eps_f / 2, est

    good, est_hi = ok(hi)
    if not good:
        raise ValueError(f"no certified design up to n_F = {hi * step} (L={L}, {mean_snr_db} dB)")
    best = (hi, est_hi)
    while lo < hi:
        mid = (lo + hi) // 2
        good, est = ok(mid)
        if good:
            hi, best = mid, (mid, est)
        else:
            lo = mid + 1
    return best[0] * step, best[1]
