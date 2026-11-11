"""Dependence-testing bound estimator for the floor block. [P1 Eq. 25, Thm 1, Lemma 5]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


def dt_estimate(b_bits: int, n_f: int, L: int, mean_snr_db: float, draws: int, seed: int) -> tuple[float, int]:
    """Dt estimate. [P1 Eq. 25, Thm 1]"""
    raise stub(
        "nidar/video/certificates/dt_bound.py:dt_estimate",
        "P1 Eq. 25, Thm 1",
        WAITS_FOR,
    )
