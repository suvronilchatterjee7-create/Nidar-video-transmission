"""Registry tests: CT-03 (fail loudly), CT-08 (registered classes match their interfaces).
[ADIAT-inspired: algorithms.conf, CLAUDE.md §2.3]"""
from __future__ import annotations

import importlib
import json
import typing

import pytest

from nidar.common.registry import (
    PlatformMismatchError,
    Registry,
    RegistryError,
    UnknownComponentError,
)

REG = Registry.load()


def test_ct03_unknown_name_and_platform_fail_loudly() -> None:
    with pytest.raises(UnknownComponentError, match="no_such_component"):
        REG.resolve("no_such_component", "gcs")
    with pytest.raises(PlatformMismatchError, match="hungarian_auction"):
        REG.resolve("hungarian_auction", "onboard")   # GCS-run per [P2 §7.3]


def test_malformed_entries_rejected(tmp_path) -> None:
    good = {"name": "x", "interface": "a.B", "module": "a", "class": "B", "platforms": ["sim"],
            "sources": ["P1 Eq. 1"], "evidence": "INFRA"}
    for bad in ({**good, "sources": []}, {**good, "sources": ["made up"]}, {**good, "platforms": ["cloud"]},
                {**good, "evidence": "GUESS"}, {k: v for k, v in good.items() if k != "module"}):
        f = tmp_path / "r.json"
        f.write_text(json.dumps({"components": [bad]}), encoding="utf-8")
        with pytest.raises(RegistryError):
            Registry.load(f)
    f = tmp_path / "dup.json"
    f.write_text(json.dumps({"components": [good, good]}), encoding="utf-8")
    with pytest.raises(RegistryError, match="duplicate"):
        Registry.load(f)


def _interface(path: str) -> type:
    module, _, name = path.rpartition(".")
    return getattr(importlib.import_module(module), name)


@pytest.mark.parametrize("name", REG.names())
def test_ct08_registered_classes_match_interfaces(name: str) -> None:
    spec = REG.spec(name)
    cls = REG.resolve(name, sorted(spec.platforms)[0])
    iface = _interface(spec.interface)
    if getattr(iface, "_is_protocol", False):
        required = {m for m in typing.get_protocol_members(iface)} if hasattr(typing, "get_protocol_members") else {
            m for m in vars(iface) if not m.startswith("_") and callable(getattr(iface, m))}
        missing = sorted(m for m in required if m != "drone_id" and not hasattr(cls, m))
        assert not missing, f"{name}: {cls.__name__} lacks {missing} required by {spec.interface}"
    else:
        assert cls is iface, f"{name}: interface {spec.interface} should be the class itself"
