"""Outage quantiles for L independent Rayleigh blocks and ideal / rateless floor shares.
[P1 §6.4, Table 9, §6.6]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


def outage_rate(L: int, mean_snr_db: float, eps: float, draws: int, seed: int) -> float:
    """Outage rate. [P1 §6.4]"""
    raise stub(
        "nidar/video/certificates/outage.py:outage_rate",
        "P1 §6.4",
        WAITS_FOR,
    )


def ideal_floor_fraction(b_bits: float, n_total: int, L: int, mean_snr_db: float, eps: float) -> float:
    """Ideal floor fraction. [P1 Table 9]"""
    raise stub(
        "nidar/video/certificates/outage.py:ideal_floor_fraction",
        "P1 Table 9",
        WAITS_FOR,
    )


def ideal_rateless_mean_fraction(b_bits: float, n_total: int, L: int, mean_snr_db: float, eps: float) -> float:
    """Ideal rateless mean fraction. [P1 §6.6]"""
    raise stub(
        "nidar/video/certificates/outage.py:ideal_rateless_mean_fraction",
        "P1 §6.6",
        WAITS_FOR,
    )
