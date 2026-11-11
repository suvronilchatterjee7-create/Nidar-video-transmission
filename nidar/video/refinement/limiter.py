"""Hard amplitude limiter: Bussgang gain and distortion, SNDR, optimal back-off. [P1 §B.1 Lemma 6 Eq. 29-30, Table 15]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


def bussgang(beta: float) -> tuple[float, float]:
    """Bussgang. [P1 Lemma 6 Eq. 29]"""
    raise stub(
        "nidar/video/refinement/limiter.py:bussgang",
        "P1 Lemma 6 Eq. 29",
        WAITS_FOR,
    )


def sndr(beta: float, peak_snr: float) -> float:
    """Sndr. [P1 Eq. 30]"""
    raise stub(
        "nidar/video/refinement/limiter.py:sndr",
        "P1 Eq. 30",
        WAITS_FOR,
    )


def optimal_backoff_db(peak_snr_db: float) -> float:
    """Optimal backoff db. [P1 Table 15]"""
    raise stub(
        "nidar/video/refinement/limiter.py:optimal_backoff_db",
        "P1 Table 15",
        WAITS_FOR,
    )
