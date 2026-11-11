"""KL upper confidence bound for the mean of [0, 1]-valued samples. [P1 Prop. 11]

eps_bar_delta = max{q >= eps_hat : N KL(eps_hat || q) <= ln(1/delta)} bounds the true mean from above
with probability at least 1 - delta.
"""
from __future__ import annotations

import math


def kl_bernoulli(p: float, q: float) -> float:
    """KL(p || q) = p ln(p/q) + (1-p) ln((1-p)/(1-q)), with 0 ln 0 = 0."""
    if not (0.0 <= p <= 1.0 and 0.0 < q < 1.0):
        raise ValueError(f"need 0 <= p <= 1 and 0 < q < 1, got p={p}, q={q}")
    out = 0.0
    if p > 0:
        out += p * math.log(p / q)
    if p < 1:
        out += (1 - p) * math.log((1 - p) / (1 - q))
    return out


def upper_bound(p_hat: float, n: int, delta: float) -> float:
    """eps_bar_delta of [P1 Prop. 11] by bisection (KL is increasing in q for q >= p_hat)."""
    if n <= 0 or not 0 < delta < 1:
        raise ValueError("n must be positive and 0 < delta < 1")
    budget = math.log(1.0 / delta) / n
    lo, hi = p_hat, 1.0 - 1e-15
    if kl_bernoulli(p_hat, hi) <= budget:
        return 1.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if mid <= 0.0 or kl_bernoulli(p_hat, mid) <= budget:
            lo = mid
        else:
            hi = mid
    return hi
