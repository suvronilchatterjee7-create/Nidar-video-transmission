"""Onboard / GCS component protocols (docs/INTERFACES.md §9).

Every real-time component sits behind one of these, so the Python reference and a compiled
implementation are interchangeable and run the same contract tests. [USER-PROMPT §6.2]
"""
from __future__ import annotations

from typing import Mapping, Optional, Protocol

import numpy as np

from nidar.common.contracts.base import DroneId, ProcessResult
from nidar.common.contracts.link import GcsCommand, LinkStatus
from nidar.common.contracts.mission import GeoPolygon
from nidar.common.contracts.perception import Detection, GeotagObservation, SurvivorTrack
from nidar.common.contracts.state import DroneState, DroneStatus, EstimatorHealth
from nidar.common.contracts.swarm import PartitionCell


class Estimator(Protocol):
    """ES-EKF, 15-dim error state. [P2 §4.1]"""

    def propagate_imu(self, acc: np.ndarray, gyro: np.ndarray, t: float) -> None: ...
    def update_lidar(self, delta_x: np.ndarray, R: np.ndarray, t: float) -> bool: ...
    def update_gnss(self, z: np.ndarray, R: np.ndarray, t: float) -> bool: ...
    def state(self) -> DroneState: ...
    def health(self) -> EstimatorHealth: ...


class TerrainMap(Protocol):
    """TSDF. [P2 §4.2 Eq. 82-87]"""

    def integrate(self, points: np.ndarray, pose: DroneState) -> None: ...
    def sdf(self, p: np.ndarray) -> float: ...
    def grad(self, p: np.ndarray) -> np.ndarray: ...
    def ray_intersect(self, origin: np.ndarray, direction: np.ndarray) -> Optional[float]: ...


class PersonDetector(Protocol):
    """[P2 §4.3] [DATASET: yolov8n-pose.pt]"""

    def detect(self, frame: np.ndarray, t: float) -> ProcessResult[list[Detection]]: ...


class Geotagger(Protocol):
    """[P2 Eq. 88-100]"""

    def geotag(self, det: Detection, pose: DroneState, P: np.ndarray,
               terrain: TerrainMap) -> ProcessResult[GeotagObservation]: ...


class SurvivorConfirmer(Protocol):
    """[P2 §9.3]"""

    def observe(self, obs: GeotagObservation) -> Optional[SurvivorTrack]: ...
    def merge_remote(self, track: SurvivorTrack) -> None: ...


class CoveragePlanner(Protocol):
    """[P2 §7.2]"""

    def plan(self, cell: PartitionCell, altitude_m: float, fov_h_rad: float,
             overlap: float) -> ProcessResult[np.ndarray]: ...


class TrajectoryGenerator(Protocol):
    """[P2 §8.1]"""

    def generate(self, waypoints: np.ndarray, v_max: float, a_max: float,
                 terrain: TerrainMap) -> ProcessResult[object]: ...


class SafetyController(Protocol):
    """NMPC + CBF + lexicographic fallback. [P2 §8.2-§8.5]"""

    def step(self, x_hat: DroneState, ref: object, neighbours: Mapping[DroneId, tuple[DroneState, float]],
             geofence: GeoPolygon, terrain: TerrainMap) -> ProcessResult[np.ndarray]: ...
    def on_payload_release(self, dm_kg: float, dI: np.ndarray, dr_cg: np.ndarray) -> None: ...


class ModeAutomaton(Protocol):
    """Table-driven SHA. [P2 §9.1, §13.1] (table OQ-05a)"""

    def evaluate(self, status: DroneStatus, link: LinkStatus, command: Optional[GcsCommand]) -> str: ...


class PayloadMechanism(Protocol):
    """[P2 §6.4 Exc. 4] (design OQ-01, OQ-20)"""

    def release(self) -> ProcessResult[float]: ...
