"""GT-02: the GCS exposes exactly the four Brief actions, gated by mission phase. [BRIEF §3, §4, §8]"""
from __future__ import annotations

import pytest

from nidar.common.contracts import MissionPhase, OperatorAction
from nidar.gcs.controllers.operator_actions import ActionNotPermitted, allowed_actions, check_action


def test_gt02_exactly_four_actions_gated_by_phase() -> None:
    assert OperatorAction.ALL == {"load_mission_file", "start_mission", "safety_abort", "emergency_recall"}
    union = set().union(*(allowed_actions(p) for p in MissionPhase.ALL))
    assert union == OperatorAction.ALL
    assert allowed_actions(MissionPhase.READY) >= {OperatorAction.START_MISSION}
    for phase in MissionPhase.ALL - {MissionPhase.READY}:
        assert OperatorAction.START_MISSION not in allowed_actions(phase), phase
    for phase in (MissionPhase.READY, MissionPhase.RUNNING, MissionPhase.RETURNING):
        assert {OperatorAction.SAFETY_ABORT, OperatorAction.EMERGENCY_RECALL} <= allowed_actions(phase)


@pytest.mark.parametrize("action", ["manual_waypoint", "drop_payload", "tag_survivor", "replan"])
def test_manual_intervention_inputs_rejected(action: str) -> None:
    """Examples of manual intervention listed in [BRIEF §3] have no input path."""
    with pytest.raises(ActionNotPermitted):
        check_action(action, MissionPhase.RUNNING)


def test_load_not_allowed_while_running() -> None:
    with pytest.raises(ActionNotPermitted):
        check_action(OperatorAction.LOAD_MISSION_FILE, MissionPhase.RUNNING)
    check_action(OperatorAction.EMERGENCY_RECALL, MissionPhase.RUNNING)
