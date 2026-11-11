"""Contract validation tests (docs/INTERFACES.md). CT-07 source-frame pixels [ADIAT-inspired: StreamDetection]."""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from nidar.common.contracts import (
    AssignmentCostTerms,
    AuctionAssignment,
    CertifiedFloorDesign,
    Detection,
    DroneState,
    DroneStatus,
    EstimatorHealth,
    GcsCommand,
    GeoPolygon,
    MissionDefinition,
    ResourcePlan,
    SurvivorStatus,
    SurvivorTrack,
)

SQUARE = [[0, 0], [100, 0], [100, 100], [0, 100]]


def _det(**kw) -> Detection:
    base = dict(drone_id=1, t_source=0.0, frame_size_wh=(640, 480), bbox_xyxy=(10, 20, 50, 100),
                centroid_uv=(30, 60), confidence=0.9, class_name="person")
    return Detection(**{**base, **kw})


def test_ct07_detection_in_source_frame_pixels() -> None:
    _det()
    with pytest.raises(ValueError, match="source frame"):
        _det(bbox_xyxy=(600, 20, 700, 100))          # outside a 640-wide frame
    with pytest.raises(ValueError, match="centroid"):
        _det(centroid_uv=(5, 5))
    with pytest.raises(ValueError):
        _det(confidence=1.2)
    with pytest.raises(ValueError):
        _det(keypoints=np.zeros((16, 3)))             # COCO-17 only [DATASET]


def test_contracts_are_frozen() -> None:
    s = DroneState(1, 0.0, [0, 0, 0], [0, 0, 0], [1, 0, 0, 0], [0, 0, 0])
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.drone_id = 2
    assert s.as_vector().shape == (13,)
    assert not s.p.flags.writeable


def test_drone_state_requires_unit_quaternion() -> None:
    with pytest.raises(ValueError, match="unit quaternion"):
        DroneState(1, 0.0, [0, 0, 0], [0, 0, 0], [1, 1, 0, 0], [0, 0, 0])


def test_status_payload_consistency() -> None:
    st = DroneState(1, 0.0, [0, 0, 0], [0, 0, 0], [1, 0, 0, 0], [0, 0, 0])
    eh = EstimatorHealth(np.eye(3) * 0.01, True, True)
    assert eh.trace_pos_m2 == pytest.approx(0.03)
    kw = dict(schema_version=1, state=st, mode="SEARCH", battery_energy_j=50.0, battery_energy_max_j=100.0,
              search_active=True, cbf_active={"terrain": False}, nmpc_feasible=True, estimator=eh)
    DroneStatus(**kw, payload_present=True, kits_remaining=1)
    with pytest.raises(ValueError, match="payload_present"):
        DroneStatus(**kw, payload_present=True, kits_remaining=0)


def test_polygon_and_mission_area() -> None:
    poly = GeoPolygon(np.array(SQUARE), datum="local")
    assert poly.area_m2 == pytest.approx(10_000)
    with pytest.raises(ValueError, match="counter-clockwise"):
        GeoPolygon(np.array(SQUARE[::-1]), datum="local")
    big = GeoPolygon(np.array([[0, 0], [400, 0], [400, 400], [0, 400]]), datum="local")
    with pytest.raises(ValueError, match="10 ha"):
        MissionDefinition(1, "0" * 64, big, None)


def test_assignment_requires_payload() -> None:
    terms = AssignmentCostTerms(10.0, 0.1, float("inf"))
    with pytest.raises(ValueError):
        AuctionAssignment(1, 0.0, 1, "s1", 10.0, terms, "hungarian")


def test_resource_plan_sums() -> None:
    ResourcePlan(1, 0, 100, 6, 4, 30, 60, "d1")
    with pytest.raises(ValueError, match="must equal n_total"):
        ResourcePlan(1, 0, 100, 6, 4, 30, 61, "d1")


def test_certified_design_rules() -> None:
    kw = dict(design_id="d", gamma_f_db=10.0, n_f=400, L=4, m=100, b_f_bits=1000, eps_core=1e-3, margin_db=3.0,
              dt_upper_bound=4e-4, n_samples=10**6, confidence_delta=1e-6)
    d = CertifiedFloorDesign(**kw)
    assert not d.includes_clipping and not d.includes_estimation_error   # paper's certificate gap (P-7)
    with pytest.raises(ValueError, match="L \\* m"):
        CertifiedFloorDesign(**{**kw, "n_f": 401})
    with pytest.raises(ValueError, match="eps_core / 2"):
        CertifiedFloorDesign(**{**kw, "dt_upper_bound": 6e-4})


def test_survivor_track_lifecycle() -> None:
    base = dict(schema_version=1, survivor_id="s", p_surv=[0, 0, 0], sigma_surv=np.eye(3), belief=0.5,
                consistent_frames=3, observing_drones=frozenset({1}), t_first_seen=0.0)
    SurvivorTrack(**base, status=SurvivorStatus.CANDIDATE)
    with pytest.raises(ValueError, match="t_confirmed"):
        SurvivorTrack(**base, status=SurvivorStatus.CONFIRMED)


def test_command_kinds_closed() -> None:
    GcsCommand(1, 0, 0.0, "recall", None)
    with pytest.raises(ValueError, match="unknown command kind"):
        GcsCommand(1, 0, 0.0, "set_waypoint", 1)
