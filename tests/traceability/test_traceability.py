"""Traceability gate: fails if any requirement in docs/TRACEABILITY.md lacks a resolvable module or a
known test, or if any implemented test ID points at a missing test. [TEAM-BRIEF §8 Phase 2, §6.1 D10]
"""
from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path

import pytest

import nidar.common.contracts as contracts

ROOT = Path(__file__).resolve().parents[2]
TRACE = ROOT / "docs" / "TRACEABILITY.md"
INDEX = json.loads((ROOT / "tests" / "test_index.json").read_text(encoding="utf-8"))["tests"]
REQ_ROW = re.compile(r"^\| (R-(?:B|P1|P2|M)[\w-]*) \|")
TEST_ID = re.compile(r"\b(VT|PT|MS|CT|GT|HW)-(\d{2})\b")
RANGE = re.compile(r"\b(VT|PT|MS|CT|GT|HW)-(\d{2})\s*…\s*(?:\1-)?(\d{2})\b")

pytestmark = pytest.mark.traceability


def _rows() -> list[list[str]]:
    rows = []
    for line in TRACE.read_text(encoding="utf-8").splitlines():
        if REQ_ROW.match(line):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows


def _resolve_path(token: str) -> bool:
    tok = token.rstrip("*").rstrip("/")
    base = ROOT if tok.split("/")[0] in {"sim", "tools", "tests", "docs"} else ROOT / "nidar"
    p = base / tok
    return p.with_suffix(".py").exists() or p.is_dir() or p.exists()


def _resolve_symbol(token: str) -> bool:
    head, _, attr = token.partition(".")
    obj = getattr(contracts, head, None)
    if obj is None:
        return False
    if not attr:
        return True
    if dataclasses.is_dataclass(obj):
        return attr in {f.name for f in dataclasses.fields(obj)}
    return hasattr(obj, attr)


def _test_ids(cell: str) -> set[str]:
    ids = {f"{a}-{b}" for a, b in TEST_ID.findall(cell)}
    for prefix, lo, hi in RANGE.findall(cell):
        ids |= {f"{prefix}-{i:02d}" for i in range(int(lo), int(hi) + 1)}
    return ids


def test_rows_found() -> None:
    rows = _rows()
    assert len(rows) >= 60, f"expected the full requirement table, parsed only {len(rows)} rows"
    ids = [r[0] for r in rows]
    assert len(ids) == len(set(ids)), "duplicate requirement IDs"


@pytest.mark.parametrize("row", _rows(), ids=lambda r: r[0])
def test_requirement_has_module_and_test(row: list[str]) -> None:
    req = row[0]
    module_cell, test_cell = row[3], row[4]   # same column positions in requirement and R-M tables
    tests = _test_ids(test_cell)
    assert tests, f"{req}: no test ID in '{test_cell}'"
    unknown = sorted(t for t in tests if t not in INDEX)
    assert not unknown, f"{req}: test IDs not in tests/test_index.json: {unknown}"

    tokens = re.findall(r"`([^`]+)`", module_cell)
    if not tokens:
        assert module_cell.startswith("—") and any(t.startswith("HW-") for t in tests), (
            f"{req}: module column '{module_cell}' names no module; only hardware/procedure rows may do that")
        return
    for tok in tokens:
        ok = _resolve_path(tok) if "/" in tok else _resolve_symbol(tok)
        assert ok, f"{req}: module reference `{tok}` does not resolve to a file, package or contract symbol"


def test_every_requirement_has_an_evidence_level() -> None:
    levels = ("PROVED", "REPRODUCED", "SIMULATED", "TARGET", "REQUIRED", "OPEN", "—")
    for row in _rows():
        if row[0].startswith("R-M"):
            continue
        assert row[-1].startswith(levels), f"{row[0]}: evidence '{row[-1]}' must start with one of {levels}"


@pytest.mark.parametrize("test_id", sorted(t for t, v in INDEX.items() if v["status"] == "implemented"))
def test_implemented_ids_point_to_real_tests(test_id: str) -> None:
    node = INDEX[test_id]["node"]
    path, _, func = node.partition("::")
    file = ROOT / path
    assert file.exists(), f"{test_id}: {path} missing"
    assert re.search(rf"^def {re.escape(func)}\(", file.read_text(encoding="utf-8"), re.M), (
        f"{test_id}: function {func} not found in {path}")


def test_index_entries_are_well_formed() -> None:
    for tid, v in INDEX.items():
        assert TEST_ID.fullmatch(tid), tid
        assert v["status"] in {"implemented", "planned"}, tid
        assert ("node" in v) == (v["status"] == "implemented"), tid
