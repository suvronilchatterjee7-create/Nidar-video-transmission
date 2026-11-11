"""Units, stubs, mode tables, mission loader. [BRIEF §2, §7] [P2 §1.2, §9.1, §13.1]"""
from __future__ import annotations

import importlib

import numpy as np
import pytest

from nidar.common import units
from nidar.common.stub import NotYetImplemented
from nidar.gcs import mission_loader
from nidar.onboard.automaton import automaton


def test_constants_match_brief() -> None:
    assert units.LAUNCH_PAD_SIDE_M == pytest.approx(3.6576)
    assert units.FLEET_MAX_KG == 25.0 and units.PAYLOAD_KG == 0.2 and units.MAX_FLIGHT_S == 1800.0


def test_quaternion_rotation() -> None:
    assert np.allclose(units.quat_to_rotmatrix([1, 0, 0, 0]), np.eye(3))
    r = units.quat_to_rotmatrix([np.cos(np.pi / 4), 0, 0, np.sin(np.pi / 4)])   # +90 deg yaw
    assert np.allclose(r @ [1, 0, 0], [0, 1, 0])
    assert np.allclose(r @ r.T, np.eye(3))
    with pytest.raises(ValueError):
        units.quat_normalize([0, 0, 0, 0])


def test_db_round_trip() -> None:
    assert units.linear_to_db(units.db_to_linear(7.3)) == pytest.approx(7.3)


@pytest.mark.parametrize("module, call", [
    ("nidar.video.decoder", lambda m: m.kalman_steady_state(0.9, 0.19, 3.0)),
    ("nidar.video.floor.designer", lambda m: m.intra_rate_bits(0.1, np.ones(3))),
    ("nidar.swarm.auction.hungarian", lambda m: m.HungarianAuction().assign(np.zeros((1, 1)), [1], ["s"])),
    ("nidar.onboard.payload.hybrid_reset", lambda m: m.thrust_feedforward_delta(0.2)),
])
def test_stubs_raise_not_yet_implemented_with_source(module, call) -> None:
    with pytest.raises(NotYetImplemented) as info:
        call(importlib.import_module(module))
    assert info.value.source and info.value.waits_for


def test_mode_tables_are_candidates_and_none_active() -> None:
    names = automaton.available_tables()
    assert names == ["p2_variant_a", "p2_variant_b"]
    assert automaton.ACTIVE_TABLE is None, "OQ-05a is undecided: no default mode table"
    for n in names:
        t = automaton.load_mode_table(n)
        assert t.status.startswith("CANDIDATE") and t.transitions
        assert all(tr.source for tr in t.transitions)


def test_mission_loader_without_parser_fails_cleanly() -> None:
    res = mission_loader.load(b"<unknown/>", "boundary.xyz")
    assert not res.ok and "boundary.xyz" in res.error_message and "OQ-22" in res.error_message
