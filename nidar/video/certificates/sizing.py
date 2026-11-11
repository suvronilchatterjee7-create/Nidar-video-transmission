"""Normal-approximation sizing of the floor block. [P1 Prop. 12 Eq. 26-27, Table 7]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


def n_f_normal_approx(b_bits: float, snr: float, eps: float, ensemble: str) -> float:
    """N f normal approx. [P1 Eq. 26]"""
    raise stub(
        "nidar/video/certificates/sizing.py:n_f_normal_approx",
        "P1 Eq. 26",
        WAITS_FOR,
    )


def relative_overhead(b_bits: float, snr: float, eps: float, ensemble: str) -> float:
    """Relative overhead. [P1 Eq. 27, Table 7]"""
    raise stub(
        "nidar/video/certificates/sizing.py:relative_overhead",
        "P1 Eq. 27, Table 7",
        WAITS_FOR,
    )


def segmentation_overhead(b_bits: float, snr: float, eps: float, k: int) -> float:
    """Segmentation overhead. [P1 Prop. 13]"""
    raise stub(
        "nidar/video/certificates/sizing.py:segmentation_overhead",
        "P1 Prop. 13",
        WAITS_FOR,
    )
