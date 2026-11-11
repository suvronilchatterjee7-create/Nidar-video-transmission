# Interfaces — typed contracts between modules

Status: **Phase 1 draft for review**. Code below is *specification* in Python syntax. It becomes `nidar/common/contracts/*.py` in Phase 2 [USER-PROMPT §8 Phase 2].

Tag conventions: [ARCHITECTURE.md §0](ARCHITECTURE.md#0-conventions).

---

## 1. Principles

| # | Rule | Tag |
|---|---|---|
| 1 | **One normalised contract per stream type**, plus adapters for anything that doesn't speak it natively. Orchestrators only see the contract | [ADIAT-inspired: `streaming/contracts.py`, `adapters.py`] |
| 2 | Every processing call returns `ProcessResult[T]`: a payload, timings and `error_message`. A failed item never crashes the pipeline | [ADIAT-inspired: `StreamProcessResult`, `StreamAnalyzeService`] |
| 3 | Image coordinates are **source-frame pixels**, top-left origin | [ADIAT-inspired: `StreamDetection` docstring] |
| 4 | SI units; positions in the local inertial frame F_I (metres); quaternion body→inertial, scalar-first (q_w, q_x, q_y, q_z) | [P2 §1.2 Eq. 8–9] |
| 5 | Every message carries `t_source` (seconds, sender clock) and `drone_id` where applicable. The GCS reconciles by timestamp | [P2 §12.1] |
| 6 | Messages are immutable (`frozen=True`). Arrays are `numpy.ndarray` with documented shape | [USER-PROMPT §6.2] |
| 7 | Fields whose value depends on an open question **have no default** and name the OQ in their docstring | [USER-PROMPT §0.4] |
| 8 | Every wire message has a `schema_version`. Readers accept older versions (backward compatible) | [ADIAT-inspired: versioned result files] |

```python
# nidar/common/contracts/base.py  (spec)
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Generic, TypeVar, Optional, Protocol, Sequence, Mapping
import numpy as np

T = TypeVar("T")
SCHEMA_VERSION = 1
DroneId = int                      # 1..N   [P2 Eq. 7, 160]

@dataclass(frozen=True)
class StageTimings:
    t_start: float
    t_end: float
    skipped: bool = False          # [ADIAT-inspired: StageTimings.was_skipped]

@dataclass(frozen=True)
class ProcessResult(Generic[T]):
    """Normalised output of every service call. [ADIAT-inspired: StreamProcessResult]"""
    payload: Optional[T]
    timings: StageTimings
    error_message: Optional[str] = None     # names component + operation + input id
    @property
    def ok(self) -> bool: return self.error_message is None and self.payload is not None
```

---

## 2. Mission file

Format unknown: **OQ-22**. The parser is pluggable. Only the *parsed* form is fixed.

```python
@dataclass(frozen=True)
class GeoPolygon:
    """Closed polygon in the local inertial frame F_I, metres, CCW. [P2 §1.4 Eq. 21; §8.3 Eq. 224]"""
    vertices_xy: np.ndarray          # shape (M, 2)
    datum: str                       # geodetic origin / CRS of the source file. OQ-22

@dataclass(frozen=True)
class MissionDefinition:
    """Parsed organiser file. [BRIEF §3]"""
    schema_version: int
    source_file_sha256: str          # provenance for the mission log
    boundary: GeoPolygon             # geofence B   [BRIEF §7] [P2 §12.3.3]
    area_m2: float                   # must be <= 100_000   [BRIEF §1]
    launch_zone: Optional[GeoPolygon]  # 12 ft x 12 ft Z, if the file provides it; else surveyed at setup. OQ-22  [BRIEF §7]

class MissionFileParser(Protocol):
    """Registered by name in the registry. [ADIAT-inspired: algorithms.conf]"""
    name: str
    def can_parse(self, raw: bytes, filename: str) -> bool: ...
    def parse(self, raw: bytes, filename: str) -> ProcessResult[MissionDefinition]: ...
```

---

## 3. Drone state and status

```python
@dataclass(frozen=True)
class DroneState:
    """13-component state x_i = [p, v, q, omega]. [P2 §1.2 Eq. 8-9]"""
    drone_id: DroneId
    t_source: float
    p: np.ndarray        # (3,) m, F_I
    v: np.ndarray        # (3,) m/s, F_I
    q: np.ndarray        # (4,) unit quaternion, body->inertial, scalar first
    omega: np.ndarray    # (3,) rad/s, body frame F_B
    def as_vector(self) -> np.ndarray: ...   # (13,)  used for the GCS N x 13 matrix [P2 §12.1]

@dataclass(frozen=True)
class EstimatorHealth:
    """[P2 §4.1, §13.2]"""
    cov_pos: np.ndarray            # (3,3) P_pos block of the 15x15 error-state covariance
    trace_pos_m2: float            # tr(P_pos)
    gnss_accepted: bool            # last innovation gate result (gate form: OQ-05d)
    lidar_accepted: bool

@dataclass(frozen=True)
class DroneStatus:
    """Telemetry 'state packet': state + battery + CBF status. [P2 §12.1 'state packet contains x_i, battery, CBF status']"""
    schema_version: int
    state: DroneState
    mode: str                      # registered mode name; the mode table is OQ-05a
    battery_energy_j: float        # E_i(t)   [P2 Eq. 104, 245]
    battery_energy_max_j: float    # E_max
    payload_present: bool          # chi_payload,i   [P2 Eq. 120, 180]
    kits_remaining: int            # >1 only if OQ-01 is decided that way
    search_active: bool            # chi_search,i   [P2 Eq. 105]
    cbf_active: Mapping[str, bool] # {"inter_agent","terrain","geofence"} -> constraint active   [P2 §8.3]
    nmpc_feasible: bool            # [P2 §8.5]
    estimator: EstimatorHealth
    link_rssi_db: Optional[float]
```

---

## 4. Perception: detections, geotags, survivors

```python
@dataclass(frozen=True)
class Detection:
    """Normalised detector output, source-frame pixels. [ADIAT-inspired: StreamDetection] [P2 §4.3]"""
    drone_id: DroneId
    t_source: float                 # camera exposure time
    frame_size_wh: tuple[int, int]
    bbox_xyxy: tuple[float, float, float, float]
    centroid_uv: tuple[float, float]         # pixel used for the ray cast (u, v)  [P2 Eq. 88]
    confidence: float               # C_cnn in [0,1]   [P2 Eq. 260] (calibration: OQ-25)
    class_name: str                 # "person"
    keypoints: Optional[np.ndarray] # (17,3) COCO x,y,v   [DATASET: annotations/coco]
    posture: Optional[str]          # carried if the model outputs it. NOT used by any decision (IDEA-01 pending)

@dataclass(frozen=True)
class GeotagObservation:
    """Single-view 3-D geotag with covariance. [P2 §4.3 Eq. 88-100]"""
    detection: Detection
    p_surv: np.ndarray              # (3,) F_I   [P2 Eq. 96]
    sigma_surv: np.ndarray          # (3,3)      [P2 Eq. 99]
    low_confidence: bool            # gate form OQ-05k   [P2 Eq. 100]
    ray_depth_m: float              # s* from the TSDF root find   [P2 Eq. 92]

class SurvivorStatus:               # string constants
    CANDIDATE = "candidate"         # belief below threshold
    CONFIRMED = "confirmed"         # P > 0.95   [P2 Eq. 264-265]
    ASSIGNED = "assigned"
    DELIVERED = "delivered"
    UNSERVICEABLE = "unserviceable" # no kit-holding drone left (OQ-01)

@dataclass(frozen=True)
class SurvivorTrack:
    """Fused survivor hypothesis. [P2 §9.3]"""
    schema_version: int
    survivor_id: str                # stable key for the GCS (cf. ADIAT track_key; gallery itself is IDEA-02)
    p_surv: np.ndarray              # fused (3,)
    sigma_surv: np.ndarray          # fused (3,3)
    belief: float                   # P(S | D_1:m)   [P2 Eq. 260, 264]
    consistent_frames: int          # K   [P2 Eq. 261-262]
    observing_drones: frozenset[DroneId]   # multi-agent confirmation within r_tol  [P2 Eq. 263]
    status: str                     # SurvivorStatus
    t_first_seen: float
    t_confirmed: Optional[float]
```

---

## 5. Swarm: partition, auction, delivery

```python
@dataclass(frozen=True)
class PartitionCell:
    """[P2 §7.1 Eq. 159]"""
    drone_id: DroneId
    polygon: GeoPolygon
    weight: float                   # w_i in [w_min, 1]; weight law OQ-05c'
    frozen: bool                    # GNSS-degraded freeze   [P2 §13.2.2]

@dataclass(frozen=True)
class PartitionUpdate:
    schema_version: int
    t_source: float
    cells: tuple[PartitionCell, ...]
    density_kernels: tuple[tuple[np.ndarray, float, float], ...]  # (p_surv, lambda, sigma)  [P2 Eq. 167]

@dataclass(frozen=True)
class AssignmentCostTerms:
    """Per (i, j) term breakdown, so either cost form can be logged and compared. [P2 Eq. 38 / Eq. 179] OQ-05c"""
    time_to_intercept_s: float
    battery_term: float
    payload_term: float             # +inf when payload gone   [P2 Eq. 181]
    abandonment_term: Optional[float]   # only in Eq. 179

@dataclass(frozen=True)
class AuctionAssignment:
    """Output of the GCS min-cost assignment. [P2 §7.3 Eq. 183-185]"""
    schema_version: int
    t_source: float
    drone_id: DroneId
    survivor_id: str
    cost: float
    terms: AssignmentCostTerms
    solver: str                     # "hungarian"   [P2 Eq. 125]

@dataclass(frozen=True)
class DeliveryEvent:
    """[BRIEF §4 'delivery status of survivor's kits by each drone'] [P2 §8.4]"""
    schema_version: int
    drone_id: DroneId
    survivor_id: str
    t_release: float
    p_release: np.ndarray           # (3,)
    v_release: np.ndarray           # (3,)   check vs |v| <= 0.3 m/s   [P2 Eq. 236]
    miss_distance_est_m: float      # vs |p - p_surv| <= 0.5 m   [P2 Eq. 235] (target choice OQ-20)
    hw_trigger_confirmed: bool      # [P2 §6.4 Exc. 4]
```

---

## 6. Link contracts

```python
class OperatorAction:
    """The ONLY operator inputs. [BRIEF §3, §4, §8]  (P2 lists 3; RECALL added per Brief, OQ-16)"""
    LOAD_MISSION_FILE = "load_mission_file"
    START_MISSION = "start_mission"
    SAFETY_ABORT = "safety_abort"          # physical semantics OQ-16
    EMERGENCY_RECALL = "emergency_recall"  # physical semantics OQ-16

@dataclass(frozen=True)
class GcsCommand:
    """GCS -> drone. Generated by the GCS services or by one of the 4 operator actions only."""
    schema_version: int
    seq: int                        # repeated until acked
    t_source: float
    kind: str                       # "heartbeat" | "partition" | "assignment" | "abort" | "recall" | "start" | "preflight"
    target: Optional[DroneId]       # None = broadcast
    body: object                    # PartitionUpdate | AuctionAssignment | None

@dataclass(frozen=True)
class SnrReport:
    """GCS -> drone, one per GoP. Feeds the margin rule. [P1 §C.2 A7, Thm 3]"""
    schema_version: int
    drone_id: DroneId
    gop_index: int                  # g of the measured GoP
    t_source: float
    mean_snr_db: float              # s_hat_g, report noise sigma_m to be measured (OQ-03)
    fading_blocks_observed: int     # estimate of L actually seen in that GoP (P-1 gate)

@dataclass(frozen=True)
class LinkStatus:
    """GCS-side summary per drone link. [P2 §14.1] [P1 §C.2]"""
    drone_id: DroneId
    last_rx_t: float
    heartbeat_age_s: float          # compared with t_timeout (OQ-05b)
    snr_report_delay_gops: int      # d   [P1 Lemma 8]
    packet_loss_ratio: float

@dataclass(frozen=True)
class ResourcePlan:
    """Channel-use budget for one GoP of one drone link. [P1 §3.1, §6.5] [P2 §12.1 priority order]"""
    drone_id: DroneId
    gop_index: int
    n_total: int                    # (1 - delta) * W_i * T_g
    n_pilot: int                    # [P1 Table 18]
    n_telemetry: int                # OQ-14 / OQ-15: no default
    n_floor: int                    # = design.n_F
    n_refinement: int               # remainder
    design_id: str                  # CertifiedFloorDesign in force   [P1 Prop. 18]

class Radio(Protocol):
    """Physical link abstraction. Hardware: OQ-03 / OQ-10. Local RF only [BRIEF §5]."""
    def send(self, channel: str, payload: bytes) -> ProcessResult[None]: ...
    def send_symbols(self, iq: np.ndarray) -> ProcessResult[None]: ...      # SDR-class only (OQ-10)
    def receive(self, timeout_s: float) -> ProcessResult[tuple[str, bytes]]: ...
    def receive_symbols(self, n: int, timeout_s: float) -> ProcessResult[np.ndarray]: ...
```

---

## 7. Video contracts

```python
@dataclass(frozen=True)
class CertifiedFloorDesign:
    """One entry of the offline certified grid. [P1 Thm 1, Prop. 11, Prop. 18]"""
    design_id: str
    gamma_f_db: float               # floor per-use SNR
    n_f: int                        # = L * m
    L: int                          # fading blocks; must be >= 4 in practice   [P1 Cor. 6]
    m: int
    b_f_bits: int                   # payload certified for
    eps_core: float
    margin_db: float                # margin rule in force   [P1 Thm 3]
    dt_upper_bound: float           # p_bar <= eps_core/2   [P1 Prop. 11]
    n_samples: int
    confidence_delta: float         # 1e-6 in the paper
    ensemble: str                   # "iid"  (V_iid sizing)   [P1 Rem. 8]
    includes_clipping: bool = False         # P-7: not in the paper's certificate
    includes_estimation_error: bool = False # P-7

@dataclass(frozen=True)
class GopHeader:
    schema_version: int
    drone_id: DroneId
    gop_index: int
    t_first_frame: float
    G: int
    frame_wh: tuple[int, int]
    fps: float
    transform: str                  # "haar" | "dct2"   [P1 Def. 4]
    design_id: str

@dataclass(frozen=True)
class MetadataBlock:
    """Quantised (lambda, omega, a) per chunk, protected inside the floor. [P1 A5, §D.3]"""
    chunk_count: int
    lam_db_q: np.ndarray            # 1 dB steps
    omega_db_q: np.ndarray          # 1 dB steps
    a_q: np.ndarray                 # 1/32 steps

@dataclass(frozen=True)
class FloorBlock:
    """Firewalled digital layer: uses NO data from earlier GoPs. [P1 E3-E4, Prop. 7]"""
    header: GopHeader
    metadata: MetadataBlock
    theta_f: float                  # water level   [P1 Def. 7]
    coded_set_size: int             # |F|
    payload_bits: bytes             # quantised + entropy-coded {c_i : i in F}
    crc_bits: int                   # r   [P1 Rem. 7]

@dataclass(frozen=True)
class AnalogueBlock:
    """Linear refinement layer. [P1 E5-E7, Prop. 8/16]"""
    gop_index: int
    active_set: np.ndarray          # indices with g_i > 0
    symbols: np.ndarray             # complex (n_A,) after spreading + limiter
    spreading: str                  # matrix family id (open)
    limiter_backoff_db: float       # [P1 Table 15]

@dataclass(frozen=True)
class PilotPlan:
    block_len_m: int
    pilots_per_block: int           # [P1 Table 18]

@dataclass(frozen=True)
class VideoQualityReport:
    """Per GoP, decoder side. [P1 Def. 6, Prop. 10, Cor. 7]"""
    drone_id: DroneId
    gop_index: int
    floor_ok: bool
    teq_model_mbps: float           # model-based, Gaussian surrogate (upper bound)   [P1 §8]
    beta_up: float
    fallback_floor_only: bool       # [P1 Rem. 5]
    design_id: str
    margin_db: float
    snr_report_delay_gops: int
    floor_failures_total: int
    floor_failure_budget: float     # eps_F * GoPs so far

@dataclass(frozen=True)
class VideoFrame:
    drone_id: DroneId
    t_source: float
    image: np.ndarray               # (H, W, 3) uint8 for display
    gop_index: int

class VideoEncoder(Protocol):
    """Drone side. [P1 §5.1 E1-E7]"""
    def encode(self, frames: Sequence[np.ndarray], plan: ResourcePlan,
               design: CertifiedFloorDesign) -> ProcessResult[tuple[FloorBlock, AnalogueBlock]]: ...

class VideoDecoder(Protocol):
    """GCS side. [P1 §5.1 D1-D5]
    Phase 4: the received unit is ``nidar.video.receiver.ReceivedGop`` (floor block, analogue uses, block
    indices, pilots, noise variance) rather than a bare symbol array, because D1 needs the pilots and the
    block structure. The result payload is a ``DecodedGop`` (frames, floor-only frames, report)."""
    def decode(self, rx_symbols: "ReceivedGop", plan: ResourcePlan | None = None
               ) -> ProcessResult["DecodedGop"]: ...

class VideoSource(Protocol):
    """What the GCS video panel consumes. Neutral to OQ-02 (Paper 1 hybrid or P2 H.265)."""
    drone_id: DroneId
    def latest(self) -> Optional[tuple[VideoFrame, Optional[VideoQualityReport]]]: ...

class SnrPredictor(Protocol):
    """[P1 Lemma 8, Thm 3]"""
    def update(self, report: SnrReport) -> None: ...
    def design_snr_db(self, eps: float) -> float: ...   # s_pred - z_eps * sqrt(P_pred(d))

class FloorController(Protocol):
    """[P1 Eq. 40, Prop. 18]: output is always a member of the certified grid."""
    def step(self, design_snr_db: float, n_available: int) -> Optional[CertifiedFloorDesign]: ...  # None => infeasible (OQ-24)
```

---

## 8. GCS display model and operator commands

```python
@dataclass(frozen=True)
class GcsDisplayModel:
    """Everything the Brief says must be shown. [BRIEF §4]"""
    mission_loaded: Optional[MissionDefinition]           # 'loading of the mission file/boundary'
    preflight: Mapping[str, str]                          # gate -> PASS/FAIL/PENDING   [P2 §12.4]
    drones: Mapping[DroneId, DroneStatus]                 # 'live location and status of all drones'
    display_positions: Mapping[DroneId, np.ndarray]       # predictor output, display only   [P2 §14.3]
    stale: Mapping[DroneId, bool]                         # dim when stale [ADIAT-inspired]
    survivors: tuple[SurvivorTrack, ...]                  # 'tagged location of detected survivors' (provisional shown? OQ-05l)
    deliveries: tuple[DeliveryEvent, ...]                 # 'delivery status of kits by each drone'
    assignments: tuple[AuctionAssignment, ...]
    coverage_fraction: float                              # 'basic mission progress'
    mission_phase: str                                    # IDLE..COMPLETE (ARCHITECTURE §7)
    mission_elapsed_s: float                              # vs 30 min cap   [BRIEF §3]
    video: Mapping[DroneId, VideoSource]                  # 'live video feed display' (how many shown: OQ-09)
    allowed_actions: frozenset[str]                       # subset of OperatorAction, by phase
```

`allowed_actions` by phase:
- `LOAD_MISSION_FILE` in IDLE and BLOCKED
- `START_MISSION` in READY only
- `SAFETY_ABORT` and `EMERGENCY_RECALL` from READY onward

No other input path exists in the UI [BRIEF §3] [P2 §14.3].

---

## 9. Onboard component protocols

Each one is swappable: a Python reference for simulation, a compiled implementation for flight ([ARCHITECTURE.md §10](ARCHITECTURE.md#10-language-and-tooling-user-prompt-62)).

```python
class Estimator(Protocol):            # ES-EKF, 15-dim error state   [P2 §4.1]
    def propagate_imu(self, acc: np.ndarray, gyro: np.ndarray, t: float) -> None: ...
    def update_lidar(self, delta_x: np.ndarray, R: np.ndarray, t: float) -> bool: ...   # NDT result [P2 Eq. 80-81]
    def update_gnss(self, z: np.ndarray, R: np.ndarray, t: float) -> bool: ...          # gated (OQ-05d)
    def state(self) -> DroneState: ...
    def health(self) -> EstimatorHealth: ...

class TerrainMap(Protocol):           # TSDF   [P2 §4.2 Eq. 82-87]
    def integrate(self, points: np.ndarray, pose: DroneState) -> None: ...
    def sdf(self, p: np.ndarray) -> float: ...
    def grad(self, p: np.ndarray) -> np.ndarray: ...
    def ray_intersect(self, origin: np.ndarray, direction: np.ndarray) -> Optional[float]: ...  # Brent/secant [P2 Eq. 92]

class PersonDetector(Protocol):       # YOLOv8-pose class model   [P2 §4.3] [DATASET: yolov8n-pose.pt]
    def detect(self, frame: np.ndarray, t: float) -> ProcessResult[list[Detection]]: ...

class Geotagger(Protocol):            # [P2 Eq. 88-100]
    def geotag(self, det: Detection, pose: DroneState, P: np.ndarray, terrain: TerrainMap
               ) -> ProcessResult[GeotagObservation]: ...

class SurvivorConfirmer(Protocol):    # Bayesian grid, K frames, multi-drone fusion   [P2 §9.3]
    def observe(self, obs: GeotagObservation) -> Optional[SurvivorTrack]: ...   # returns on promotion
    def merge_remote(self, track: SurvivorTrack) -> None: ...                   # topology OQ-28

class CoveragePlanner(Protocol):      # BCD + Dubins   [P2 §7.2]
    def plan(self, cell: PartitionCell, altitude_m: float, fov_h_rad: float, overlap: float
             ) -> ProcessResult[np.ndarray]: ...      # waypoints (M, 3)

class TrajectoryGenerator(Protocol):  # min-snap B-spline QP   [P2 §8.1]
    def generate(self, waypoints: np.ndarray, v_max: float, a_max: float, terrain: TerrainMap
                 ) -> ProcessResult[object]: ...      # spline handle

class SafetyController(Protocol):     # NMPC + CBF + lexicographic fallback   [P2 §8.2-§8.5]
    def step(self, x_hat: DroneState, ref: object, neighbours: Mapping[DroneId, tuple[DroneState, float]],
             geofence: GeoPolygon, terrain: TerrainMap) -> ProcessResult[np.ndarray]: ...  # u = [T, tau]
    def on_payload_release(self, dm_kg: float, dI: np.ndarray, dr_cg: np.ndarray) -> None: ...  # [P2 Eq. 231-234, 272]

class ModeAutomaton(Protocol):        # table-driven SHA   [P2 §9.1, §13.1] (table: OQ-05a)
    def evaluate(self, status: DroneStatus, link: LinkStatus, command: Optional[GcsCommand]) -> str: ...

class PayloadMechanism(Protocol):     # [P2 §6.4 Exc. 4]  design: OQ-01, OQ-20
    def release(self) -> ProcessResult[float]: ...    # returns HW-trigger timestamp
```

---

## 10. Registry entry

[ADIAT-inspired: `algorithms.conf` entry fields]

```json
{
  "components": [
    {
      "name": "hungarian_auction",
      "interface": "nidar.swarm.auction.Auction",
      "module": "nidar.swarm.auction.hungarian",
      "class": "HungarianAuction",
      "platforms": ["gcs", "sim"],
      "sources": ["P2 §7.3 Eq. 183", "P2 Eq. 125"],
      "evidence": "PROVED (optimal assignment)"
    }
  ]
}
```

- Unknown names, or a platform mismatch, fail loudly with the component name [ADIAT-inspired: CLAUDE.md §2.3].
- The `sources` field feeds the traceability check in Phase 2.
