"""Block-Rayleigh fading channel: L independent blocks of m uses per GoP, correlation across GoPs.
[P1 §6.1, §6.4, Table 13 phases 1-2]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


def block_gains(L: int, m: int, gops: int, seed: int) -> np.ndarray:
    """Block gains. [P1 §6.1 (power gains Exp(1))]"""
    raise stub(
        "sim/channel/block_fading.py:block_gains",
        "P1 §6.1 (power gains Exp(1))",
        WAITS_FOR,
    )
