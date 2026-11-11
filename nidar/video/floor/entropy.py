"""Static-model entropy coder driven by the variance field (pilot: Laplacian code length).
[P1 §5.1 E4, Table 22]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.contracts import MetadataBlock
from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


def encode(indices: np.ndarray, metadata: MetadataBlock) -> bytes:
    """Encode. [P1 E4]"""
    raise stub(
        "nidar/video/floor/entropy.py:encode",
        "P1 E4",
        WAITS_FOR,
    )


def decode(data: bytes, metadata: MetadataBlock, count: int) -> np.ndarray:
    """Decode. [P1 E4]"""
    raise stub(
        "nidar/video/floor/entropy.py:decode",
        "P1 E4",
        WAITS_FOR,
    )
