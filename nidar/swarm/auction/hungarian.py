"""Min-cost assignment of confirmed survivors to drones by the Hungarian (Munkres) algorithm, at the GCS.

Paper 2's problem: every survivor gets exactly one drone, every drone at most one task [P2 §7.3 Eq. 183],
O(N^3) [P2 Eq. 125]. That problem is infeasible when survivors outnumber kit-holding drones (OQ-01), so this
solver returns the minimum-cost assignment of as many survivors as possible and lists the rest as
unassigned instead of failing (team decision 2026-11-12: kits per drone is a scenario setting; survivors
without a kit are reported). Infinite cost = drone has no payload [P2 Eq. 181].
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass

import numpy as np

from nidar.common.contracts import ProcessResult


@dataclass(frozen=True)
class AuctionResult:
    assignments: tuple[tuple[int, str, float], ...]   # (drone_id, survivor_id, cost)
    unassigned_survivors: tuple[str, ...]
    feasible: bool                                     # True iff every survivor was assigned [P2 Eq. 183]


def solve_square(cost: np.ndarray) -> list[int]:
    """Hungarian algorithm with potentials on a finite square matrix; returns column of each row."""
    n = cost.shape[0]
    u, v = [0.0] * (n + 1), [0.0] * (n + 1)
    p, way = [0] * (n + 1), [0] * (n + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [math.inf] * (n + 1)
        used = [False] * (n + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], math.inf, 0
            for j in range(1, n + 1):
                if not used[j]:
                    cur = cost[i0 - 1, j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    cols = [0] * n
    for j in range(1, n + 1):
        cols[p[j] - 1] = j - 1
    return cols


class HungarianAuction:
    def assign(self, costs: np.ndarray, drone_ids: list, survivor_ids: list) -> ProcessResult:
        """``costs[i, j]`` = cost of drone i serving survivor j (inf = not allowed) [P2 Eq. 183]."""
        t0 = time.monotonic()
        c = np.asarray(costs, dtype=float).reshape(len(drone_ids), len(survivor_ids))
        if np.isnan(c).any():
            return ProcessResult.failure("[swarm.auction] assign failed: NaN in cost matrix", t0)
        n = max(c.shape)
        if n == 0 or c.shape[1] == 0:
            return ProcessResult.success(AuctionResult((), tuple(survivor_ids), not survivor_ids), t0)
        finite = c[np.isfinite(c)]
        big = (float(np.abs(finite).sum()) + 1.0) * 1e3      # dominates any sum of real costs
        square = np.full((n, n), big)                         # dummy rows/cols: "leave unassigned"
        square[: c.shape[0], : c.shape[1]] = np.where(np.isfinite(c), c, big * n)   # forbidden pair: worse still
        cols = solve_square(square)
        out, taken = [], set()
        for i, j in enumerate(cols):
            if i < c.shape[0] and j < c.shape[1] and np.isfinite(c[i, j]):
                out.append((drone_ids[i], survivor_ids[j], float(c[i, j])))
                taken.add(j)
        left = tuple(s for j, s in enumerate(survivor_ids) if j not in taken)
        return ProcessResult.success(AuctionResult(tuple(out), left, not left), t0)
