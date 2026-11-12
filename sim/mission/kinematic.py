"""Kinematic multi-drone mission simulator: search -> detect -> confirm -> auction -> deliver -> return.

Drives the real swarm / GCS modules (DWVT partition, boustrophedon coverage, Bayesian confirmation, cost
forms + Hungarian auction, guards, operator gate, GeoJSON loader, global state) through their contracts
[P2 §5, §7, §9] [BRIEF §3, §4, §7, §8] [TEAM-BRIEF §6.1 D9].

What it is NOT: there is no flight dynamics, estimator, NMPC or CBF. Drones are points moving at set speeds
and constant altitude, so it tests the mission logic and timing, and it only *measures* separation and
geofence excursions instead of preventing them. Every physical number (speeds, altitude, field of view,
endurance, detector quality) is a scenario input; the shipped scenarios use labelled placeholders, not our
hardware (OQ-07, OQ-21, OQ-25).
"""
from __future__ import annotations

import dataclasses
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from nidar.common.contracts import (
    SCHEMA_VERSION,
    DeliveryEvent,
    Detection,
    DroneState,
    DroneStatus,
    EstimatorHealth,
    GcsDisplayModel,
    GeoPolygon,
    GeotagObservation,
    MissionPhase,
    OperatorAction,
    SurvivorStatus,
    SurvivorTrack,
)
from nidar.common.units import LAUNCH_PAD_SIDE_M, MAX_FLIGHT_S
from nidar.gcs.controllers.operator_actions import ActionNotPermitted, allowed_actions, check_action
from nidar.gcs.global_state import GlobalState
from nidar.gcs.mission_loader.geojson import GeoJsonMissionParser
from nidar.gcs.services.auction_service import AuctionService
from nidar.gcs.services.partition_service import PartitionService
from nidar.onboard.automaton import guards
from nidar.onboard.planning.coverage_bcd import footprint_width, plan_segments, sweep_spacing
from nidar.swarm import dwvt
from nidar.swarm.confirmation import BayesianConfirmer

AIRBORNE = {"TAKEOFF", "SEARCH", "HOLD", "DELIVER", "RTH", "LANDING", "ABORT_LANDING"}
TERMINAL = {"LANDED", "LANDED_OFF_PAD", "CRASHED"}
SENSING = {"SEARCH", "HOLD", "DELIVER", "RTH"}


@dataclass(frozen=True)
class Scenario:
    """All inputs of one simulated mission. No defaults: every value is stated in the scenario file."""

    name: str
    boundary_file: str
    pad_center: tuple[float, float]
    n_drones: int
    kits_per_drone: int
    altitude_m: float
    fov_h_deg: float
    overlap: float
    v_sweep: float
    v_cruise: float
    v_vertical: float
    endurance_s: float
    battery_margin_frac: float
    survivors: tuple
    decoys: tuple
    detector: dict
    confirmation: dict
    cost_form: str
    cost_weights: dict
    weight_law: str
    weight_params: dict
    gcs_timeout_s: float
    delivery_dwell_s: float
    coverage_target: float
    raster_resolution_m: float
    d_safe_m: float
    pad_exclusion_radius_m: float
    link_outages: tuple
    operator_events: tuple
    dt: float
    seed: int
    max_time_s: float

    @staticmethod
    def from_dict(d: dict, base_dir: Path | None = None) -> "Scenario":
        d = {k: v for k, v in d.items() if not k.startswith("_")}
        names = {f.name for f in dataclasses.fields(Scenario)}
        missing, extra = names - set(d), set(d) - names
        if missing or extra:
            raise ValueError(f"scenario fields missing {sorted(missing)} / unknown {sorted(extra)}")
        if base_dir is not None:
            d["boundary_file"] = str((base_dir / d["boundary_file"]).resolve())
        for k in ("survivors", "decoys", "link_outages", "operator_events", "pad_center"):
            d[k] = tuple(tuple(x) if isinstance(x, list) else x for x in d[k])
        return Scenario(**d)

    @staticmethod
    def load(path: str | Path) -> "Scenario":
        """Load a scenario file; ``"_base": "other.json"`` inherits that file and overrides its fields."""
        p = Path(path)
        d = json.loads(p.read_text(encoding="utf-8"))
        if "_base" in d:
            base = json.loads((p.parent / d["_base"]).read_text(encoding="utf-8"))
            d = {**base, **{k: v for k, v in d.items() if not k.startswith("_")}}
        return Scenario.from_dict(d, p.parent)


@dataclass
class _Drone:
    drone_id: int
    pos: np.ndarray
    pad_slot: np.ndarray
    kits: int
    confirmer: BayesianConfirmer
    task: str = "TAKEOFF"
    energy: float = 1.0
    timer: float = 0.0
    segments: np.ndarray = field(default_factory=lambda: np.zeros((0, 2, 2)))
    seg_i: int = 0
    seg_phase: int = 0
    target_sid: str | None = None
    link_up: bool = True
    hb_age: float = 0.0
    gcs_lost: bool = False
    health: str = "NOMINAL"
    outbox: list = field(default_factory=list)
    vel: np.ndarray = field(default_factory=lambda: np.zeros(2))
    landed_in_pad: bool | None = None
    path_m: float = 0.0


@dataclass
class _Tag:
    track: SurvivorTrack
    status: str
    t_tag: float
    by_drone: int
    true_index: int | None
    error_m: float | None
    assigned_to: int | None = None
    t_delivered: float | None = None
    miss_m: float | None = None


@dataclass
class MissionResult:
    scenario: str
    phase: str
    mission_time_s: float
    within_30_min: bool
    coverage_fraction: float
    coverage_lower_bound_s: float          # ideal bound A / (N W v_sweep) [P2 §12.2.3]
    survivors_total: int
    survivors_tagged: int
    survivors_delivered: int
    survivors_without_kit: int
    false_tags: int
    false_deliveries: int
    tags: list
    deliveries: list
    drones: dict
    min_separation_m: float
    min_separation_at: tuple | None
    separation_violations: int
    geofence_violation_steps: int
    crashed: int
    timeline: list
    display: GcsDisplayModel | None = None

    def summary(self) -> str:
        return (f"{self.scenario}: phase={self.phase} t={self.mission_time_s:.0f}s "
                f"coverage={self.coverage_fraction:.3f} tagged={self.survivors_tagged}/{self.survivors_total} "
                f"delivered={self.survivors_delivered} "
                f"no_kit={self.survivors_without_kit} false_tags={self.false_tags} "
                f"min_sep={self.min_separation_m:.1f}m crashed={self.crashed}")


def _clip(x: float, lo: float, hi: float) -> float:
    return float(min(hi, max(lo, x)))


class MissionSimulator:
    def run(self, scenario: Scenario | dict, seed: int | None = None) -> MissionResult:
        sc = scenario if isinstance(scenario, Scenario) else Scenario.from_dict(scenario)
        rng = np.random.default_rng(sc.seed if seed is None else seed)
        timeline: list = []

        def log(t: float, msg: str) -> None:
            timeline.append((round(t, 2), msg))

        # ---- mission file (operator action 1) and geometry
        phase = MissionPhase.IDLE
        check_action(OperatorAction.LOAD_MISSION_FILE, phase)
        raw = Path(sc.boundary_file).read_bytes()
        loaded = GeoJsonMissionParser().parse(raw, sc.boundary_file)
        if not loaded.ok:
            raise ValueError(loaded.error_message)
        mission = loaded.payload
        pad_c = np.array(sc.pad_center, dtype=float)
        half = LAUNCH_PAD_SIDE_M / 2.0
        pad = mission.launch_zone or GeoPolygon(
            pad_c + np.array([[-half, -half], [half, -half], [half, half], [-half, half]]), mission.boundary.datum)
        points = dwvt.rasterise(mission.boundary, sc.raster_resolution_m)
        covered = np.zeros(len(points), dtype=bool)
        width = footprint_width(sc.altitude_m, math.radians(sc.fov_h_deg))
        spacing = sweep_spacing(width, sc.overlap)
        survivors = np.array(sc.survivors, dtype=float).reshape(-1, 2)
        drain = 1.0 / sc.endurance_s
        det, conf = sc.detector, sc.confirmation
        frames_per_step = max(1, round(det["fps"] * sc.dt))

        # ---- fleet on the pad
        side = math.ceil(math.sqrt(sc.n_drones))
        offs = (np.arange(side) + 0.5) / side * LAUNCH_PAD_SIDE_M - half
        slots = [pad_c + np.array([offs[i % side], offs[i // side]]) for i in range(sc.n_drones)]
        drones = [_Drone(i + 1, slots[i].copy(), slots[i].copy(), sc.kits_per_drone,
                         BayesianConfirmer(conf["r_tol_m"], conf["max_gap_s"], f"D{i + 1}", conf["prior"],
                                           conf["k_min"], conf["threshold"]),
                         timer=sc.altitude_m / sc.v_vertical) for i in range(sc.n_drones)]
        by_id = {d.drone_id: d for d in drones}
        cell: dict[int, np.ndarray] = {}

        partition = PartitionService(sc.weight_law, sc.weight_params)
        auction = AuctionService(sc.cost_form, sc.cost_weights, sc.v_cruise)
        gstate = GlobalState()
        tags: dict[str, _Tag] = {}
        deliveries: list[DeliveryEvent] = []
        assignments: list = []
        min_sep, sep_viol, fence_viol = math.inf, 0, 0
        min_sep_at: tuple | None = None

        def status_of(d: _Drone, t: float) -> DroneStatus:
            alt = sc.altitude_m if d.task in AIRBORNE else 0.0
            st = DroneState(d.drone_id, t, [d.pos[0], d.pos[1], alt], [d.vel[0], d.vel[1], 0.0],
                            [1, 0, 0, 0], [0, 0, 0])
            return DroneStatus(SCHEMA_VERSION, st, d.task, d.energy, 1.0, d.kits > 0, d.kits,
                               d.task in ("SEARCH", "HOLD"), {}, True,
                               EstimatorHealth(np.eye(3) * 0.01, True, True))

        def plan_for(d: _Drone, idx: np.ndarray) -> None:
            cell[d.drone_id] = idx
            d.segments = plan_segments(points[idx], spacing, sc.raster_resolution_m, d.pos,
                                       mission.boundary.vertices_xy)
            d.seg_i, d.seg_phase = 0, 0
            d.task = "SEARCH" if len(d.segments) else "HOLD"

        def repartition(t: float) -> None:
            searchers = [d for d in drones if d.task in ("SEARCH", "HOLD") and not d.gcs_lost]
            todo = np.flatnonzero(~covered)
            if not searchers or todo.size == 0:
                return
            ids, labels = partition.update({d.drone_id: status_of(d, t) for d in searchers}, points[todo])
            for k, drone_id in enumerate(ids):
                plan_for(by_id[drone_id], todo[labels == k])
            log(t, f"repartition among drones {ids} ({todo.size} cells left)")

        def release_tag(d: _Drone) -> None:
            if d.target_sid and tags[d.target_sid].status == SurvivorStatus.ASSIGNED:
                tags[d.target_sid].status = SurvivorStatus.CONFIRMED
                tags[d.target_sid].assigned_to = None
            d.target_sid = None

        def go_home(d: _Drone, t: float, why: str) -> None:
            if d.task in AIRBORNE and d.task not in ("RTH", "LANDING", "ABORT_LANDING"):
                release_tag(d)
                d.task = "RTH"
                log(t, f"drone {d.drone_id} RTH ({why})")

        def move(d: _Drone, target: np.ndarray, speed: float) -> bool:
            delta = target - d.pos
            dist = float(np.linalg.norm(delta))
            step = speed * sc.dt
            if dist <= step:
                d.vel = delta / sc.dt
                d.pos = target.copy()
                d.path_m += dist
                return True
            d.vel = delta / dist * speed
            d.pos = d.pos + d.vel * sc.dt
            d.path_m += step
            return False

        def observe(d: _Drone, true_xy: np.ndarray, confidence: float, t: float) -> None:
            sigma = det["geotag_sigma_m"]
            p = np.array([*(true_xy + rng.normal(0, sigma, 2)), 0.0])
            cov = np.eye(3) * sigma**2
            dets = Detection(d.drone_id, t, (640, 480), (300, 220, 340, 260), (320, 240), confidence, "person")
            obs = GeotagObservation(dets, p, cov, bool(np.trace(cov) > conf["eps_tag_m"] ** 2), sc.altitude_m)
            track = d.confirmer.observe(obs)
            if track is not None:
                d.outbox.append(track)

        # ---- initial partition (GCS, during setup) and START (operator action 2)
        seeds = dwvt.farthest_point_seeds(points, sc.n_drones, pad_c)
        _, labels0 = dwvt.lloyd(points, seeds, np.ones(sc.n_drones))
        initial_cells = [np.flatnonzero(labels0 == k) for k in range(sc.n_drones)]
        phase = MissionPhase.READY
        check_action(OperatorAction.START_MISSION, phase)
        phase = MissionPhase.RUNNING
        log(0.0, f"START: {sc.n_drones} drones, {sc.kits_per_drone} kit(s) each, sweep spacing {spacing:.1f} m")

        t, events, need_partition, next_status = 0.0, sorted(sc.operator_events, key=lambda e: e["t"]), False, 0.0
        while t < sc.max_time_s and not all(d.task in TERMINAL for d in drones):
            t += sc.dt
            # 1. operator inputs: only the four Brief actions, gated by phase [BRIEF §3]
            while events and events[0]["t"] <= t:
                ev = events.pop(0)
                try:
                    check_action(ev["action"], phase)
                except ActionNotPermitted as exc:
                    log(t, f"operator input rejected: {exc}")
                    continue
                if ev["action"] == OperatorAction.EMERGENCY_RECALL:
                    phase = MissionPhase.RECALLING
                    for d in drones:
                        go_home(d, t, "operator recall")
                elif ev["action"] == OperatorAction.SAFETY_ABORT:
                    phase = MissionPhase.ABORTING
                    for d in drones:
                        if d.task in AIRBORNE and d.task != "ABORT_LANDING":
                            release_tag(d)
                            d.task, d.timer = "ABORT_LANDING", sc.altitude_m / sc.v_vertical
                    log(t, "operator SAFETY ABORT: all drones land in place")

            # 2. link state and failsafe guards [P2 Eq. 245-249]
            for d in drones:
                d.link_up = not any(o["drone"] == d.drone_id and o["t0"] <= t < o["t1"] for o in sc.link_outages)
                d.hb_age = 0.0 if d.link_up else d.hb_age + sc.dt
                if d.link_up and d.gcs_lost:
                    d.gcs_lost = False
                lost = guards.gcs_link_lost(d.hb_age, sc.gcs_timeout_s)
                if lost and not d.gcs_lost:
                    d.gcs_lost, d.health = True, "COMMS_LOSS"
                    if d.task in AIRBORNE:
                        need_partition = True
                    go_home(d, t, "GCS link lost")
                if d.task in AIRBORNE and d.task not in ("RTH", "LANDING", "ABORT_LANDING", "TAKEOFF"):
                    need = guards.energy_to_return(float(np.linalg.norm(d.pos - d.pad_slot)), sc.v_cruise, drain)
                    if guards.low_battery(d.energy, need, sc.battery_margin_frac):
                        go_home(d, t, "low battery")
                        need_partition = True

            # 3. motion
            for d in drones:
                d.vel = np.zeros(2)
                if d.task == "TAKEOFF":
                    d.timer -= sc.dt
                    if d.timer <= 0:
                        plan_for(d, initial_cells[d.drone_id - 1])
                elif d.task == "SEARCH":
                    if d.seg_i >= len(d.segments):
                        d.task = "HOLD"
                        need_partition = bool((~covered).any())
                    else:
                        target = d.segments[d.seg_i, d.seg_phase]
                        far = np.linalg.norm(target - d.pos) > 2 * spacing
                        if move(d, target, sc.v_cruise if (d.seg_phase == 0 and far) else sc.v_sweep):
                            d.seg_i, d.seg_phase = (d.seg_i, 1) if d.seg_phase == 0 else (d.seg_i + 1, 0)
                    covered |= ((points - d.pos) ** 2).sum(axis=1) <= (width / 2.0) ** 2
                elif d.task == "DELIVER":
                    tag = tags[d.target_sid]
                    if d.timer > 0:
                        d.timer -= sc.dt
                        if d.timer <= 0:
                            dist = np.linalg.norm(survivors - d.pos, axis=1) if len(survivors) else np.array([math.inf])
                            miss = float(dist.min())
                            d.kits -= 1
                            tag.status, tag.t_delivered, tag.miss_m = SurvivorStatus.DELIVERED, t, miss
                            deliveries.append(DeliveryEvent(SCHEMA_VERSION, d.drone_id, d.target_sid, t,
                                                            [d.pos[0], d.pos[1], sc.altitude_m], [0, 0, 0], miss, True))
                            log(t, f"drone {d.drone_id} delivered kit to {d.target_sid} (miss {miss:.2f} m)")
                            d.target_sid, d.task, d.segments, d.seg_i = None, "HOLD", np.zeros((0, 2, 2)), 0
                            need_partition = True
                    elif move(d, tag.track.p_surv[:2], sc.v_cruise):
                        d.timer = sc.delivery_dwell_s
                elif d.task == "RTH":
                    if move(d, d.pad_slot, sc.v_cruise):
                        d.task, d.timer = "LANDING", sc.altitude_m / sc.v_vertical
                elif d.task in ("LANDING", "ABORT_LANDING"):
                    d.timer -= sc.dt
                    if d.timer <= 0:
                        d.landed_in_pad = bool(dwvt.point_in_polygon(d.pos[None, :], pad.vertices_xy)[0])
                        d.task = "LANDED" if d.landed_in_pad else "LANDED_OFF_PAD"
                        log(t, f"drone {d.drone_id} landed {'on the pad' if d.landed_in_pad else 'OFF the pad'}")
                if d.task in AIRBORNE:
                    d.energy -= drain * sc.dt
                    if d.energy <= 0:
                        d.energy, d.task = 0.0, "CRASHED"
                        log(t, f"drone {d.drone_id} ran out of energy in the air")

            # 4. sensing: detector on every frame, onboard confirmation [P2 §4.3, §9.3]
            for d in drones:
                if d.task not in SENSING:
                    continue
                for xy, c_mean, c_std, p_det in (
                        [(s, det["conf_mean"], det["conf_std"], det["p_detect"]) for s in survivors]
                        + [(np.array(k["xy"], dtype=float), k["confidence"], 0.0, 1.0) for k in sc.decoys]):
                    if np.linalg.norm(xy - d.pos) <= width / 2.0:
                        for f in range(frames_per_step):
                            if rng.random() < p_det:
                                c = _clip(rng.normal(c_mean, c_std), 0.01, 0.99)
                                observe(d, xy, c, t - sc.dt + (f + 1) * sc.dt / frames_per_step)
                for _ in range(rng.poisson(det["fp_rate_hz"] * sc.dt)):
                    r, a = width / 2.0 * math.sqrt(rng.random()), rng.random() * 2 * math.pi
                    c = _clip(rng.normal(det["fp_conf_mean"], det["fp_conf_std"]), 0.01, 0.99)
                    observe(d, d.pos + r * np.array([math.cos(a), math.sin(a)]), c, t)

            # 5. reports reach the GCS over the link; duplicates within r_tol are merged [P2 Eq. 263]
            for d in drones:
                if not d.link_up:
                    continue
                for track in d.outbox:
                    if any(np.linalg.norm(g.track.p_surv[:2] - track.p_surv[:2]) <= conf["r_tol_m"]
                           for g in tags.values()):
                        continue
                    dist = np.linalg.norm(survivors - track.p_surv[:2], axis=1) if len(survivors) else np.array([])
                    hit = int(np.argmin(dist)) if dist.size and dist.min() <= conf["r_tol_m"] else None
                    tags[track.survivor_id] = _Tag(track, SurvivorStatus.CONFIRMED, t, d.drone_id, hit,
                                                   None if hit is None else float(dist[hit]))
                    log(t, f"survivor {track.survivor_id} tagged by drone {d.drone_id}"
                           + ("" if hit is not None else " (FALSE tag)"))
                    for other in drones:
                        if other is not d and other.link_up:
                            other.confirmer.merge_remote(track)
                d.outbox.clear()

            # 6. survivor auction at the GCS [P2 §7.3]
            if phase == MissionPhase.RUNNING:
                waiting = [g.track for g in tags.values() if g.status == SurvivorStatus.CONFIRMED]
                if waiting:
                    flying = [d for d in drones if d.task in AIRBORNE and d.task not in ("RTH", "LANDING")
                              and not d.gcs_lost]
                    committed = sum(g.status == SurvivorStatus.ASSIGNED for g in tags.values())
                    if sum(d.kits for d in flying) - committed <= 0:
                        for g in tags.values():
                            if g.status == SurvivorStatus.CONFIRMED:
                                g.status = SurvivorStatus.UNSERVICEABLE
                                log(t, f"survivor {g.track.survivor_id}: no kit left (OQ-01)")
                    else:
                        eligible = {d.drone_id: status_of(d, t) for d in flying
                                    if d.task in ("SEARCH", "HOLD") and d.kits > 0}
                        frac = {i: float((~covered[cell.get(i, np.zeros(0, dtype=int))]).sum()) / len(points)
                                for i in eligible}
                        made, _ = auction.run(waiting, eligible, frac, t)
                        for a in made:
                            d = by_id[a.drone_id]
                            d.task, d.target_sid, d.timer = "DELIVER", a.survivor_id, 0.0
                            tags[a.survivor_id].status = SurvivorStatus.ASSIGNED
                            tags[a.survivor_id].assigned_to = a.drone_id
                            assignments.append(a)
                            need_partition = True
                            log(t, f"auction: drone {a.drone_id} -> {a.survivor_id} (cost {a.cost:.1f})")

            # 7. re-partition the unsearched area [P2 §7.1]
            if need_partition and phase == MissionPhase.RUNNING:
                repartition(t)
            need_partition = False

            # 8. completion: area covered and nothing left to deliver -> everyone returns [BRIEF §3]
            if phase == MissionPhase.RUNNING:
                pending = any(g.status in (SurvivorStatus.CONFIRMED, SurvivorStatus.ASSIGNED) for g in tags.values())
                searching = any(d.task in ("SEARCH", "TAKEOFF") for d in drones)
                done_cover = covered.mean() >= sc.coverage_target
                nobody_left = not any(d.task in ("SEARCH", "HOLD", "DELIVER", "TAKEOFF") for d in drones)
                if (done_cover and not pending and not searching) or nobody_left:
                    phase = MissionPhase.RETURNING
                    log(t, f"search complete (coverage {covered.mean():.3f}); all drones return")
                    for d in drones:
                        go_home(d, t, "mission complete")

            # 9. measurements (no avoidance is simulated: these are observations, not guarantees)
            air = [d for d in drones if d.task in AIRBORNE]
            for d in air:
                if not dwvt.point_in_polygon(d.pos[None, :], mission.boundary.vertices_xy)[0]:
                    fence_viol += 1
                    if fence_viol == 1:
                        log(t, f"geofence: drone {d.drone_id} outside the boundary at {d.pos.round(1)} ({d.task})")
            away = [d for d in air if np.linalg.norm(d.pos - pad_c) > sc.pad_exclusion_radius_m]
            for i in range(len(away)):
                for j in range(i + 1, len(away)):
                    sep = float(np.linalg.norm(away[i].pos - away[j].pos))
                    if sep < min_sep:
                        min_sep, min_sep_at = sep, (round(t, 1), away[i].drone_id, away[i].task,
                                                    away[j].drone_id, away[j].task)
                    sep_viol += sep < sc.d_safe_m
            if t >= next_status:
                next_status = t + 1.0
                for d in drones:
                    if d.link_up:
                        gstate.ingest(status_of(d, t))

        if all(d.task in TERMINAL for d in drones):
            phase = MissionPhase.COMPLETE
        true_tags = [g for g in tags.values() if g.true_index is not None]
        delivered_true = {g.true_index for g in true_tags if g.status == SurvivorStatus.DELIVERED}
        tagged_true = {g.true_index for g in true_tags}
        no_kit = {g.true_index for g in true_tags if g.status == SurvivorStatus.UNSERVICEABLE}
        display = GcsDisplayModel(
            mission, {}, gstate.statuses(), {i: gstate.display_position(i, t) for i in gstate.drone_ids()},
            gstate.stale(t, 5.0), tuple(dataclasses.replace(g.track, status=g.status) for g in tags.values()),
            tuple(deliveries), tuple(assignments), float(covered.mean()), phase, t, {}, allowed_actions(phase))
        return MissionResult(
            scenario=sc.name, phase=phase, mission_time_s=t, within_30_min=t <= MAX_FLIGHT_S,
            coverage_fraction=float(covered.mean()),
            coverage_lower_bound_s=mission.area_m2 / (sc.n_drones * width * sc.v_sweep),
            survivors_total=len(survivors), survivors_tagged=len(tagged_true),
            survivors_delivered=len(delivered_true), survivors_without_kit=len(no_kit),
            false_tags=sum(g.true_index is None for g in tags.values()),
            false_deliveries=sum(g.true_index is None and g.status == SurvivorStatus.DELIVERED for g in tags.values()),
            tags=[dataclasses.asdict(dataclasses.replace(g, track=None)) | {"id": g.track.survivor_id}
                  for g in tags.values()],
            deliveries=deliveries,
            drones={d.drone_id: {"task": d.task, "energy": round(d.energy, 3), "kits": d.kits,
                                 "landed_in_pad": d.landed_in_pad, "path_m": round(d.path_m, 1)} for d in drones},
            min_separation_m=min_sep, min_separation_at=min_sep_at, separation_violations=int(sep_viol),
            geofence_violation_steps=fence_viol,
            crashed=sum(d.task == "CRASHED" for d in drones), timeline=timeline, display=display)
