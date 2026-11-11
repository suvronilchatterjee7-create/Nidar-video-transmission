"""Partition, auction and delivery contracts. docs/INTERFACES.md §5.

DWVT [P2 §7.1 Eq. 157-168]; min-cost assignment [P2 §7.3 Eq. 176-187]; delivery [P2 §8.4].
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np

from nidar.common.contracts.base import DroneId, as_array, require
from nidar.common.contracts.mission import GeoPolygon


@dataclass(frozen=True)
class PartitionCell:
    """One weighted Voronoi cell V_i(t). Weight law is OQ-05c'. [P2 Eq. 159, 163]"""

    drone_id: DroneId
    polygon: GeoPolygon
    weight: float
    frozen: bool     # GNSS-degraded freeze [P2 §13.2.2]

    def __post_init__(self) -> None:
        require(0.0 < self.weight <= 1.0, "weight must be in (0, 1] [P2 Eq. 27, 163]")


@dataclass(frozen=True)
class DensityKernel:
    """Gaussian priority kernel phi = 1 + lambda exp(-|q-p|^2 / 2 sigma^2). [P2 Eq. 167]"""

    p_surv_xy: np.ndarray
    strength: float      # lambda > 0
    sigma_m: float       # sigma > 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "p_surv_xy", as_array("DensityKernel.p_surv_xy", self.p_surv_xy, (2,)))
        require(self.strength > 0 and self.sigma_m > 0, "kernel strength and sigma must be > 0 [P2 Eq. 167]")


@dataclass(frozen=True)
class PartitionUpdate:
    schema_version: int
    t_source: float
    cells: tuple[PartitionCell, ...]
    density_kernels: tuple[DensityKernel, ...] = ()

    def __post_init__(self) -> None:
        ids = [c.drone_id for c in self.cells]
        require(len(ids) == len(set(ids)), "one cell per drone")


@dataclass(frozen=True)
class AssignmentCostTerms:
    """Per (i, j) term breakdown, so either cost form can be logged (OQ-05c). [P2 Eq. 38 / Eq. 179]"""

    time_to_intercept_s: float
    battery_term: float
    payload_term: float                      # +inf when the payload is gone [P2 Eq. 181]
    abandonment_term: Optional[float] = None # only in Eq. 179

    @property
    def feasible(self) -> bool:
        return math.isfinite(self.payload_term)


@dataclass(frozen=True)
class AuctionAssignment:
    """GCS min-cost assignment output. [P2 Eq. 183-185]"""

    schema_version: int
    t_source: float
    drone_id: DroneId
    survivor_id: str
    cost: float
    terms: AssignmentCostTerms
    solver: str

    def __post_init__(self) -> None:
        require(math.isfinite(self.cost), "an issued assignment must have finite cost [P2 Eq. 181]")
        require(self.terms.feasible, "cannot assign a drone without payload [P2 Eq. 181]")


@dataclass(frozen=True)
class DeliveryEvent:
    """Kit release report. [BRIEF §4] [P2 §6.4 Exc. 4, Eq. 235-236]"""

    schema_version: int
    drone_id: DroneId
    survivor_id: str
    t_release: float
    p_release: np.ndarray
    v_release: np.ndarray
    miss_distance_est_m: float    # target 0.5 m vs 0.3 m is OQ-20
    hw_trigger_confirmed: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "p_release", as_array("DeliveryEvent.p_release", self.p_release, (3,)))
        object.__setattr__(self, "v_release", as_array("DeliveryEvent.v_release", self.v_release, (3,)))
        require(self.miss_distance_est_m >= 0, "miss distance must be >= 0")
