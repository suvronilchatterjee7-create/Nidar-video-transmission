"""Normal-approximation sizing of the floor block and the segmentation penalty.

n_F C - sqrt(n_F V) Q^-1(eps_F / 2) = B_F  ->  n_F^NA of [P1 Prop. 12 Eq. 26]; relative excess
rho = n_F C / B_F - 1 [P1 Eq. 27, Table 7]; K-segment penalty [P1 Prop. 13].
V = V_iid for the i.i.d. ensemble certified by Theorem 1, V(gamma) for equal-energy codewords [P1 Rem. 8].
"""
from __future__ import annotations

import math
from statistics import NormalDist

from nidar.video.certificates.info_density import capacity_bits, v_equal_energy, v_iid

_N = NormalDist()


def q_inv(p: float) -> float:
    """Q^-1(p): inverse Gaussian complementary CDF [P1 §6]."""
    return _N.inv_cdf(1.0 - p)


def _dispersion(snr: float, ensemble: str) -> float:
    if ensemble == "iid":
        return float(v_iid(snr))
    if ensemble == "equal_energy":
        return float(v_equal_energy(snr))
    raise ValueError(f"ensemble must be 'iid' or 'equal_energy', got {ensemble!r}")


def n_f_normal_approx(b_bits: float, snr: float, eps: float, ensemble: str = "iid") -> float:
    """[P1 Eq. 26] with q = Q^-1(eps / 2)."""
    c = float(capacity_bits(snr))
    v = _dispersion(snr, ensemble)
    q = q_inv(eps / 2.0)
    root = (math.sqrt(v) * q + math.sqrt(v * q * q + 4.0 * c * b_bits)) / (2.0 * c)
    return root * root


def relative_overhead(b_bits: float, snr: float, eps: float, ensemble: str = "iid") -> float:
    """rho = n_F^NA C / B_F - 1 [P1 Eq. 27, Table 7]."""
    return n_f_normal_approx(b_bits, snr, eps, ensemble) * float(capacity_bits(snr)) / b_bits - 1.0


def segmentation_overhead(b_bits: float, snr: float, eps: float, k: int, ensemble: str = "iid") -> float:
    """rho_K ~ Q^-1(eps / (2K)) sqrt(K V / (C B_F)) [P1 Prop. 13]."""
    c = float(capacity_bits(snr))
    return q_inv(eps / (2.0 * k)) * math.sqrt(k * _dispersion(snr, ensemble) / (c * b_bits))
