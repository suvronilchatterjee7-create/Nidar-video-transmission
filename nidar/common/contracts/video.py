"""Paper 1 video contracts. docs/INTERFACES.md §7, docs/VIDEO_SUBSYSTEM.md.

Certified floor design [P1 Thm 1, Prop. 11, Prop. 18]; firewalled floor [P1 E3-E4, Prop. 7];
analogue refinement [P1 E5-E7, Prop. 8/16]; quality accounting [P1 Def. 6, Prop. 10, Cor. 7].
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Sequence

import numpy as np

from nidar.common.contracts.base import DroneId, ProcessResult, require
from nidar.common.contracts.link import ResourcePlan, SnrReport


@dataclass(frozen=True)
class CertifiedFloorDesign:
    """One entry of the offline certified grid. [P1 Thm 1, Prop. 11, Prop. 18]

    ``includes_clipping`` / ``includes_estimation_error`` default to False because the paper's
    certificate does not include them (VIDEO_SUBSYSTEM P-7)."""

    design_id: str
    gamma_f_db: float
    n_f: int
    L: int
    m: int
    b_f_bits: int
    eps_core: float
    margin_db: float
    dt_upper_bound: float
    n_samples: int
    confidence_delta: float
    ensemble: str = "iid"
    includes_clipping: bool = False
    includes_estimation_error: bool = False

    def __post_init__(self) -> None:
        require(self.n_f == self.L * self.m, "n_F must equal L * m [P1 §6.1]")
        require(self.L >= 1 and self.m >= 1 and self.b_f_bits >= 1, "L, m, B_F must be positive")
        require(0 < self.eps_core < 1 and 0 < self.confidence_delta < 1, "probabilities must be in (0, 1)")
        require(self.dt_upper_bound <= self.eps_core / 2,
                "certified only if p_bar <= eps_core / 2 [P1 Thm 1, Prop. 11]")
        require(self.ensemble == "iid", "only the i.i.d. ensemble is certified by Thm 1 [P1 Rem. 8]")


@dataclass(frozen=True)
class GopHeader:
    schema_version: int
    drone_id: DroneId
    gop_index: int
    t_first_frame: float
    G: int
    frame_wh: tuple[int, int]
    fps: float
    transform: str        # "haar" | "dct2" [P1 Def. 4]
    design_id: str

    def __post_init__(self) -> None:
        require(self.G >= 1 and self.fps > 0, "G >= 1 and fps > 0")
        require(self.transform in {"haar", "dct2"}, "temporal transform must be haar or dct2 [P1 Def. 4]")

    @property
    def t_g(self) -> float:
        """GoP duration T_g = G / f_v [P1 §3.1]."""
        return self.G / self.fps


@dataclass(frozen=True)
class MetadataBlock:
    """Quantised (lambda, omega, a) per chunk; protected inside the floor. [P1 A5, §D.3]"""

    chunk_count: int
    lam_db_q: np.ndarray
    omega_db_q: np.ndarray
    a_q: np.ndarray

    def __post_init__(self) -> None:
        for name in ("lam_db_q", "omega_db_q", "a_q"):
            require(np.asarray(getattr(self, name)).shape == (self.chunk_count,),
                    f"MetadataBlock.{name} must have one entry per chunk")


@dataclass(frozen=True)
class FloorBlock:
    """Firewalled digital layer: uses NO data from earlier GoPs. [P1 E3-E4, Prop. 7]"""

    header: GopHeader
    metadata: MetadataBlock
    theta_f: float
    coded_set_size: int
    payload_bits: bytes
    crc_bits: int

    def __post_init__(self) -> None:
        require(self.theta_f > 0, "water level theta_F must be > 0 [P1 Def. 7]")
        require(self.crc_bits >= 0 and self.coded_set_size >= 0, "sizes must be >= 0")


@dataclass(frozen=True)
class AnalogueBlock:
    """Linear refinement layer. [P1 E5-E7, Prop. 8/16]"""

    gop_index: int
    active_set: np.ndarray
    symbols: np.ndarray
    spreading: str            # matrix family id: open (VIDEO_SUBSYSTEM §4.9)
    limiter_backoff_db: float # [P1 Table 15]

    def __post_init__(self) -> None:
        require(np.iscomplexobj(self.symbols) or np.asarray(self.symbols).size == 0,
                "analogue symbols are complex channel uses")


@dataclass(frozen=True)
class PilotPlan:
    block_len_m: int
    pilots_per_block: int   # [P1 Table 18]

    def __post_init__(self) -> None:
        require(0 <= self.pilots_per_block < self.block_len_m, "pilots must leave room for data")


@dataclass(frozen=True)
class VideoQualityReport:
    """Per-GoP decoder report. [P1 Def. 6, Prop. 10, Cor. 7]"""

    drone_id: DroneId
    gop_index: int
    floor_ok: bool
    teq_model_mbps: float       # model-based, Gaussian surrogate (upper bound) [P1 §8]
    beta_up: float
    fallback_floor_only: bool   # [P1 Rem. 5]
    design_id: str
    margin_db: float
    snr_report_delay_gops: int
    floor_failures_total: int
    floor_failure_budget: float

    def __post_init__(self) -> None:
        require(0.0 <= self.beta_up <= 1.0, "beta_up in [0, 1] [P1 Lemma 1]")


@dataclass(frozen=True)
class VideoFrame:
    drone_id: DroneId
    t_source: float
    image: np.ndarray
    gop_index: int

    def __post_init__(self) -> None:
        img = np.asarray(self.image)
        require(img.ndim == 3 and img.shape[2] == 3 and img.dtype == np.uint8, "image must be (H, W, 3) uint8")


class VideoEncoder(Protocol):
    """Drone side. [P1 §5.1 E1-E7]"""

    def encode(self, frames: Sequence[np.ndarray], plan: ResourcePlan,
               design: CertifiedFloorDesign) -> ProcessResult[tuple[FloorBlock, AnalogueBlock]]: ...


class VideoDecoder(Protocol):
    """GCS side. [P1 §5.1 D1-D5]"""

    def decode(self, rx_symbols: np.ndarray,
               plan: ResourcePlan) -> ProcessResult[tuple[list[VideoFrame], VideoQualityReport]]: ...


class VideoSource(Protocol):
    """What the GCS video panel consumes; neutral to OQ-02."""

    drone_id: DroneId

    def latest(self) -> Optional[tuple[VideoFrame, Optional[VideoQualityReport]]]: ...


class SnrPredictor(Protocol):
    """[P1 Lemma 8, Thm 3]"""

    def update(self, report: SnrReport) -> None: ...

    def design_snr_db(self, eps: float) -> float: ...


class FloorController(Protocol):
    """Output is always a member of the certified grid, or None if infeasible (OQ-24). [P1 Eq. 40, Prop. 18]"""

    def step(self, design_snr_db: float, n_available: int) -> Optional[CertifiedFloorDesign]: ...
