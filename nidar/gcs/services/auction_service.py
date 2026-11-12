"""GCS survivor auction: build the cost matrix for the waiting survivors and assign them [P2 §5.3 / §7.3].

The cost form is a named setting (OQ-05c): "eq179" [P2 Eq. 179] or "eq38" [P2 Eq. 38]. Survivors that
cannot be assigned now (more survivors than free kit-holding drones, OQ-01) stay in the queue and are
reported; they are not dropped.
"""
from __future__ import annotations

from typing import Mapping

import numpy as np

from nidar.common.contracts import SCHEMA_VERSION, AuctionAssignment, DroneStatus, SurvivorTrack
from nidar.swarm.auction import cost as cost_forms
from nidar.swarm.auction.hungarian import HungarianAuction


class AuctionService:
    def __init__(self, cost_form: str, weights: Mapping[str, float], v_cruise: float) -> None:
        if cost_form not in ("eq179", "eq38"):
            raise ValueError(f"cost_form must be 'eq179' or 'eq38' (OQ-05c), got {cost_form!r}")
        self.cost_form, self.weights, self.v_cruise = cost_form, dict(weights), v_cruise
        self._solver = HungarianAuction()

    def run(self, waiting: list[SurvivorTrack], eligible: Mapping[int, DroneStatus],
            abandoned_area_frac: Mapping[int, float], t: float) -> tuple[list[AuctionAssignment], list[str]]:
        """Returns (assignments, ids of survivors still waiting)."""
        if not waiting or not eligible:
            return [], [s.survivor_id for s in waiting]
        ids = sorted(eligible)
        terms = {}
        costs = np.empty((len(ids), len(waiting)))
        for i, d in enumerate(ids):
            for j, s in enumerate(waiting):
                if self.cost_form == "eq179":
                    tm = cost_forms.cost_eq179(eligible[d], s.p_surv, self.v_cruise, self.weights,
                                               abandoned_area_frac.get(d, 0.0))
                else:
                    tm = cost_forms.cost_eq38(eligible[d], s.p_surv, self.v_cruise, self.weights)
                terms[(d, s.survivor_id)] = tm
                costs[i, j] = cost_forms.total(tm)
        res = self._solver.assign(costs, ids, [s.survivor_id for s in waiting])
        if not res.ok:
            return [], [s.survivor_id for s in waiting]
        out = [AuctionAssignment(SCHEMA_VERSION, t, d, sid, c, terms[(d, sid)], "hungarian")
               for d, sid, c in res.payload.assignments]
        return out, list(res.payload.unassigned_survivors)

    def on_confirmed(self, track: SurvivorTrack, statuses: Mapping[int, DroneStatus]) -> list:
        """Single-survivor convenience wrapper [P2 Eq. 176-187]."""
        return self.run([track], statuses, {}, track.t_confirmed or 0.0)[0]
