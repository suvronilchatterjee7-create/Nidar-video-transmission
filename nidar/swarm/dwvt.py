"""Dynamic weighted Voronoi tessellation (DWVT) on a raster of the search area, Lloyd centroids, weights.

Cell of drone i: points q with |q - c_i| / w_i <= |q - c_j| / w_j [P2 §7.1 Eq. 159]. Density-weighted
centroid [P2 Eq. 165] with phi = 1 + lambda exp(-|q - p_surv|^2 / 2 sigma^2) [P2 Eq. 167]. Weight laws
(OQ-05c'): multiplicative w+ = eta w- [P2 Eq. 29-30] and linear w = max(w_min, a1 E/E_max + a2 chi_search)
[P2 Eq. 107, 161-163]. Boundary hysteresis [P2 Eq. 127] and speed damping v = v_max tanh(kappa d)
[P2 Eq. 129].

Implementation choices: the area is a raster of points (multiplicatively weighted cells have curved edges, so
exact polygons are not used); ``PartitionCell.polygon`` is the convex hull of a cell's points (display
approximation). Initial generators come from farthest-point seeding + Lloyd because all drones start on
the pad (docs/MISSION_SIM.md §2).
"""
from __future__ import annotations

import numpy as np

from nidar.common.contracts import SCHEMA_VERSION, DensityKernel, GeoPolygon, PartitionCell, PartitionUpdate


def point_in_polygon(points: np.ndarray, vertices: np.ndarray) -> np.ndarray:
    """Even-odd ray casting, vectorised over points (N, 2)."""
    x, y = points[:, 0], points[:, 1]
    inside = np.zeros(len(points), dtype=bool)
    xj, yj = vertices[-1]
    for xi, yi in vertices:
        cross = (yi > y) != (yj > y)
        with np.errstate(divide="ignore", invalid="ignore"):
            xint = (xj - xi) * (y - yi) / (yj - yi) + xi
        inside ^= cross & (x < xint)
        xj, yj = xi, yi
    return inside


def rasterise(boundary: GeoPolygon, resolution_m: float) -> np.ndarray:
    """Centres of the resolution-sized squares that lie inside the boundary, shape (M, 2)."""
    v = boundary.vertices_xy
    xs = np.arange(v[:, 0].min() + resolution_m / 2, v[:, 0].max(), resolution_m)
    ys = np.arange(v[:, 1].min() + resolution_m / 2, v[:, 1].max(), resolution_m)
    gx, gy = np.meshgrid(xs, ys)
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    return pts[point_in_polygon(pts, v)]


def assign(points: np.ndarray, generators: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Label of each point: argmin_i |q - c_i| / w_i [P2 Eq. 159]."""
    d = np.linalg.norm(points[:, None, :] - generators[None, :, :], axis=2)
    return np.argmin(d / np.asarray(weights, dtype=float)[None, :], axis=1)


def density(points: np.ndarray, kernels: tuple[DensityKernel, ...] = ()) -> np.ndarray:
    """phi(q) = 1 + sum_k lambda_k exp(-|q - p_k|^2 / (2 sigma_k^2)) [P2 Eq. 167]."""
    phi = np.ones(len(points))
    for k in kernels:
        phi += k.strength * np.exp(-((points - k.p_surv_xy) ** 2).sum(axis=1) / (2.0 * k.sigma_m**2))
    return phi


def centroids(points: np.ndarray, labels: np.ndarray, n: int, phi: np.ndarray | None = None) -> np.ndarray:
    """Density-weighted centroid of every cell [P2 Eq. 165]; NaN for an empty cell."""
    phi = np.ones(len(points)) if phi is None else phi
    out = np.full((n, 2), np.nan)
    for i in range(n):
        m = labels == i
        if m.any():
            out[i] = (points[m] * phi[m, None]).sum(axis=0) / phi[m].sum()
    return out


def farthest_point_seeds(points: np.ndarray, n: int, start_xy: np.ndarray) -> np.ndarray:
    """Deterministic seeding: the point nearest ``start_xy``, then repeatedly the point farthest from all."""
    idx = [int(np.argmin(((points - start_xy) ** 2).sum(axis=1)))]
    d = ((points - points[idx[0]]) ** 2).sum(axis=1)
    for _ in range(1, n):
        idx.append(int(np.argmax(d)))
        d = np.minimum(d, ((points - points[idx[-1]]) ** 2).sum(axis=1))
    return points[idx].copy()


def lloyd(points: np.ndarray, generators: np.ndarray, weights: np.ndarray, phi: np.ndarray | None = None,
          iterations: int = 50, tol_m: float = 0.05) -> tuple[np.ndarray, np.ndarray]:
    """Lloyd iteration: generators move to their cell centroids until they stop [P2 Eq. 165, 168]."""
    g = generators.astype(float).copy()
    labels = assign(points, g, weights)
    for _ in range(iterations):
        c = centroids(points, labels, len(g), phi)
        c = np.where(np.isnan(c), g, c)
        moved = float(np.abs(c - g).max())
        g = c
        labels = assign(points, g, weights)
        if moved < tol_m:
            break
    return g, labels


def weight_linear(energy_frac: float, search_active: bool, alpha1: float, alpha2: float, w_min: float) -> float:
    """w = max(w_min, alpha1 E/E_max + alpha2 chi_search), capped at 1 [P2 Eq. 107, 163]."""
    return float(min(1.0, max(w_min, alpha1 * energy_frac + alpha2 * (1.0 if search_active else 0.0))))


def weight_multiplicative(w_prev: float, eta: float, w_min: float) -> float:
    """w+ = eta w- (eta = 0.5 representative), kept above w_min [P2 Eq. 29-30]."""
    return float(max(w_min, eta * w_prev))


def boundary_speed(v_max: float, kappa: float, dist_to_boundary_m: float) -> float:
    """v_ref = v_max tanh(kappa d) [P2 Eq. 129]."""
    return float(v_max * np.tanh(kappa * dist_to_boundary_m))


def owner_with_hysteresis(pos_xy: np.ndarray, current_owner: int, points: np.ndarray, labels: np.ndarray,
                          eps_h_m: float) -> int:
    """Reassign a drone to the neighbouring cell only after it has penetrated it by more than eps_h
    (distance to its own cell's nearest point) [P2 Eq. 126-127]."""
    nearest = int(np.argmin(((points - pos_xy) ** 2).sum(axis=1)))
    here = int(labels[nearest])
    if here == current_owner:
        return current_owner
    own = points[labels == current_owner]
    if len(own) == 0:
        return here
    return here if float(np.sqrt(((own - pos_xy) ** 2).sum(axis=1).min())) > eps_h_m else current_owner


def convex_hull(points: np.ndarray) -> np.ndarray:
    """Monotone-chain convex hull, counter-clockwise, without the closing point."""
    pts = sorted(map(tuple, np.unique(points, axis=0)))
    if len(pts) < 3:
        return np.array(pts, dtype=float)

    def half(seq: list) -> list:
        out: list = []
        for p in seq:
            while len(out) >= 2 and ((out[-1][0] - out[-2][0]) * (p[1] - out[-2][1])
                                     - (out[-1][1] - out[-2][1]) * (p[0] - out[-2][0])) <= 0:
                out.pop()
            out.append(p)
        return out

    lower, upper = half(pts), half(pts[::-1])
    return np.array(lower[:-1] + upper[:-1], dtype=float)


class DwvtPartitioner:
    """Raster DWVT for the GCS. ``resolution_m`` has no default: it trades accuracy for compute."""

    def __init__(self, resolution_m: float) -> None:
        self.resolution_m = resolution_m
        self.points: np.ndarray | None = None
        self.labels: np.ndarray | None = None
        self.ids: list[int] = []

    def partition(self, boundary: GeoPolygon, positions: dict, weights: dict,
                  kernels: tuple[DensityKernel, ...] = (), t: float = 0.0) -> PartitionUpdate:
        """[P2 Eq. 159]. ``positions``: drone_id -> (x, y); ``weights``: drone_id -> w in (0, 1]."""
        self.ids = sorted(positions)
        self.points = rasterise(boundary, self.resolution_m)
        gen = np.array([positions[i] for i in self.ids], dtype=float)
        self.labels = assign(self.points, gen, np.array([weights[i] for i in self.ids]))
        cells = []
        for k, drone_id in enumerate(self.ids):
            hull = convex_hull(self.points[self.labels == k])
            if len(hull) >= 3:
                cells.append(PartitionCell(drone_id, GeoPolygon(hull, boundary.datum), float(weights[drone_id]), False))
        return PartitionUpdate(SCHEMA_VERSION, t, tuple(cells), tuple(kernels))

    def centroids(self, update: PartitionUpdate) -> dict:
        """Density-weighted centroid per drone of the last partition [P2 Eq. 165]."""
        if self.points is None:
            raise ValueError("call partition() first")
        c = centroids(self.points, self.labels, len(self.ids), density(self.points, update.density_kernels))
        return {drone_id: c[k] for k, drone_id in enumerate(self.ids) if not np.isnan(c[k]).any()}
