"""Information density of the floor block over L Rayleigh blocks: moments and an exact sampler.

Channel (normalised nu = 1, P_F = 1): y = sqrt(gamma) x + z per use, x, z ~ CN(0, 1) i.i.d. ensemble
[P1 §6.1 Eq. 22]. Moments [P1 Lemma 4 Eq. 23-24]. Exact O(1)-per-block sampler of the sufficient
statistics (||a||^2, ||b||^2, Re<a, b>) by Bartlett decomposition [P1 §A].
"""
from __future__ import annotations

import math

import numpy as np

LN2 = math.log(2.0)
LOG2E = 1.0 / LN2


def capacity_bits(snr: float | np.ndarray) -> float | np.ndarray:
    """C = log2(1 + gamma) bits per complex use [P1 §6.3]."""
    return np.log2(1.0 + np.asarray(snr, dtype=float))


def v_iid(snr: float | np.ndarray) -> float | np.ndarray:
    """Dispersion of the i.i.d. Gaussian ensemble, bits^2: 2 gamma / (1 + gamma) log2^2 e [P1 Eq. 24]."""
    g = np.asarray(snr, dtype=float)
    return 2.0 * g / (1.0 + g) * LOG2E**2


def v_equal_energy(snr: float | np.ndarray) -> float | np.ndarray:
    """Dispersion for equal-energy codewords, bits^2: gamma (gamma + 2) / (1 + gamma)^2 log2^2 e [P1 Lemma 4]."""
    g = np.asarray(snr, dtype=float)
    return g * (g + 2.0) / (1.0 + g) ** 2 * LOG2E**2


def sample_block_nats(m: float, snr: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Exact draws of one block's information density, in nats, for per-draw block SNRs ``snr``.

    With a = y / sqrt(1+gamma) and b = (x - sqrt(gamma) z) / sqrt(1+gamma) independent CN(0, I_m):
      sum |y|^2/(1+gamma) = A = ||a||^2 ~ Gamma(m),
      <a, b> | a ~ CN(0, A)  ->  c = sqrt(A) w,  w ~ CN(0, 1),
      ||b||^2 = |w|^2 + Gamma(m - 1),
      sum |z|^2 = (A - 2 sqrt(gamma) Re<a, b> + gamma ||b||^2) / (1 + gamma).
    The density is m ln(1+gamma) + A - sum |z|^2  [P1 Eq. 22 in nats; §A].
    """
    g = np.asarray(snr, dtype=float)
    shape = g.shape
    a2 = rng.gamma(m, size=shape)
    wr = rng.standard_normal(shape) * math.sqrt(0.5)
    wi = rng.standard_normal(shape) * math.sqrt(0.5)
    rest = rng.gamma(m - 1.0, size=shape) if m > 1 else np.zeros(shape)
    b2 = wr * wr + wi * wi + rest
    cross = np.sqrt(a2) * wr
    z2 = (a2 - 2.0 * np.sqrt(g) * cross + g * b2) / (1.0 + g)
    return m * np.log1p(g) + a2 - z2


def sample_bits(m: float, block_snr: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Information density in bits summed over the last axis (the L blocks). ``block_snr`` has shape (N, L)."""
    return sample_block_nats(m, block_snr, rng).sum(axis=-1) * LOG2E


def sample(m: int, snr_per_block: np.ndarray, draws: int, seed: int) -> np.ndarray:
    """``draws`` samples (bits) for fixed per-block SNRs ``snr_per_block`` (shape (L,))."""
    rng = np.random.default_rng(seed)
    snr = np.broadcast_to(np.asarray(snr_per_block, dtype=float), (draws, np.size(snr_per_block)))
    return sample_bits(m, snr, rng)
