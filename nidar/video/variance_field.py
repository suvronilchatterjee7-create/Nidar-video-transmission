"""Per-chunk (lambda, omega, a) estimation from source frames, metadata quantisation (1 dB, a to 1/32),
temporal-DC mixing correction. [P1 A3, A5, §D.3, Lemma 9 Eq. 41]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.contracts import MetadataBlock
from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


def estimate(coeffs: np.ndarray, prev_last_frame: np.ndarray | None) -> MetadataBlock:
    """Estimate. [P1 A3, §D.3]"""
    raise stub(
        "nidar/video/variance_field.py:estimate",
        "P1 A3, §D.3",
        WAITS_FOR,
    )


def side_info_variance_dc(omega: np.ndarray, a: np.ndarray, w: np.ndarray, d_prev: np.ndarray, G: int) -> np.ndarray:
    """Side info variance dc. [P1 Lemma 9 Eq. 41]"""
    raise stub(
        "nidar/video/variance_field.py:side_info_variance_dc",
        "P1 Lemma 9 Eq. 41",
        WAITS_FOR,
    )
