"""Table-driven mode automaton.

Paper 2 gives two incompatible mode sets (OQ-05a), so modes, guards and reset maps are data in
``mode_tables/*.json``. Both variants ship as *candidates*; ``ACTIVE_TABLE`` is None until you choose,
and building an automaton without naming a table is an error. Guard evaluation is a stub.
[P2 §9.1 Eq. 243-249] [P2 §13.1] [ADIAT-inspired: config-driven registry]
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from nidar.common.contracts import DroneStatus, GcsCommand, LinkStatus
from nidar.common.stub import stub

TABLE_DIR = Path(__file__).with_name("mode_tables")
ACTIVE_TABLE: str | None = None   # decision OQ-05a: deliberately unset


@dataclass(frozen=True)
class Transition:
    source_mode: str
    target_mode: str
    guard: str
    source: str
    open_questions: tuple[str, ...]


@dataclass(frozen=True)
class ModeTable:
    name: str
    status: str
    source: str
    modes: tuple[str, ...]
    initial: str
    transitions: tuple[Transition, ...]


def available_tables() -> list[str]:
    return sorted(p.stem for p in TABLE_DIR.glob("*.json"))


def load_mode_table(name: str) -> ModeTable:
    path = TABLE_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"mode table {name!r} not found; available: {available_tables()}")
    data = json.loads(path.read_text(encoding="utf-8"))
    modes = tuple(data["modes"])
    transitions = tuple(
        Transition(t["from"], t["to"], t["guard"], t["source"], tuple(t.get("open", []))) for t in data["transitions"]
    )
    for t in transitions:
        if t.source_mode != "*" and t.source_mode not in modes:
            raise ValueError(f"{name}: transition from unknown mode {t.source_mode!r}")
        if t.target_mode not in modes:
            raise ValueError(f"{name}: transition to unknown mode {t.target_mode!r}")
    if data["initial"] not in modes:
        raise ValueError(f"{name}: initial mode {data['initial']!r} not in modes")
    return ModeTable(data["name"], data["status"], data["source"], modes, data["initial"], transitions)


class TableDrivenAutomaton:
    """Implements ``ModeAutomaton`` (docs/INTERFACES.md §9)."""

    def __init__(self, table_name: str) -> None:
        self.table = load_mode_table(table_name)
        self.mode = self.table.initial

    def evaluate(self, status: DroneStatus, link: LinkStatus, command: GcsCommand | None) -> str:
        """[P2 §9.1 guards/reset maps; thresholds per OQ-05a/b/d/g]"""
        raise stub("nidar/onboard/automaton/automaton.py:TableDrivenAutomaton.evaluate",
                   "P2 §9.1, §13.1 guards", "decision OQ-05a and the onboard phase")
