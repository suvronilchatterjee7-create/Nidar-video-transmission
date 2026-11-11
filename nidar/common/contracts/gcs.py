"""GCS display model and mission phases. docs/INTERFACES.md §8, docs/ARCHITECTURE.md §7.

Everything the Brief requires the GCS to display [BRIEF §4]; display predictor is display-only
[P2 §14.3].
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

import numpy as np

from nidar.common.contracts.base import DroneId, require
from nidar.common.contracts.mission import MissionDefinition
from nidar.common.contracts.perception import SurvivorTrack
from nidar.common.contracts.state import DroneStatus
from nidar.common.contracts.swarm import AuctionAssignment, DeliveryEvent
from nidar.common.contracts.video import VideoSource


class MissionPhase:
    """GCS mission-level states. [BRIEF §3, §7, §8] [P2 §12.4] (ARCHITECTURE §7)"""

    IDLE = "IDLE"
    MISSION_LOADED = "MISSION_LOADED"
    PREFLIGHT = "PREFLIGHT"
    BLOCKED = "BLOCKED"
    READY = "READY"
    RUNNING = "RUNNING"
    RECALLING = "RECALLING"
    ABORTING = "ABORTING"
    RETURNING = "RETURNING"
    COMPLETE = "COMPLETE"
    ALL = frozenset({IDLE, MISSION_LOADED, PREFLIGHT, BLOCKED, READY, RUNNING,
                     RECALLING, ABORTING, RETURNING, COMPLETE})


@dataclass(frozen=True)
class GcsDisplayModel:
    """Everything the Brief says must be shown. [BRIEF §4]"""

    mission_loaded: Optional[MissionDefinition]
    preflight: Mapping[str, str]
    drones: Mapping[DroneId, DroneStatus]
    display_positions: Mapping[DroneId, np.ndarray]
    stale: Mapping[DroneId, bool]
    survivors: tuple[SurvivorTrack, ...]
    deliveries: tuple[DeliveryEvent, ...]
    assignments: tuple[AuctionAssignment, ...]
    coverage_fraction: float
    mission_phase: str
    mission_elapsed_s: float
    video: Mapping[DroneId, VideoSource]
    allowed_actions: frozenset[str]

    def __post_init__(self) -> None:
        require(self.mission_phase in MissionPhase.ALL, f"unknown mission phase {self.mission_phase!r}")
        require(0.0 <= self.coverage_fraction <= 1.0, "coverage_fraction in [0, 1]")
        require(set(self.preflight.values()) <= {"PASS", "FAIL", "PENDING"}, "preflight values PASS/FAIL/PENDING")
