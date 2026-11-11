"""Uniform scalar quantiser for the coded set F; no state from earlier GoPs. [P1 §5.1 E4, §5.2, A6]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


def quantise(coeffs: np.ndarray, theta_f: float) -> np.ndarray:
    """Quantise. [P1 E4]"""
    raise stub(
        "nidar/video/floor/quantiser.py:quantise",
        "P1 E4",
        WAITS_FOR,
    )


def dequantise(indices: np.ndarray, theta_f: float) -> np.ndarray:
    """Dequantise. [P1 E4]"""
    raise stub(
        "nidar/video/floor/quantiser.py:dequantise",
        "P1 E4",
        WAITS_FOR,
    )
