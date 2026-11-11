"""Static architecture rules checked on the source tree (no imports executed).

- CT-01: no internet / socket client imports in the runtime package [BRIEF §5]
- CT-04: no print() in runtime code [ADIAT-inspired: ADIAT-standards §2.4]
- layering: runtime never imports sim/ or tests/; onboard, swarm, link, video never import gcs
  (docs/ARCHITECTURE.md §3)
- GT-14: the GCS display predictor (gcs.global_state) is never used by onboard control [P2 §14.3]
- every module carries a source tag in its docstring [TEAM-BRIEF §0.2]
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "nidar"
NETWORK_MODULES = {"socket", "ssl", "http", "urllib", "requests", "httpx", "aiohttp", "websocket", "websockets",
                   "ftplib", "smtplib", "paramiko", "grpc", "boto3"}
TAGS = ("[BRIEF", "[P1", "[P2", "[ADIAT-inspired", "[TEAM-BRIEF", "[DATASET")


def _py_files(base: Path) -> list[Path]:
    return sorted(p for p in base.rglob("*.py") if ".venv" not in p.parts)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def _rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def test_ct01_no_network_imports_in_runtime() -> None:
    bad = [(_rel(p), m) for p in _py_files(RUNTIME) for m in _imports(p) if m.split(".")[0] in NETWORK_MODULES]
    assert not bad, f"runtime must not use external-network clients [BRIEF §5]: {bad}"


def test_ct04_no_print_in_runtime() -> None:
    bad = []
    for p in _py_files(RUNTIME):
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                bad.append(f"{_rel(p)}:{node.lineno}")
    assert not bad, f"use nidar.common.logging, not print(): {bad}"


def test_runtime_never_imports_sim_or_tests() -> None:
    bad = [(_rel(p), m) for p in _py_files(RUNTIME) for m in _imports(p) if m.split(".")[0] in {"sim", "tests"}]
    assert not bad, f"runtime code must not import offline packages: {bad}"


@pytest.mark.parametrize("layer", ["onboard", "swarm", "link", "video", "common"])
def test_lower_layers_do_not_import_gcs(layer: str) -> None:
    bad = [(_rel(p), m) for p in _py_files(RUNTIME / layer) for m in _imports(p) if m.startswith("nidar.gcs")]
    assert not bad, f"{layer} must not depend on the GCS layer: {bad}"


def test_gt14_display_predictor_not_used_by_onboard() -> None:
    users = [_rel(p) for p in _py_files(ROOT / "nidar") for m in _imports(p)
             if m.startswith("nidar.gcs.global_state") and not _rel(p).startswith("nidar/gcs/")]
    assert not users, f"display-only predictor must not feed control [P2 §14.3]: {users}"


@pytest.mark.parametrize("path", _py_files(RUNTIME) + _py_files(ROOT / "sim") + _py_files(ROOT / "tools"),
                         ids=_rel)
def test_every_module_docstring_has_a_source_tag(path: Path) -> None:
    doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
    assert any(t in doc for t in TAGS), f"{_rel(path)}: module docstring needs a source tag {TAGS}"
