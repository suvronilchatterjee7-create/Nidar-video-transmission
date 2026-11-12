"""Unit tests for swarm and GCS logic: auction (PT-15, PT-16), cost forms, DWVT (PT-10, PT-11, PT-14),
confirmation (PT-09), coverage (PT-12), Dubins (PT-13), payload reset (PT-05), guards, priority mux (CT-15),
resource plan, GeoJSON mission file (GT-01), preflight, global state. [P2 §5, §7, §8.4, §9.3, §12]"""
from __future__ import annotations

import itertools
import json
import math

import numpy as np
import pytest

from nidar.common.contracts import (
    CertifiedFloorDesign,
    Detection,
    DroneState,
    DroneStatus,
    EstimatorHealth,
    GeoPolygon,
    GeotagObservation,
)
from nidar.gcs import mission_loader
from nidar.gcs.global_state import GlobalState
from nidar.gcs.preflight import FAIL, PASS, PENDING, PreflightRunner
from nidar.link.priority_mux import PriorityMux
from nidar.link.resource_plan import plan_gop
from nidar.onboard.automaton import guards
from nidar.onboard.payload import hybrid_reset
from nidar.onboard.planning import coverage_bcd, dubins
from nidar.swarm import dwvt
from nidar.swarm.auction import cost
from nidar.swarm.auction.hungarian import HungarianAuction
from nidar.swarm.confirmation import BayesianConfirmer, bayes_update

SQUARE = GeoPolygon(np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=float), "local")
L_SHAPE = GeoPolygon(np.array([[0, 0], [120, 0], [120, 40], [40, 40], [40, 120], [0, 120]], dtype=float), "local")


def _status(drone_id: int, xy, energy=1.0, payload=True, t=0.0, v=(0, 0, 0)) -> DroneStatus:
    st = DroneState(drone_id, t, [xy[0], xy[1], 20.0], list(v), [1, 0, 0, 0], [0, 0, 0])
    return DroneStatus(1, st, "SEARCH", energy, 1.0, payload, 1 if payload else 0, True, {}, True,
                       EstimatorHealth(np.eye(3) * 0.01, True, True))


# ---------------- auction ----------------
@pytest.mark.parametrize("seed", range(30))
def test_pt15_hungarian_matches_brute_force(seed) -> None:
    rng = np.random.default_rng(seed)
    n_d, n_s = rng.integers(1, 5), rng.integers(1, 5)
    c = rng.uniform(1, 100, (n_d, n_s))
    c[rng.random((n_d, n_s)) < 0.2] = math.inf
    res = HungarianAuction().assign(c, list(range(n_d)), [f"s{j}" for j in range(n_s)]).payload
    best_count, best_cost = 0, math.inf                    # max survivors served, then min cost
    for perm in itertools.permutations(range(max(n_d, n_s))):
        pairs = [(i, perm[i]) for i in range(n_d) if perm[i] < n_s and math.isfinite(c[i, perm[i]])]
        k, s = len(pairs), sum(c[i, j] for i, j in pairs)
        if k > best_count or (k == best_count and s < best_cost - 1e-9):
            best_count, best_cost = k, s
    assert len(res.assignments) == best_count
    assert sum(a[2] for a in res.assignments) == pytest.approx(best_cost if best_count else 0.0)
    assert len({a[0] for a in res.assignments}) == len(res.assignments)        # one task per drone [Eq. 183]


def test_pt16_more_survivors_than_kits_is_reported_not_failed() -> None:
    c = np.array([[1.0, 2.0, 3.0], [2.0, 1.0, 3.0]])
    res = HungarianAuction().assign(c, [1, 2], ["a", "b", "c"]).payload
    assert not res.feasible and res.unassigned_survivors == ("c",)
    no_payload = HungarianAuction().assign(np.full((1, 1), math.inf), [1], ["a"]).payload
    assert no_payload.assignments == () and no_payload.unassigned_survivors == ("a",)


def test_cost_forms() -> None:
    s = _status(1, (0, 0), energy=0.5)
    t179 = cost.cost_eq179(s, np.array([80.0, 0, 0]), 8.0, {"alpha1": 10, "alpha2": 0, "alpha3": 50}, 0.2)
    assert (t179.time_to_intercept_s, t179.battery_term, t179.abandonment_term) == pytest.approx((10, 5, 10))
    t38 = cost.cost_eq38(s, np.array([80.0, 0, 0]), 8.0, {"alpha": 2, "beta": 1, "gamma": 0})
    assert (t38.time_to_intercept_s, t38.battery_term) == pytest.approx((20, 2))
    assert math.isinf(cost.total(cost.cost_eq179(_status(1, (0, 0), payload=False), np.zeros(3), 8.0,
                                                 {"alpha1": 1, "alpha2": 0, "alpha3": 0}, 0.0)))


# ---------------- DWVT ----------------
def test_pt10_cells_tile_the_area() -> None:
    pts = dwvt.rasterise(SQUARE, 2.0)
    assert len(pts) * 4.0 == pytest.approx(SQUARE.area_m2, rel=0.01)
    labels = dwvt.assign(pts, np.array([[20.0, 20], [80, 80], [20, 80]]), np.ones(3))
    assert set(np.unique(labels)) == {0, 1, 2} and len(labels) == len(pts)        # disjoint, complete


def test_pt11_smaller_weight_gives_smaller_cell() -> None:
    pts = dwvt.rasterise(SQUARE, 2.0)
    gen = np.array([[30.0, 50], [70, 50]])
    equal = np.bincount(dwvt.assign(pts, gen, np.array([1.0, 1.0])))
    shrunk = np.bincount(dwvt.assign(pts, gen, np.array([0.5, 1.0])))
    assert shrunk[0] < equal[0] and equal[0] == pytest.approx(equal[1], rel=0.05)


def test_lloyd_converges_to_balanced_cells() -> None:
    pts = dwvt.rasterise(SQUARE, 2.0)
    g, labels = dwvt.lloyd(pts, dwvt.farthest_point_seeds(pts, 4, np.array([0.0, 0.0])), np.ones(4))
    sizes = np.bincount(labels)
    assert sizes.min() / sizes.max() > 0.8


def test_density_kernel_pulls_centroid() -> None:
    from nidar.common.contracts import DensityKernel
    pts = dwvt.rasterise(SQUARE, 2.0)
    labels = np.zeros(len(pts), dtype=int)
    plain = dwvt.centroids(pts, labels, 1)[0]
    pulled = dwvt.centroids(pts, labels, 1, dwvt.density(pts, (DensityKernel(np.array([90.0, 90]), 5.0, 10.0),)))[0]
    assert np.all(pulled > plain)                                                  # [P2 Eq. 167]


def test_pt14_hysteresis_prevents_chattering() -> None:
    pts = dwvt.rasterise(SQUARE, 2.0)
    labels = dwvt.assign(pts, np.array([[25.0, 50], [75, 50]]), np.ones(2))
    owner = 0
    for x in (49.5, 50.5, 49.5, 51.0, 52.0):                                       # jitter across the edge
        owner = dwvt.owner_with_hysteresis(np.array([x, 50.0]), owner, pts, labels, eps_h_m=5.0)
        assert owner == 0
    assert dwvt.owner_with_hysteresis(np.array([60.0, 50.0]), 0, pts, labels, eps_h_m=5.0) == 1
    assert dwvt.boundary_speed(4.0, 0.5, 0.0) == 0.0 and dwvt.boundary_speed(4.0, 0.5, 50.0) == pytest.approx(4.0)


def test_weight_laws() -> None:
    assert dwvt.weight_linear(0.8, True, 0.5, 0.5, 0.05) == pytest.approx(0.9)
    assert dwvt.weight_linear(0.0, False, 0.5, 0.5, 0.05) == 0.05                  # w_min [P2 Eq. 107]
    assert dwvt.weight_multiplicative(1.0, 0.5, 0.05) == 0.5                       # [P2 Eq. 30]


def test_partitioner_contract() -> None:
    p = dwvt.DwvtPartitioner(resolution_m=2.0)
    up = p.partition(SQUARE, {1: (20, 20), 2: (80, 80)}, {1: 1.0, 2: 1.0})
    assert {c.drone_id for c in up.cells} == {1, 2}
    assert set(p.centroids(up)) == {1, 2}


# ---------------- confirmation ----------------
def _obs(xy, conf, t, drone=1, low=False) -> GeotagObservation:
    det = Detection(drone, t, (640, 480), (300, 220, 340, 260), (320, 240), conf, "person")
    return GeotagObservation(det, np.array([*xy, 0.0]), np.eye(3) * 0.25, low, 20.0)


def test_pt09_bayes_update_arithmetic() -> None:
    p = 0.01                                                                       # [P2 Eq. 259]
    for _ in range(10):
        p = bayes_update(p, 0.85)
    assert p > 0.95                                                                # [P2 Eq. 265]
    assert bayes_update(0.01, 0.5) == pytest.approx(0.01)                          # an uninformative frame


def test_confirmation_needs_k_frames_and_threshold() -> None:
    c = BayesianConfirmer(r_tol_m=3.0, max_gap_s=1.0, id_prefix="T")
    out = [c.observe(_obs((10, 10), 0.99, 0.033 * k)) for k in range(12)]
    first = next(i for i, o in enumerate(out) if o is not None)
    assert first == 9                                                              # K = 10 [P2 Eq. 262]
    assert sum(o is not None for o in out) == 1                                    # promoted once
    assert out[first].belief > 0.95 and np.linalg.norm(out[first].p_surv[:2] - [10, 10]) < 1.0


def test_confirmation_ignores_low_confidence_and_resets_on_gap() -> None:
    c = BayesianConfirmer(r_tol_m=3.0, max_gap_s=1.0, id_prefix="T")
    assert all(c.observe(_obs((5, 5), 0.99, 0.03 * k, low=True)) is None for k in range(20))   # [P2 Eq. 100]
    for k in range(9):
        c.observe(_obs((5, 5), 0.99, 0.03 * k))
    assert c.observe(_obs((5, 5), 0.99, 5.0)) is None                              # gap > max_gap resets K


def test_merge_remote_suppresses_duplicates() -> None:
    a = BayesianConfirmer(r_tol_m=3.0, max_gap_s=1.0, id_prefix="A")
    b = BayesianConfirmer(r_tol_m=3.0, max_gap_s=1.0, id_prefix="B")
    track = next(t for t in (a.observe(_obs((30, 30), 0.99, 0.03 * k)) for k in range(12)) if t is not None)
    b.merge_remote(track)                                                          # [P2 Eq. 263]
    assert all(b.observe(_obs((31, 30), 0.99, 0.03 * k, drone=2)) is None for k in range(15))


# ---------------- coverage ----------------
@pytest.mark.parametrize("poly", [SQUARE, L_SHAPE], ids=["square", "L"])
def test_pt12_sweeps_cover_every_point_and_stay_inside(poly) -> None:
    res = 2.0
    pts = dwvt.rasterise(poly, res)
    spacing = coverage_bcd.sweep_spacing(coverage_bcd.footprint_width(20.0, math.radians(60)), 0.1)
    segs = coverage_bcd.plan_segments(pts, spacing, res, np.array([0.0, 0.0]), poly.vertices_xy)
    mids = segs.mean(axis=1, keepdims=True)
    toward = mids - segs                                         # nudge each endpoint 1 mm along its sweep
    norm = np.linalg.norm(toward, axis=2, keepdims=True)
    inner = (segs + 1e-3 * np.divide(toward, norm, out=np.zeros_like(toward), where=norm > 0)).reshape(-1, 2)
    assert dwvt.point_in_polygon(inner, poly.vertices_xy).all()   # endpoints on or inside the boundary
    half_w = coverage_bcd.footprint_width(20.0, math.radians(60)) / 2.0
    a, b = segs[:, 0], segs[:, 1]
    ab = b - a
    t = np.clip(((pts[:, None, :] - a) * ab).sum(-1) / np.maximum((ab * ab).sum(-1), 1e-12), 0, 1)
    d = np.linalg.norm(pts[:, None, :] - (a + t[..., None] * ab), axis=-1).min(axis=1)
    assert (d <= half_w).mean() > 0.98                                             # nearly all on the first pass


def test_footprint_and_spacing() -> None:
    assert coverage_bcd.footprint_width(20.0, math.radians(60)) == pytest.approx(2 * 20 * math.tan(math.radians(30)))
    assert coverage_bcd.sweep_spacing(10.0, 0.15) == pytest.approx(8.5)            # [P2 Eq. 172-173]
    with pytest.raises(ValueError):
        coverage_bcd.sweep_spacing(10.0, 1.0)


def test_pt13_turn_radius() -> None:
    assert dubins.min_turn_radius(8.0, math.radians(30)) == pytest.approx(64 / (9.81 * math.tan(math.radians(30))))
    assert dubins.u_turn_length(30.0, 10.0) == pytest.approx(math.pi * 15)
    assert dubins.u_turn_length(5.0, 10.0) > math.pi * 10                          # bulb turn is longer


# ---------------- payload, guards ----------------
def test_pt05_payload_drop_feedforward() -> None:
    assert hybrid_reset.thrust_feedforward_delta(0.2) == pytest.approx(-1.962)      # [P2 Eq. 155]
    assert hybrid_reset.mass_after_drop(4.8, 0.2) == pytest.approx(4.6)             # [P2 Eq. 228]
    assert hybrid_reset.acceleration_step(4.8, 0.2) == pytest.approx(0.4265, abs=1e-4)   # [P2 Eq. 230]
    assert np.allclose(hybrid_reset.torque_feedforward(0.2, np.array([0.1, 0, 0])), [0, 0.1962, 0])


def test_guards() -> None:
    assert guards.energy_to_return(800.0, 8.0, 1 / 1200) == pytest.approx(100 / 1200)
    assert guards.low_battery(0.15, 0.1, 0.1) and not guards.low_battery(0.3, 0.1, 0.1)
    assert guards.gcs_link_lost(5.5, 5.0) and not guards.gcs_link_lost(3.0, 5.0)


# ---------------- link ----------------
def test_ct15_priority_order_under_overload() -> None:
    sent = PriorityMux().schedule({"video": [100] * 5, "map": [50] * 2, "state": [10] * 3}, capacity=200)
    assert sent == {"video": 0, "map": 2, "state": 3}                              # state > map > video
    capped = PriorityMux(caps={"state": 20}).schedule({"state": [10] * 3, "video": [50]}, capacity=100)
    assert capped == {"state": 2, "video": 1}
    with pytest.raises(ValueError):
        PriorityMux().schedule({"chat": [1]}, 10)


def test_resource_plan() -> None:
    d = CertifiedFloorDesign("d", 10.0, 400, 4, 100, 1000, 1e-3, 3.0, 4e-4, 10**6, 1e-6)
    p = plan_gop(1, 0, 1000, 24, 50, d)
    assert p.n_refinement == 526 and p.n_floor == 400
    assert plan_gop(1, 0, 450, 24, 50, d) is None                                  # floor does not fit (OQ-24)


# ---------------- GCS: mission file, preflight, state ----------------
def test_gt01_geojson_lonlat_is_projected_to_metres() -> None:
    lat = 20.0
    dlat = 100.0 / 6_371_008.8 * 180 / math.pi
    dlon = dlat / math.cos(math.radians(lat))
    ring = [[85.0, lat], [85.0 + dlon, lat], [85.0 + dlon, lat + dlat], [85.0, lat + dlat], [85.0, lat]]
    doc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"role": "boundary"}, "geometry": {"type": "Polygon", "coordinates": [ring]}},
        {"type": "Feature", "properties": {"role": "launch_zone"},
         "geometry": {"type": "Polygon", "coordinates": [[[85.0, lat], [85.00003, lat], [85.00003, lat + 0.00003],
                                                          [85.0, lat + 0.00003], [85.0, lat]]]}}]}
    res = mission_loader.load(json.dumps(doc).encode(), "boundary.geojson")
    assert res.ok, res.error_message
    m = res.payload
    assert m.area_m2 == pytest.approx(10_000, rel=0.01) and m.launch_zone is not None
    assert len(m.source_file_sha256) == 64 and "WGS-84" in m.boundary.datum


def test_mission_file_errors_name_the_file() -> None:
    too_big = {"type": "Polygon", "units": "metres", "coordinates": [[[0, 0], [400, 0], [400, 400], [0, 400], [0, 0]]]}
    res = mission_loader.load(json.dumps({**too_big, "units": None}).encode(), "big.geojson")
    assert not res.ok
    res = mission_loader.load(json.dumps(too_big).encode(), "big.geojson")
    assert not res.ok and "big.geojson" in res.error_message and "10 ha" in res.error_message
    assert not mission_loader.load(b"{}", "empty.geojson").ok


def test_preflight_gates() -> None:
    runner = PreflightRunner(eps_lidar_m2=0.5, min_battery_frac=0.9, link_timeout_s=2.0)
    ok = {1: _status(1, (0, 0), t=10.0), 2: _status(2, (1, 0), t=10.0)}
    square = {"type": "Polygon", "units": "metres", "coordinates": [[[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]]]}
    m = mission_loader.load(json.dumps(square).encode(), "b.geojson").payload
    gates = runner.run(m, ok, now=11.0, fleet_weight_kg=19.2, video_floor_ok=lambda: True)
    assert PreflightRunner.ready(gates)
    bad = runner.run(None, {1: _status(1, (0, 0), energy=0.5, payload=False, t=0.0)}, now=11.0)
    assert bad["mission_loaded"] == PENDING and bad["fleet_size"] == FAIL and bad["payload"] == FAIL
    assert bad["link_up"] == FAIL and bad["battery"] == FAIL and bad["fleet_weight"] == PENDING
    assert not PreflightRunner.ready(bad) and gates["estimator"] == PASS


def test_global_state_matrix_order_and_predictor() -> None:
    g = GlobalState()
    assert g.ingest(_status(2, (0, 0), t=1.0, v=(1, 0, 0)))
    assert g.ingest(_status(1, (5, 5), t=1.0))
    assert not g.ingest(_status(2, (9, 9), t=0.5))                                 # out of order: ignored
    assert g.ingest(_status(2, (1, 0), t=2.0, v=(2, 0, 0)))
    assert g.matrix().shape == (2, 13) and g.matrix()[1, 0] == 1.0
    assert g.display_position(2, 3.0)[0] == pytest.approx(1 + 2 + 0.5)            # a = 1 m/s^2 [P2 §14.3]
    assert g.stale(now=10.0, max_age_s=5.0) == {1: True, 2: True}
