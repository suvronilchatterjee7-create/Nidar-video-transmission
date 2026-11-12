"""Mission-level scenario tests on the kinematic simulator (MS-xx, GT-xx). Points move at set speeds: these
test mission logic, failsafes and timing, not flight dynamics. Scenario values are placeholders
(sim/scenarios/*.json). [BRIEF §1-§8] [P2 §5, §7, §9, §12]"""
from __future__ import annotations

from pathlib import Path

import pytest

from nidar.common.contracts import MissionPhase, OperatorAction, SurvivorStatus
from sim.mission.kinematic import MissionSimulator, Scenario

SC = Path(__file__).resolve().parents[2] / "sim" / "scenarios"


def _run(name: str):
    return MissionSimulator().run(Scenario.load(SC / f"{name}.json"))


@pytest.fixture(scope="module")
def baseline():
    return _run("baseline_p2")


def test_ms03_baseline_completes_within_30_minutes(baseline) -> None:
    r = baseline
    assert r.phase == MissionPhase.COMPLETE and r.within_30_min
    assert r.coverage_fraction >= 0.999
    assert r.mission_time_s > r.coverage_lower_bound_s                       # ideal bound [P2 §12.2.3]


def test_ms13_ten_survivors_tagged_kits_delivered_rest_reported(baseline) -> None:
    r = baseline
    assert r.survivors_tagged == 10 and r.false_tags == 0
    assert r.survivors_delivered == 4 and r.survivors_without_kit == 6       # 4 drones x 1 kit (OQ-01)
    assert all(d.miss_distance_est_m < 2.0 for d in r.deliveries)


def test_ms04_work_is_shared(baseline) -> None:
    assert len({d.drone_id for d in baseline.deliveries}) == 4                # every drone delivers
    paths = [v["path_m"] for v in baseline.drones.values()]
    assert min(paths) > 0.4 * max(paths)                                      # parallel scouting


def test_ms05_all_land_inside_the_pad(baseline) -> None:
    assert all(v["landed_in_pad"] for v in baseline.drones.values())        # [BRIEF §7]
    assert baseline.crashed == 0


def test_planned_paths_stay_inside_the_geofence(baseline) -> None:
    assert baseline.geofence_violation_steps == 0                            # [BRIEF §7]


def test_gt05_to_gt09_display_model_has_everything_the_brief_requires(baseline) -> None:
    d = baseline.display
    assert d.mission_loaded is not None                                       # boundary loaded
    assert len(d.drones) == 4 and len(d.display_positions) == 4               # live location and status
    assert len(d.survivors) >= 10                                             # tagged survivors
    assert {e.drone_id for e in d.deliveries} == {1, 2, 3, 4}                 # delivery status per drone
    assert d.coverage_fraction >= 0.999 and d.mission_phase == MissionPhase.COMPLETE   # progress / completion
    statuses = {s.status for s in d.survivors}
    assert statuses <= {SurvivorStatus.DELIVERED, SurvivorStatus.UNSERVICEABLE}


def test_ms01_two_drone_minimum_fleet() -> None:
    r = _run("two_drones")
    assert r.phase == MissionPhase.COMPLETE and r.within_30_min and r.survivors_delivered == 2


def test_kits_per_drone_setting_serves_everyone() -> None:
    r = _run("kits_3_per_drone")
    assert r.survivors_delivered == 10 and r.survivors_without_kit == 0 and r.within_30_min


def test_ms12_recall_returns_everyone_to_the_pad() -> None:
    r = _run("recall")
    assert any("operator recall" in m for _, m in r.timeline)
    assert all(v["landed_in_pad"] for v in r.drones.values()) and r.mission_time_s < 300


def test_ms11_abort_lands_everyone_in_place() -> None:
    r = _run("abort")
    assert any("SAFETY ABORT" in m for _, m in r.timeline)
    assert all(v["task"] in ("LANDED", "LANDED_OFF_PAD") for v in r.drones.values())
    assert not any(v["landed_in_pad"] for v in r.drones.values())           # OQ-16: land where they are
    assert r.mission_time_s < 215


def test_gt03_manual_inputs_are_rejected() -> None:
    r = _run("manual_input_rejected")
    rejected = [m for _, m in r.timeline if "rejected" in m]
    assert len(rejected) == 2 and "drop_payload" in rejected[0]               # [BRIEF §3]
    assert r.survivors_delivered == 4                                         # mission unaffected


def test_ms08_link_loss_triggers_onboard_return() -> None:
    r = _run("link_loss")
    assert any("drone 2 RTH (GCS link lost)" in m for _, m in r.timeline)    # [P2 Eq. 247-249]
    assert r.coverage_fraction >= 0.999 and r.phase == MissionPhase.COMPLETE
    assert all(v["landed_in_pad"] for v in r.drones.values())


def test_ms07_low_battery_returns_before_empty() -> None:
    r = _run("low_battery")
    assert any("low battery" in m for _, m in r.timeline)                    # [P2 Eq. 245-246]
    assert r.crashed == 0 and all(v["energy"] > 0 for v in r.drones.values())


def test_ms14_decoy_is_confirmed_by_the_paper2_rule() -> None:
    """Finding (RISK-S04, OQ-25): a decoy scored 0.7 on every frame passes the 0.95 threshold because
    Paper 2's update treats consecutive frames as independent evidence."""
    r = _run("decoy_debris")
    assert r.false_tags >= 1


def test_p2_early_variants_also_run() -> None:
    r = _run("p2_early_variants")
    assert r.phase == MissionPhase.COMPLETE and r.survivors_tagged == 10


def test_separation_is_measured_not_guaranteed(baseline) -> None:
    """The kinematic sim has no CBF avoidance [P2 §8.3]: it reports closest approaches instead."""
    assert baseline.min_separation_at is not None and baseline.min_separation_m >= 0.0


def test_runs_are_deterministic() -> None:
    a, b = _run("baseline_p2"), _run("baseline_p2")
    assert a.timeline == b.timeline


def test_operator_gate_used_by_the_simulator() -> None:
    assert OperatorAction.EMERGENCY_RECALL in OperatorAction.ALL
