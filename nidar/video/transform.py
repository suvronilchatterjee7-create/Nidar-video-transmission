"""Orthonormal spatio-temporal transform Theta = Theta_t (x) Theta_s.

Theta_t: orthonormal Haar (G a power of two) or DCT-II across the G frames of a GoP; Theta_s: orthonormal
2-D block DCT (8x8) on each frame. Fixed and linear: no motion search, no RD optimisation, no entropy-coder
state [P1 Def. 4, §4.1]; distortion is preserved, ||x - x_hat|| = ||c - c_hat|| [P1 Lemma 2].
Operates on one plane of shape (G, H, W) with H, W multiples of the block size.
"""
from __future__ import annotations

import functools

import numpy as np

BLOCK = 8


@functools.lru_cache(maxsize=32)
def dct_matrix(n: int) -> np.ndarray:
    """Orthonormal DCT-II matrix (rows = basis functions) [P1 Def. 4, ref. 22]."""
    k = np.arange(n)[:, None]
    i = np.arange(n)[None, :]
    m = np.cos(np.pi * (2 * i + 1) * k / (2 * n)) * np.sqrt(2.0 / n)
    m[0, :] = np.sqrt(1.0 / n)
    m.setflags(write=False)
    return m


@functools.lru_cache(maxsize=32)
def haar_matrix(n: int) -> np.ndarray:
    """Orthonormal Haar matrix, rows ordered DC first; n must be a power of two [P1 Def. 4]."""
    if n < 1 or n & (n - 1):
        raise ValueError(f"Haar needs a power-of-two GoP length, got {n}")
    h = np.array([[1.0]])
    while h.shape[0] < n:
        top = np.kron(h, [1.0, 1.0])
        bottom = np.kron(np.eye(h.shape[0]), [1.0, -1.0])
        h = np.vstack([top, bottom]) / np.sqrt(2.0)
    h.setflags(write=False)
    return h


def temporal_matrix(G: int, kind: str) -> np.ndarray:
    if kind == "haar":
        return haar_matrix(G)
    if kind == "dct2":
        return dct_matrix(G)
    raise ValueError(f"temporal transform must be 'haar' or 'dct2' [P1 Def. 4], got {kind!r}")


def _blockify(plane: np.ndarray, b: int) -> np.ndarray:
    g, h, w = plane.shape
    if h % b or w % b:
        raise ValueError(f"plane {h}x{w} is not a multiple of the {b}x{b} block")
    return plane.reshape(g, h // b, b, w // b, b)


def forward(gop: np.ndarray, temporal: str, block: int = BLOCK) -> np.ndarray:
    """c = Theta x for one plane; output has the input's shape, coefficient (u, v) of block (by, bx) of
    temporal band t stored at [t, by*b + u, bx*b + v]."""
    x = np.asarray(gop, dtype=float)
    t = np.tensordot(temporal_matrix(x.shape[0], temporal), x, axes=(1, 0))
    d = dct_matrix(block)
    blocks = _blockify(t, block)
    c = np.einsum("ui,gaibj,vj->gaubv", d, blocks, d)
    return c.reshape(x.shape)


def inverse(coeffs: np.ndarray, temporal: str, block: int = BLOCK) -> np.ndarray:
    """x = Theta^T c [P1 Lemma 2]."""
    c = np.asarray(coeffs, dtype=float)
    d = dct_matrix(block)
    blocks = _blockify(c, block)
    t = np.einsum("ui,gaubv,vj->gaibj", d, blocks, d).reshape(c.shape)
    return np.tensordot(temporal_matrix(c.shape[0], temporal).T, t, axes=(1, 0))


def zone_map(h: int, w: int, block: int = BLOCK) -> np.ndarray:
    """Frequency zone u + v (0 .. 2b-2) for every coefficient position of a plane: 15 zones for 8x8
    [P1 Table 21]."""
    u = np.arange(block)
    z = u[:, None] + u[None, :]
    return np.tile(z, (h // block, w // block))
