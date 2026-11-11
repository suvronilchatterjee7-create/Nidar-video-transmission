"""Operator actions, commands and link contracts. docs/INTERFACES.md §6.

Local RF only [BRIEF §5]. Operator inputs are exactly four [BRIEF §3, §4, §8].
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

import numpy as np

from nidar.common.contracts.base import DroneId, ProcessResult, require


class OperatorAction:
    """The ONLY operator inputs. [BRIEF §3, §4, §8]
    P2 lists three [P2 §12.3.2]; EMERGENCY_RECALL is added because the Brief requires it (OQ-16).
    Physical semantics of ABORT and RECALL: OQ-16."""

    LOAD_MISSION_FILE = "load_mission_file"
    START_MISSION = "start_mission"
    SAFETY_ABORT = "safety_abort"
    EMERGENCY_RECALL = "emergency_recall"
    ALL = frozenset({LOAD_MISSION_FILE, START_MISSION, SAFETY_ABORT, EMERGENCY_RECALL})


COMMAND_KINDS = frozenset({"heartbeat", "partition", "assignment", "abort", "recall", "start", "preflight"})


@dataclass(frozen=True)
class GcsCommand:
    """GCS -> drone. Repeated until acknowledged (seq)."""

    schema_version: int
    seq: int
    t_source: float
    kind: str
    target: Optional[DroneId]     # None = broadcast
    body: object = None

    def __post_init__(self) -> None:
        require(self.kind in COMMAND_KINDS, f"unknown command kind {self.kind!r}")
        require(self.seq >= 0, "seq must be >= 0")


@dataclass(frozen=True)
class SnrReport:
    """GCS -> drone, one per GoP. Feeds the margin rule. [P1 §C.2 A7, Thm 3]"""

    schema_version: int
    drone_id: DroneId
    gop_index: int
    t_source: float
    mean_snr_db: float
    fading_blocks_observed: int   # estimate of L seen in that GoP [P1 Cor. 6]

    def __post_init__(self) -> None:
        require(self.gop_index >= 0, "gop_index must be >= 0")
        require(self.fading_blocks_observed >= 1, "at least one fading block per GoP")


@dataclass(frozen=True)
class LinkStatus:
    """GCS-side link summary per drone. [P2 §14.1] [P1 Lemma 8]"""

    drone_id: DroneId
    last_rx_t: float
    heartbeat_age_s: float          # compared with t_timeout (OQ-05b)
    snr_report_delay_gops: int      # d
    packet_loss_ratio: float

    def __post_init__(self) -> None:
        require(self.heartbeat_age_s >= 0 and self.snr_report_delay_gops >= 0, "ages must be >= 0")
        require(0.0 <= self.packet_loss_ratio <= 1.0, "packet_loss_ratio must be in [0, 1]")


@dataclass(frozen=True)
class ResourcePlan:
    """Channel-use budget for one GoP of one drone link. [P1 §3.1, §6.5] [P2 §12.1 priority order]

    n_telemetry has no default: OQ-14 / OQ-15."""

    drone_id: DroneId
    gop_index: int
    n_total: int
    n_pilot: int
    n_telemetry: int
    n_floor: int
    n_refinement: int
    design_id: str

    def __post_init__(self) -> None:
        parts = (self.n_pilot, self.n_telemetry, self.n_floor, self.n_refinement)
        require(all(p >= 0 for p in parts), "channel-use counts must be >= 0")
        require(sum(parts) == self.n_total,
                f"pilot+telemetry+floor+refinement = {sum(parts)} must equal n_total = {self.n_total}")


class Radio(Protocol):
    """Physical link abstraction; hardware OQ-03 / OQ-10. Local RF only [BRIEF §5]."""

    def send(self, channel: str, payload: bytes) -> ProcessResult[None]: ...

    def send_symbols(self, iq: np.ndarray) -> ProcessResult[None]: ...

    def receive(self, timeout_s: float) -> ProcessResult[tuple[str, bytes]]: ...

    def receive_symbols(self, n: int, timeout_s: float) -> ProcessResult[np.ndarray]: ...
