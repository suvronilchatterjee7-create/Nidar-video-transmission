"""Boustrophedon (lawn-mower) coverage of a cell.

Footprint W = 2 z_rel tan(FOV_h / 2) cos(slope) [P2 Eq. 114, 171]; sweep spacing dy <= W (1 - overlap),
overlap in [0, 0.15] intended [P2 Eq. 172-173]; sweep axis x [P2 Eq. 169].

Implementation: the cell is a set of raster points. Points are grouped into bands of height dy; inside a
band, gaps wider than the raster split it into runs, so a non-convex cell gives several runs per sweep line
(the connectivity changes that Paper 2's critical-point slicing detects [P2 Eq. 170]). Runs are visited band
by band in alternating direction. This covers every point but does not build Paper 2's explicit sub-cell
graph, so the path between runs is not optimised (docs/MISSION_SIM.md §2). Flat terrain unless a slope is
given.
"""
from __future__ import annotations

import math
import time

import numpy as np

from nidar.common.contracts import PartitionCell, ProcessResult
from nidar.swarm.dwvt import rasterise


def footprint_width(z_rel_m: float, fov_h_rad: float, slope_rad: float = 0.0) -> float:
    """[P2 Eq. 114 / 171]"""
    return 2.0 * z_rel_m * math.tan(fov_h_rad / 2.0) * math.cos(slope_rad)


def sweep_spacing(width_m: float, overlap: float) -> float:
    """dy = W (1 - overlap) [P2 Eq. 172]."""
    if not 0.0 <= overlap < 1.0:
        raise ValueError("overlap must be in [0, 1) [P2 Eq. 172]")
    return width_m * (1.0 - overlap)


def line_intervals(vertices: np.ndarray, y: float) -> list[tuple[float, float]]:
    """x-intervals where the horizontal line at ``y`` lies inside the polygon (even-odd rule)."""
    xs = []
    n = len(vertices)
    for k in range(n):
        (x1, y1), (x2, y2) = vertices[k], vertices[(k + 1) % n]
        if (y1 > y) != (y2 > y):
            xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
    xs.sort()
    return [(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2)]


def _clip_run(a: float, b: float, intervals: list[tuple[float, float]], inset: float) -> tuple[float, float] | None:
    """Clip [a, b] to the boundary interval that contains its midpoint (None if it lies outside)."""
    mid = 0.5 * (a + b)
    for lo, hi in intervals:
        if lo <= mid <= hi:
            a2, b2 = max(a, lo + inset), min(b, hi - inset)
            return (a2, b2) if a2 <= b2 else (mid, mid)
    return None


def plan_segments(points: np.ndarray, spacing_m: float, resolution_m: float,
                  start_xy: np.ndarray | None = None, boundary_xy: np.ndarray | None = None) -> np.ndarray:
    """Sweep segments, shape (S, 2, 2): segment s runs from [s, 0] to [s, 1]. Empty cell -> (0, 2, 2).
    With ``boundary_xy`` every sweep is clipped to where its line lies inside the boundary, so the planned
    path never leaves the geofence [BRIEF §7] [P2 §12.3.3]; corner points beyond a clipped end are left to
    the camera footprint or to the next re-sweep of uncovered cells."""
    if len(points) == 0:
        return np.zeros((0, 2, 2))
    y0 = points[:, 1].min() - resolution_m / 2.0
    band = np.floor((points[:, 1] - y0) / spacing_m).astype(int)
    n_bands = int(band.max()) + 1
    y_top = points[:, 1].max() + resolution_m / 2.0
    order = list(range(n_bands))
    if start_xy is not None and abs(start_xy[1] - y_top) < abs(start_xy[1] - y0):
        order.reverse()                                       # start from the nearer end
    segments = []
    left_to_right = True
    if start_xy is not None:
        left_to_right = abs(start_xy[0] - points[:, 0].min()) <= abs(start_xy[0] - points[:, 0].max())
    for b in order:
        in_band = band == b
        xs = np.sort(points[in_band, 0])
        if xs.size == 0:
            continue
        ys = points[in_band, 1]
        y = 0.5 * (ys.min() + ys.max())          # mid-line of the band's points: all within spacing / 2
        breaks = np.flatnonzero(np.diff(xs) > 1.5 * resolution_m)
        starts = np.concatenate([[0], breaks + 1])
        ends = np.concatenate([breaks, [xs.size - 1]])
        runs = [(xs[s] - resolution_m / 2.0, xs[e] + resolution_m / 2.0) for s, e in zip(starts, ends, strict=True)]
        if boundary_xy is not None:
            iv = line_intervals(np.asarray(boundary_xy, dtype=float), y)
            runs = [r for r in (_clip_run(a_, b_, iv, 1e-6) for a_, b_ in runs) if r is not None]
            if not runs:
                continue
        if not left_to_right:
            runs = [(b_, a_) for a_, b_ in reversed(runs)]
        segments += [[[a_, y], [b_, y]] for a_, b_ in runs]
        left_to_right = not left_to_right
    return np.array(segments, dtype=float)


def path_length(segments: np.ndarray, start_xy: np.ndarray | None = None) -> float:
    """Total length: sweeps plus straight transitions between consecutive segments."""
    if len(segments) == 0:
        return 0.0
    total = float(np.linalg.norm(segments[:, 1] - segments[:, 0], axis=1).sum())
    total += float(np.linalg.norm(segments[1:, 0] - segments[:-1, 1], axis=1).sum())
    if start_xy is not None:
        total += float(np.linalg.norm(segments[0, 0] - start_xy))
    return total


class BoustrophedonPlanner:
    """Implements ``CoveragePlanner`` (docs/INTERFACES.md §9)."""

    def plan(self, cell: PartitionCell, altitude_m: float, fov_h_rad: float, overlap: float) -> ProcessResult:
        """Waypoints (M, 3) covering the cell polygon at ``altitude_m`` [P2 Eq. 170-173]."""
        t0 = time.monotonic()
        try:
            spacing = sweep_spacing(footprint_width(altitude_m, fov_h_rad), overlap)
            res = spacing / 4.0
            segs = plan_segments(rasterise(cell.polygon, res), spacing, res, None, cell.polygon.vertices_xy)
        except ValueError as exc:
            return ProcessResult.failure(f"[onboard.planning] plan failed (drone={cell.drone_id}): {exc}", t0)
        wp = segs.reshape(-1, 2)
        return ProcessResult.success(np.column_stack([wp, np.full(len(wp), altitude_m)]), t0)
