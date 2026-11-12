"""GeoJSON mission-file parser (team decision 2026-11-12 for OQ-22: accept GeoJSON polygons for now).

Accepted: a Polygon geometry, a Feature, or a FeatureCollection. In a collection the boundary is the feature
with ``properties.role == "boundary"`` (else the first polygon); a feature with ``role == "launch_zone"``
gives the 12 ft pad [BRIEF §3, §7]. Coordinates are WGS-84 longitude / latitude (the GeoJSON standard) and
are projected to local east-north metres about the boundary's mean vertex with an equirectangular
projection (error well below a metre over a 10 ha site). A top-level ``"units": "metres"`` marks files whose
coordinates are already local metres (test scenarios). Outer ring only; holes are ignored.
The organisers' real format is still unknown: other formats plug in as further parsers.
"""
from __future__ import annotations

import json
import math

import numpy as np

from nidar.common.contracts import SCHEMA_VERSION, GeoPolygon, MissionDefinition, ProcessResult, run_isolated
from nidar.common.contracts.mission import polygon_area_m2
from nidar.gcs.mission_loader import sha256_hex

EARTH_RADIUS_M = 6_371_008.8      # mean Earth radius (IUGG)


def _polygons(doc: dict) -> list[tuple[str | None, list]]:
    """(role, outer ring) of every polygon in the document."""
    kind = doc.get("type")
    if kind == "FeatureCollection":
        return [p for f in doc.get("features", []) for p in _polygons(f)]
    if kind == "Feature":
        role = (doc.get("properties") or {}).get("role")
        return [(role, ring) for _, ring in _polygons(doc.get("geometry") or {})]
    if kind == "Polygon":
        return [(None, doc["coordinates"][0])]
    return []


def _ring(ring: list) -> np.ndarray:
    pts = np.array([c[:2] for c in ring], dtype=float)
    if len(pts) > 1 and np.allclose(pts[0], pts[-1]):
        pts = pts[:-1]                                    # GeoJSON rings repeat the first vertex
    return pts


def _ccw(pts: np.ndarray) -> np.ndarray:
    return pts if polygon_area_m2(pts) > 0 else pts[::-1]


class GeoJsonMissionParser:
    """Implements ``MissionFileParser``."""

    name = "geojson"

    def can_parse(self, raw: bytes, filename: str) -> bool:
        if not filename.lower().endswith((".geojson", ".json")):
            return False
        try:
            return isinstance(json.loads(raw.decode("utf-8")), dict)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return False

    def _parse(self, raw: bytes) -> MissionDefinition:
        doc = json.loads(raw.decode("utf-8"))
        polys = _polygons(doc)
        if not polys:
            raise ValueError("no Polygon found")
        boundary = next((r for role, r in polys if role == "boundary"), None)
        if boundary is None:
            boundary = next(r for role, r in polys if role != "launch_zone")
        pad = next((r for role, r in polys if role == "launch_zone"), None)
        b = _ring(boundary)
        if doc.get("units") == "metres":
            datum = "local metres (file units)"

            def project(p: np.ndarray) -> np.ndarray:
                return p
        else:
            lon0, lat0 = b.mean(axis=0)
            datum = f"WGS-84, equirectangular about lon {lon0:.7f}, lat {lat0:.7f}"

            def project(p: np.ndarray) -> np.ndarray:
                x = np.radians(p[:, 0] - lon0) * EARTH_RADIUS_M * math.cos(math.radians(lat0))
                y = np.radians(p[:, 1] - lat0) * EARTH_RADIUS_M
                return np.column_stack([x, y])
        zone = None if pad is None else GeoPolygon(_ccw(project(_ring(pad))), datum)
        return MissionDefinition(SCHEMA_VERSION, sha256_hex(raw), GeoPolygon(_ccw(project(b)), datum), zone)

    def parse(self, raw: bytes, filename: str) -> ProcessResult[MissionDefinition]:
        return run_isolated("gcs.mission_loader.geojson", "parse", lambda: self._parse(raw), file=filename)
