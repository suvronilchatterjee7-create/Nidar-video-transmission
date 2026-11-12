"""GCS partition service: recompute drone weights and split the not-yet-searched area [P2 §7.1].

The GCS recalculates each drone's capacity weight from its mission state [P2 Eq. 161] and re-partitions the
remaining search area with the weighted Voronoi rule [P2 Eq. 159], generators at the drones' current
positions. The weight law is a named setting (OQ-05c'): "linear" [P2 Eq. 107] or "multiplicative"
[P2 Eq. 29-30].
"""
from __future__ import annotations

from typing import Mapping

import numpy as np

from nidar.common.contracts import DroneStatus
from nidar.swarm import dwvt


class PartitionService:
    def __init__(self, weight_law: str, params: Mapping[str, float]) -> None:
        if weight_law not in ("linear", "multiplicative"):
            raise ValueError(f"weight_law must be 'linear' or 'multiplicative' (OQ-05c'), got {weight_law!r}")
        self.weight_law = weight_law
        self.params = dict(params)
        self._w: dict[int, float] = {}
        self._applied: set[tuple[int, str]] = set()

    def weight(self, status: DroneStatus) -> float:
        d = status.state.drone_id
        e = status.battery_energy_j / status.battery_energy_max_j
        p = self.params
        if self.weight_law == "linear":
            self._w[d] = dwvt.weight_linear(e, status.search_active, p["alpha1"], p["alpha2"], p["w_min"])
        else:
            w = self._w.get(d, 1.0)
            for event, happened in (("drop", not status.payload_present), ("battery", e < p["low_battery_frac"])):
                if happened and (d, event) not in self._applied:      # each event degrades the weight once
                    w = dwvt.weight_multiplicative(w, p["eta"], p["w_min"])
                    self._applied.add((d, event))
            self._w[d] = w
        return self._w[d]

    def update(self, statuses: Mapping[int, DroneStatus], points: np.ndarray) -> tuple[list[int], np.ndarray]:
        """Partition ``points`` (M, 2) among the given drones; returns (drone ids, label per point)."""
        ids = sorted(statuses)
        if not ids or len(points) == 0:
            return ids, np.zeros(len(points), dtype=int)
        gen = np.array([statuses[d].state.p[:2] for d in ids])
        w = np.array([self.weight(statuses[d]) for d in ids])
        return ids, dwvt.assign(points, gen, w)
