"""Orthogonal spreading of the analogue values and mapping to complex channel uses [P1 §5.1 E7, Table 3].

The paper says only "an orthogonal matrix" (the matrix family is open, docs/VIDEO_SUBSYSTEM.md §4.9), so both
families below are offered by name and the link configuration must name one:
- "identity": no spreading (each value sees its own channel use);
- "hadamard": block-diagonal normalised Walsh-Hadamard over the binary decomposition of the length
  (n = sum of powers of two, one fast Hadamard per segment, largest first). Orthogonal, exact length, no
  padding loss; inside a segment every value sees the average noise of the segment's uses
  ("robustness vs uniformity of loss").
Two real values per complex use [P1 §6.5].
"""
from __future__ import annotations

import numpy as np

FAMILIES = ("identity", "hadamard")


def _fwht(x: np.ndarray) -> np.ndarray:
    """Normalised fast Walsh-Hadamard transform (orthonormal, self-inverse), len(x) a power of two."""
    a = x.astype(float).copy()
    n = a.shape[0]
    h = 1
    while h < n:
        a = a.reshape(-1, 2, h)
        a = np.stack([a[:, 0] + a[:, 1], a[:, 0] - a[:, 1]], axis=1).reshape(n)
        h *= 2
    return a / np.sqrt(n)


def segments(n: int) -> list[tuple[int, int]]:
    """(start, length) of the power-of-two segments of n, largest first."""
    out, start = [], 0
    for b in range(n.bit_length() - 1, -1, -1):
        if n >> b & 1:
            out.append((start, 1 << b))
            start += 1 << b
    return out


def _check(family: str) -> None:
    if family not in FAMILIES:
        raise ValueError(f"spreading family must be one of {FAMILIES}, got {family!r}")


def padded_length(n: int, family: str) -> int:
    """Length after spreading (no padding for either family)."""
    _check(family)
    return n


def spread(values: np.ndarray, family: str) -> np.ndarray:
    _check(family)
    v = np.asarray(values, dtype=float)
    if family == "identity":
        return v.copy()
    out = np.empty_like(v)
    for s, n in segments(v.size):
        out[s:s + n] = _fwht(v[s:s + n])
    return out


def despread(symbols: np.ndarray, family: str, n_values: int) -> np.ndarray:
    return spread(np.asarray(symbols, dtype=float)[:n_values], family)     # each segment is self-inverse


def despread_noise(noise_per_dim: np.ndarray, family: str, n_values: int) -> np.ndarray:
    """Diagonal of S^T diag(nu) S: identity keeps nu; Hadamard gives each value its segment's mean noise."""
    _check(family)
    nu = np.asarray(noise_per_dim, dtype=float)[:n_values]
    if family == "identity":
        return nu.copy()
    out = np.empty_like(nu)
    for s, n in segments(n_values):
        out[s:s + n] = nu[s:s + n].mean()
    return out


def to_complex(real_dims: np.ndarray) -> np.ndarray:
    r = np.asarray(real_dims, dtype=float)
    if r.size % 2:
        r = np.concatenate([r, [0.0]])
    return r[0::2] + 1j * r[1::2]


def to_real(uses: np.ndarray, n_dims: int) -> np.ndarray:
    u = np.asarray(uses)
    out = np.empty(2 * u.size)
    out[0::2], out[1::2] = u.real, u.imag
    return out[:n_dims]
