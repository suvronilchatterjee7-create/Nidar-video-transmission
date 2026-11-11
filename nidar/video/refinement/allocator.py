"""Analogue refinement power allocation.

Prop. 8 [P1 Eq. 19]: minimise sum D_i, D_i = (1/kappa_i + x_i/nu_i)^-1, x_i = g_i^2 >= 0, subject to
sum vartheta_i x_i <= P. Optimum: D_i = min{kappa_i, sqrt(xi nu_i vartheta_i)},
P_i = vartheta_i x_i = [sqrt(nu_i vartheta_i / xi) - nu_i vartheta_i / kappa_i]^+, xi the root of sum P_i = P.
Active-set limit |A| <= M via the Lagrangian saving s(xi) = (kappa - sqrt(xi nu vartheta))^2 / kappa
[P1 Rem. 6, Lemma 7 Eq. 31]; the price zeta of a dimension is the saving of the marginal component.
Prop. 16 [P1 Eq. 36-37]: allocation when estimation error adds noise sigma_i^2 u_i.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Allocation:
    x: np.ndarray          # gains squared g_i^2
    power: np.ndarray      # P_i = vartheta_i x_i
    d: np.ndarray          # resulting D_i
    xi: float              # power multiplier
    zeta: float            # price of one active dimension (0 if the limit is slack)
    active: np.ndarray     # boolean mask


def component_saving(kappa: np.ndarray, nu: np.ndarray, vartheta: np.ndarray, xi: float) -> np.ndarray:
    """s(xi) = (kappa - sqrt(xi nu vartheta))^2 / kappa for active components, else 0 [P1 Lemma 7 Eq. 31]."""
    r = np.sqrt(xi * nu * vartheta)
    return np.where(kappa > r, (kappa - r) ** 2 / kappa, 0.0)


def _power_at(xi: float, kappa: np.ndarray, nu: np.ndarray, vartheta: np.ndarray,
              max_active: int | None) -> tuple[np.ndarray, np.ndarray, float]:
    p = np.maximum(np.sqrt(nu * vartheta / xi) - nu * vartheta / kappa, 0.0)
    active = p > 0
    zeta = 0.0
    if max_active is not None and active.sum() > max_active:
        s = component_saving(kappa, nu, vartheta, xi)
        order = np.argsort(-s, kind="stable")
        keep = np.zeros_like(active)
        keep[order[:max_active]] = True
        zeta = float(s[order[max_active]])      # best excluded component = marginal price (see docs §4.7)
        active = active & keep
        p = np.where(active, p, 0.0)
    return p, active, zeta


def allocate(kappa: np.ndarray, vartheta: np.ndarray, nu: np.ndarray, power: float,
             max_active: int | None = None) -> Allocation:
    """Prop. 8 (with optional Remark 6 dimension limit) by bisection on log xi."""
    kappa, vartheta, nu = (np.asarray(v, dtype=float) for v in (kappa, vartheta, nu))
    if power <= 0:
        z = np.zeros_like(kappa)
        return Allocation(z, z, kappa.copy(), float("inf"), 0.0, z.astype(bool))
    hi = float((kappa**2 / (nu * vartheta)).max())          # sum P_i = 0 for xi >= hi
    lo = hi * 1e-30
    for _ in range(160):                                      # 2^-160 of a 1e30 log-range: below float eps
        mid = float(np.sqrt(lo * hi))
        p, _, _ = _power_at(mid, kappa, nu, vartheta, max_active)
        lo, hi = (mid, hi) if p.sum() > power else (lo, mid)
    xi = float(np.sqrt(lo * hi))
    p, active, zeta = _power_at(xi, kappa, nu, vartheta, max_active)
    if p.sum() > 0:
        p = p * (power / p.sum())                            # remove the last bisection residue
    x = p / vartheta
    d = 1.0 / (1.0 / kappa + x / nu)
    return Allocation(x, p, d, xi, zeta, active)


def allocate_grouped(kappa: np.ndarray, vartheta: np.ndarray, nu: np.ndarray, counts: np.ndarray, power: float,
                     max_active: int | None = None) -> tuple[Allocation, np.ndarray]:
    """Prop. 8 + Remark 6 for groups of ``counts`` identical components (one chunk = one group), exactly
    equivalent to expanding them. Returns the per-group allocation and the number of active components per
    group (the marginal group may be partly active)."""
    kappa, vartheta, nu, counts = (np.asarray(v, dtype=float) for v in (kappa, vartheta, nu, counts))
    if power <= 0:
        z = np.zeros_like(kappa)
        return Allocation(z, z, kappa.copy(), float("inf"), 0.0, z.astype(bool)), z

    def at(xi: float) -> tuple[np.ndarray, np.ndarray, float]:
        p = np.maximum(np.sqrt(nu * vartheta / xi) - nu * vartheta / kappa, 0.0)
        n_act = np.where(p > 0, counts, 0.0)
        zeta = 0.0
        if max_active is not None and n_act.sum() > max_active:
            s = component_saving(kappa, nu, vartheta, xi)
            order = np.argsort(-s, kind="stable")
            cum = np.cumsum(n_act[order])
            keep = np.zeros_like(n_act)
            prev = np.concatenate([[0.0], cum[:-1]])
            take = np.clip(max_active - prev, 0.0, n_act[order])
            keep[order] = take
            excluded = order[take < n_act[order]]
            zeta = float(s[excluded[0]]) if excluded.size else 0.0
            n_act = keep
        return p, n_act, zeta

    hi = float((kappa**2 / (nu * vartheta)).max())
    lo = hi * 1e-30
    for _ in range(160):
        mid = float(np.sqrt(lo * hi))
        p, n_act, _ = at(mid)
        lo, hi = (mid, hi) if (p * n_act).sum() > power else (lo, mid)
    xi = float(np.sqrt(lo * hi))
    p, n_act, zeta = at(xi)
    total = (p * n_act).sum()
    if total > 0:
        p = p * (power / total)
    x = np.where(n_act > 0, p / vartheta, 0.0)
    d = 1.0 / (1.0 / kappa + x / nu)
    return Allocation(x, p, d, xi, zeta, n_act > 0), n_act


def allocate_with_estimation_error(kappa: np.ndarray, vartheta: np.ndarray, nu: np.ndarray, sigma2: np.ndarray,
                                   power: float) -> Allocation:
    """Prop. 16 [P1 Eq. 36]: u_i = [(1/z_i - nu_i) / sigma_i^2]^+,
    z_i = sqrt(xi) c_i / (sqrt(nu_i/vartheta_i) + sqrt(xi) nu_i / (sigma_i^2 vartheta_i)),
    c_i = 1/kappa_i + 1/(sigma_i^2 vartheta_i); D_i = (1/kappa_i + u_i/(vartheta_i (nu_i + sigma_i^2 u_i)))^-1."""
    kappa, vartheta, nu, sigma2 = (np.asarray(v, dtype=float) for v in (kappa, vartheta, nu, sigma2))
    c = 1.0 / kappa + 1.0 / (sigma2 * vartheta)

    def energies(xi: float) -> np.ndarray:
        sx = np.sqrt(xi)
        z = sx * c / (np.sqrt(nu / vartheta) + sx * nu / (sigma2 * vartheta))
        return np.maximum((1.0 / z - nu) / sigma2, 0.0)

    lo, hi = 1e-30, 1e30
    for _ in range(600):
        mid = float(np.sqrt(lo * hi))
        lo, hi = (mid, hi) if energies(mid).sum() > power else (lo, mid)
    xi = float(np.sqrt(lo * hi))
    u = energies(xi)
    if u.sum() > 0:
        u = u * (power / u.sum())
    d = 1.0 / (1.0 / kappa + u / (vartheta * (nu + sigma2 * u)))
    return Allocation(u / vartheta, u, d, xi, 0.0, u > 0)


def precision_ceiling(kappa: np.ndarray, vartheta: np.ndarray, sigma2: np.ndarray) -> np.ndarray:
    """Lower bound D_i >= (1/kappa_i + 1/(sigma_i^2 vartheta_i))^-1 for any energy [P1 Eq. 37]."""
    return 1.0 / (1.0 / np.asarray(kappa) + 1.0 / (np.asarray(sigma2) * np.asarray(vartheta)))
