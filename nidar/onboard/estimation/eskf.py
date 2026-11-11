"""Error-State EKF: 15-dim error state, IMU mechanisation at 200 Hz, LiDAR/GNSS updates.
[P2 §2.1, §4.1 Eq. 68-76]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.contracts import DroneState, EstimatorHealth
from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


class EskfEstimator:
    """Implements the ``Estimator`` protocol (docs/INTERFACES.md §9)."""

    def propagate_imu(self, acc: np.ndarray, gyro: np.ndarray, t: float) -> None:
        """[P2 §4.1 Eq. 75 (IMU mechanisation, covariance propagation)]"""
        raise stub(
            "nidar/onboard/estimation/eskf.py:EskfEstimator.propagate_imu",
            "P2 §4.1 Eq. 75 (IMU mechanisation, covariance propagation)",
            WAITS_FOR,
        )

    def update_lidar(self, delta_x: np.ndarray, R: np.ndarray, t: float) -> bool:
        """[P2 Eq. 80-81 (NDT measurement)]"""
        raise stub(
            "nidar/onboard/estimation/eskf.py:EskfEstimator.update_lidar",
            "P2 Eq. 80-81 (NDT measurement)",
            WAITS_FOR,
        )

    def update_gnss(self, z: np.ndarray, R: np.ndarray, t: float) -> bool:
        """[P2 §9.2 / §13.2.2 (gated GNSS update, OQ-05d)]"""
        raise stub(
            "nidar/onboard/estimation/eskf.py:EskfEstimator.update_gnss",
            "P2 §9.2 / §13.2.2 (gated GNSS update, OQ-05d)",
            WAITS_FOR,
        )

    def state(self) -> DroneState:
        """[P2 Eq. 68-69]"""
        raise stub(
            "nidar/onboard/estimation/eskf.py:EskfEstimator.state",
            "P2 Eq. 68-69",
            WAITS_FOR,
        )

    def health(self) -> EstimatorHealth:
        """[P2 Eq. 76]"""
        raise stub(
            "nidar/onboard/estimation/eskf.py:EskfEstimator.health",
            "P2 Eq. 76",
            WAITS_FOR,
        )
