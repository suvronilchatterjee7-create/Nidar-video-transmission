"""GCS global state: the N x 13 state matrix, timestamps, and a display-only predictor.

X_GCS(t) stacks the latest 13-component state of every drone [P2 §12.1]. Packets may arrive late or out of
order, so each is kept with its source timestamp and older ones are ignored. For a smooth display the
position is extrapolated with p_UI(t) = p_rx + v_rx (t - t_rx) + 1/2 a_rx (t - t_rx)^2 [P2 §14.3]; the
acceleration is estimated from the last two velocity samples. The prediction is for display only and must
never feed control (checked by a static test, GT-14). A drone is stale when nothing arrived within a
display setting [ADIAT-inspired: HUD dims when stale].
"""
from __future__ import annotations

import numpy as np

from nidar.common.contracts import DroneId, DroneStatus


class GlobalState:
    def __init__(self) -> None:
        self._latest: dict[DroneId, DroneStatus] = {}
        self._accel: dict[DroneId, np.ndarray] = {}

    def ingest(self, status: DroneStatus) -> bool:
        """Store a status packet; returns False if it is older than what is already held."""
        d = status.state.drone_id
        prev = self._latest.get(d)
        if prev is not None:
            dt = status.state.t_source - prev.state.t_source
            if dt <= 0:
                return False
            self._accel[d] = (status.state.v - prev.state.v) / dt
        self._latest[d] = status
        return True

    def statuses(self) -> dict[DroneId, DroneStatus]:
        return dict(self._latest)

    def drone_ids(self) -> list[DroneId]:
        return sorted(self._latest)

    def matrix(self) -> np.ndarray:
        """X_GCS, shape (N, 13), rows in drone-id order [P2 §12.1]."""
        return np.array([self._latest[d].state.as_vector() for d in self.drone_ids()]).reshape(-1, 13)

    def display_position(self, drone_id: DroneId, t: float) -> np.ndarray:
        """p_UI(t) [P2 §14.3]: display only."""
        s = self._latest[drone_id].state
        dt = t - s.t_source
        return s.p + s.v * dt + 0.5 * self._accel.get(drone_id, np.zeros(3)) * dt * dt

    def stale(self, now: float, max_age_s: float) -> dict[DroneId, bool]:
        return {d: now - s.state.t_source > max_age_s for d, s in self._latest.items()}
