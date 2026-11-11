"""Delayed, noisy SNR prediction and the chance-constrained margin rule. [P1 §C.2 A7, Lemma 8 Eq. 38, Thm 3, Eq. 39]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.contracts import SnrReport
from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


def prediction_variance(d: int, rho: float, sigma_s: float, sigma_m: float) -> float:
    """Prediction variance. [P1 Lemma 8 Eq. 38]"""
    raise stub(
        "nidar/video/control/snr_predictor.py:prediction_variance",
        "P1 Lemma 8 Eq. 38",
        WAITS_FOR,
    )


def margin_db(d: int, rho: float, sigma_s: float, sigma_m: float, eps: float) -> float:
    """Margin db. [P1 Thm 3]"""
    raise stub(
        "nidar/video/control/snr_predictor.py:margin_db",
        "P1 Thm 3",
        WAITS_FOR,
    )


class KalmanSnrPredictor:
    """Implements ``SnrPredictor``."""

    def update(self, report: SnrReport) -> None:
        """[P1 Lemma 8]"""
        raise stub(
            "nidar/video/control/snr_predictor.py:KalmanSnrPredictor.update",
            "P1 Lemma 8",
            WAITS_FOR,
        )

    def design_snr_db(self, eps: float) -> float:
        """[P1 Thm 3]"""
        raise stub(
            "nidar/video/control/snr_predictor.py:KalmanSnrPredictor.design_snr_db",
            "P1 Thm 3",
            WAITS_FOR,
        )
