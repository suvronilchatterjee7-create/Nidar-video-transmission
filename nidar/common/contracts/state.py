"""Drone state and status contracts. docs/INTERFACES.md §3.

13-component state x = [p, v, q, omega] [P2 §1.2 Eq. 8-9]; telemetry state packet contents
"x_i, battery information, and CBF status" [P2 §12.1].
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional

import numpy as np

from nidar.common.contracts.base import DroneId, as_array, require


@dataclass(frozen=True)
class DroneState:
    """x_i in R^3 x R^3 x S^3 x R^3. q is unit, scalar-first, body->inertial. [P2 Eq. 8-9]"""

    drone_id: DroneId
    t_source: float
    p: np.ndarray       # (3,) m, F_I
    v: np.ndarray       # (3,) m/s, F_I
    q: np.ndarray       # (4,) unit quaternion
    omega: np.ndarray   # (3,) rad/s, F_B

    def __post_init__(self) -> None:
        require(self.drone_id >= 1, "drone_id is 1-based [P2 Eq. 7]")
        object.__setattr__(self, "p", as_array("DroneState.p", self.p, (3,)))
        object.__setattr__(self, "v", as_array("DroneState.v", self.v, (3,)))
        q = as_array("DroneState.q", self.q, (4,))
        require(abs(float(np.linalg.norm(q)) - 1.0) < 1e-6, "DroneState.q must be a unit quaternion [P2 Eq. 70]")
        object.__setattr__(self, "q", q)
        object.__setattr__(self, "omega", as_array("DroneState.omega", self.omega, (3,)))

    def as_vector(self) -> np.ndarray:
        """(13,) row of the GCS global state matrix X_GCS [P2 §12.1]."""
        return np.concatenate([self.p, self.v, self.q, self.omega])


@dataclass(frozen=True)
class EstimatorHealth:
    """ESKF health summary. [P2 §4.1, §13.2]"""

    cov_pos: np.ndarray          # (3,3) block of the 15x15 error-state covariance [P2 Eq. 76]
    gnss_accepted: bool          # innovation-gate result; gate form OQ-05d
    lidar_accepted: bool

    def __post_init__(self) -> None:
        c = as_array("EstimatorHealth.cov_pos", self.cov_pos, (3, 3))
        require(np.allclose(c, c.T, atol=1e-9), "cov_pos must be symmetric")
        require(bool(np.all(np.linalg.eigvalsh(c) >= -1e-12)), "cov_pos must be positive semi-definite")
        object.__setattr__(self, "cov_pos", c)

    @property
    def trace_pos_m2(self) -> float:
        """tr(P_pos), the degradation trigger quantity [P2 Eq. 64, 250]."""
        return float(np.trace(self.cov_pos))


@dataclass(frozen=True)
class DroneStatus:
    """Telemetry state packet. [P2 §12.1]"""

    schema_version: int
    state: DroneState
    mode: str                         # registered mode name; mode table OQ-05a
    battery_energy_j: float           # E_i(t)  [P2 Eq. 104, 245]
    battery_energy_max_j: float       # E_max
    payload_present: bool             # chi_payload  [P2 Eq. 120, 180]
    kits_remaining: int               # > 1 only if OQ-01 is decided that way
    search_active: bool               # chi_search  [P2 Eq. 105]
    cbf_active: Mapping[str, bool]    # inter_agent / terrain / geofence  [P2 §8.3]
    nmpc_feasible: bool               # [P2 §8.5]
    estimator: EstimatorHealth
    link_rssi_db: Optional[float] = field(default=None)

    def __post_init__(self) -> None:
        require(self.battery_energy_max_j > 0, "battery_energy_max_j must be > 0")
        require(0 <= self.battery_energy_j <= self.battery_energy_max_j * (1 + 1e-9),
                "battery_energy_j must lie in [0, E_max]")
        require(self.kits_remaining >= 0, "kits_remaining must be >= 0")
        require(self.payload_present == (self.kits_remaining > 0),
                "payload_present must equal kits_remaining > 0 [P2 Eq. 180-181]")
        require(set(self.cbf_active) <= {"inter_agent", "terrain", "geofence"},
                "cbf_active keys must be inter_agent/terrain/geofence [P2 §8.3]")
