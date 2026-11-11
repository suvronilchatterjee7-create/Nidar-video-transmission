"""Information density of the floor block over L Rayleigh blocks, its moments, and an exact sampler.
[P1 §6.1 Eq. 22, Lemma 4 Eq. 23-24, §A]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


def v_iid(snr: float) -> float:
    """V iid. [P1 Eq. 24 (bits^2)]"""
    raise stub(
        "nidar/video/certificates/info_density.py:v_iid",
        "P1 Eq. 24 (bits^2)",
        WAITS_FOR,
    )


def v_equal_energy(snr: float) -> float:
    """V equal energy. [P1 Lemma 4]"""
    raise stub(
        "nidar/video/certificates/info_density.py:v_equal_energy",
        "P1 Lemma 4",
        WAITS_FOR,
    )


def sample(m: int, snr_per_block: np.ndarray, draws: int, seed: int) -> np.ndarray:
    """Sample. [P1 Eq. 22, §A sampler]"""
    raise stub(
        "nidar/video/certificates/info_density.py:sample",
        "P1 Eq. 22, §A sampler",
        WAITS_FOR,
    )
