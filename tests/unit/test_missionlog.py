"""Mission log: CT-05 backward-compatible reader; contracts serialise. [ADIAT-inspired: versioned result files]"""
from __future__ import annotations

import json

import numpy as np
import pytest

from nidar.common import missionlog
from nidar.common.contracts import SCHEMA_VERSION, AssignmentCostTerms, DroneState
from nidar.common.missionlog import MissionLogError, MissionLogReader, MissionLogWriter


def _state() -> DroneState:
    return DroneState(1, 0.5, [1, 2, 3], [0, 0, 0], [1, 0, 0, 0], [0, 0, 0])


def test_round_trip(tmp_path) -> None:
    path = tmp_path / "m.jsonl"
    w = MissionLogWriter(path, "test-mission")
    w.append("state", 0.5, _state())
    w.append("cost", 0.6, AssignmentCostTerms(10.0, 0.1, float("inf")))
    w.append("iq", 0.7, np.array([1 + 2j, 3 - 1j]))
    r = MissionLogReader(path)
    recs = list(r.records())
    assert r.mission_id == "test-mission" and r.schema_version == SCHEMA_VERSION
    assert recs[0]["body"]["p"]["data"] == [1.0, 2.0, 3.0]
    assert recs[1]["body"]["payload_term"] == {"__float__": "inf"}
    assert recs[2]["body"]["re"] == [1.0, 3.0]


def test_never_overwrites(tmp_path) -> None:
    path = tmp_path / "m.jsonl"
    MissionLogWriter(path, "a")
    with pytest.raises(FileExistsError):
        MissionLogWriter(path, "b")


def test_ct05_backward_compatible_reader(tmp_path, monkeypatch) -> None:
    """An older log is upgraded through registered migrations; a newer one is refused."""
    old = tmp_path / "old.jsonl"
    old.write_text(json.dumps({"type": "header", "schema_version": 0, "mission_id": "x"}) + "\n"
                   + json.dumps({"type": "record", "kind": "k", "t": 0, "body": {"v": 1}}) + "\n", encoding="utf-8")
    with pytest.raises(MissionLogError, match="no migration"):
        MissionLogReader(old)
    monkeypatch.setitem(missionlog.MIGRATIONS, 0, lambda rec: {**rec, "migrated": True})
    assert [r["migrated"] for r in MissionLogReader(old).records()] == [True]

    new = tmp_path / "new.jsonl"
    new.write_text(json.dumps({"type": "header", "schema_version": SCHEMA_VERSION + 1}) + "\n", encoding="utf-8")
    with pytest.raises(MissionLogError, match="newer"):
        MissionLogReader(new)
