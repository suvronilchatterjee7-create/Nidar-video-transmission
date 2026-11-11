"""Versioned, append-only mission log (JSON Lines).

Records states, detections, tags, assignments, deliveries and video statistics for replay in
``sim/``. Readers accept older schema versions through registered migrations and refuse newer ones.
[ADIAT-inspired: versioned, backward-compatible result files] [USER-PROMPT §6.1 D10]
"""
from __future__ import annotations

import dataclasses
import json
import math
from pathlib import Path
from typing import Any, Callable, Iterator

import numpy as np

from nidar.common.contracts.base import SCHEMA_VERSION

# MIGRATIONS[k] upgrades a record written with schema k to schema k+1.
MIGRATIONS: dict[int, Callable[[dict], dict]] = {}


class MissionLogError(ValueError):
    pass


def to_jsonable(obj: Any) -> Any:
    """Convert contracts (frozen dataclasses with numpy arrays) into JSON-safe structures."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {"__type__": type(obj).__name__,
                **{f.name: to_jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}}
    if isinstance(obj, np.ndarray):
        if np.iscomplexobj(obj):
            return {"__ndarray__": "complex", "re": obj.real.tolist(), "im": obj.imag.tolist()}
        return {"__ndarray__": str(obj.dtype), "data": obj.tolist()}
    if isinstance(obj, (np.floating, np.integer, np.bool_)):
        return obj.item()
    if isinstance(obj, float) and not math.isfinite(obj):
        return {"__float__": repr(obj)}
    if isinstance(obj, (frozenset, set)):
        return sorted(to_jsonable(x) for x in obj)
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, bytes):
        return {"__bytes__": obj.hex()}
    return obj


class MissionLogWriter:
    def __init__(self, path: Path | str, mission_id: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("x", encoding="utf-8") as fh:   # never overwrite an existing log
            fh.write(json.dumps({"type": "header", "schema_version": SCHEMA_VERSION, "mission_id": mission_id}) + "\n")

    def append(self, kind: str, t: float, obj: Any) -> None:
        rec = {"type": "record", "kind": kind, "t": t, "body": to_jsonable(obj)}
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")


class MissionLogReader:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        with self.path.open(encoding="utf-8") as fh:
            header = json.loads(fh.readline())
        if header.get("type") != "header":
            raise MissionLogError(f"{self.path}: first line is not a header")
        self.schema_version = int(header["schema_version"])
        self.mission_id = header.get("mission_id")
        if self.schema_version > SCHEMA_VERSION:
            raise MissionLogError(f"{self.path}: schema {self.schema_version} is newer than reader {SCHEMA_VERSION}")
        missing = [k for k in range(self.schema_version, SCHEMA_VERSION) if k not in MIGRATIONS]
        if missing:
            raise MissionLogError(f"{self.path}: no migration registered from schema(s) {missing}")

    def records(self) -> Iterator[dict]:
        with self.path.open(encoding="utf-8") as fh:
            next(fh)
            for line in fh:
                rec = json.loads(line)
                for k in range(self.schema_version, SCHEMA_VERSION):
                    rec = MIGRATIONS[k](rec)
                yield rec
