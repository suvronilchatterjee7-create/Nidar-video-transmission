"""Orthonormal spatio-temporal transform Theta = Theta_t (x) Theta_s (Haar or DCT-II in time, 2-D block DCT
in space). No motion search. [P1 Def. 4, Lemma 2]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


def forward(gop: np.ndarray, temporal: str, block: int) -> np.ndarray:
    """Forward. [P1 Def. 4]"""
    raise stub(
        "nidar/video/transform.py:forward",
        "P1 Def. 4",
        WAITS_FOR,
    )


def inverse(coeffs: np.ndarray, temporal: str, block: int) -> np.ndarray:
    """Inverse. [P1 Def. 4, Lemma 2]"""
    raise stub(
        "nidar/video/transform.py:inverse",
        "P1 Def. 4, Lemma 2",
        WAITS_FOR,
    )
