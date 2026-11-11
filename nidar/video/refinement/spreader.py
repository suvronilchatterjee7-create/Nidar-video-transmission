"""Orthogonal spreading and mapping of analogue symbols to n_A channel uses; matrix family is open
(docs/VIDEO_SUBSYSTEM.md §4.9). [P1 §5.1 E7, Table 3]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


def spread(values: np.ndarray, family: str) -> np.ndarray:
    """Spread. [P1 E7]"""
    raise stub(
        "nidar/video/refinement/spreader.py:spread",
        "P1 E7",
        WAITS_FOR,
    )


def despread(symbols: np.ndarray, family: str) -> np.ndarray:
    """Despread. [P1 E7]"""
    raise stub(
        "nidar/video/refinement/spreader.py:despread",
        "P1 E7",
        WAITS_FOR,
    )
