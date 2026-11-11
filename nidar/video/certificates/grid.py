"""Certified grid of floor designs; the controller may only pick members. [P1 Prop. 18, Thm 4]

Rounding rule: the nearest certified design *not below* the requested floor power that fits the
available channel uses [P1 Prop. 18]. The grid is a versioned JSON artefact built offline.
[ADIAT-inspired: versioned result files]
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from nidar.common.contracts import CertifiedFloorDesign

GRID_SCHEMA_VERSION = 1


class CertifiedGrid:
    def __init__(self, designs: list[CertifiedFloorDesign] | None = None) -> None:
        self.designs: list[CertifiedFloorDesign] = sorted(designs or [], key=lambda d: d.gamma_f_db)

    def load(self, path: str) -> None:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("schema_version", 0) > GRID_SCHEMA_VERSION:
            raise ValueError(f"{path}: grid schema {data['schema_version']} is newer than {GRID_SCHEMA_VERSION}")
        self.designs = sorted((CertifiedFloorDesign(**d) for d in data["designs"]), key=lambda d: d.gamma_f_db)

    def save(self, path: str) -> None:
        payload = {"schema_version": GRID_SCHEMA_VERSION, "designs": [dataclasses.asdict(d) for d in self.designs]}
        Path(path).write_text(json.dumps(payload, indent=1), encoding="utf-8")

    def nearest_not_below(self, gamma_f_db: float, n_available: int) -> CertifiedFloorDesign | None:
        """Smallest-power certified design with gamma_F >= request and n_F <= n_available; None if none."""
        for d in self.designs:
            if d.gamma_f_db >= gamma_f_db and d.n_f <= n_available:
                return d
        return None
