"""Mission file contracts. Source file format is unknown (OQ-22); only the parsed form is fixed.

docs/INTERFACES.md §2. [BRIEF §3, §7] [P2 §12.3.3]
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

import numpy as np

from nidar.common.contracts.base import ProcessResult, as_array, require
from nidar.common.units import MISSION_AREA_MAX_M2


def polygon_area_m2(vertices_xy: np.ndarray) -> float:
    """Signed shoelace area; positive for counter-clockwise vertex order."""
    x, y = vertices_xy[:, 0], vertices_xy[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


@dataclass(frozen=True)
class GeoPolygon:
    """Closed polygon in the local inertial frame F_I, metres, counter-clockwise.
    [P2 §1.4 Eq. 21; §8.3 Eq. 224]

    ``datum`` names the geodetic origin / CRS of the source file (OQ-22): no default.
    """

    vertices_xy: np.ndarray
    datum: str

    def __post_init__(self) -> None:
        v = as_array("GeoPolygon.vertices_xy", self.vertices_xy, (-1, 2))
        require(v.shape[0] >= 3, "GeoPolygon needs at least 3 vertices")
        require(polygon_area_m2(v) > 0, "GeoPolygon vertices must be counter-clockwise with non-zero area")
        object.__setattr__(self, "vertices_xy", v)

    @property
    def area_m2(self) -> float:
        return polygon_area_m2(self.vertices_xy)


@dataclass(frozen=True)
class MissionDefinition:
    """Parsed organiser mission/boundary file. [BRIEF §3]"""

    schema_version: int
    source_file_sha256: str
    boundary: GeoPolygon                 # geofence B   [BRIEF §7] [P2 §12.3.3]
    launch_zone: Optional[GeoPolygon]    # 12 ft pad Z if the file provides it (OQ-22)  [BRIEF §7]

    def __post_init__(self) -> None:
        require(len(self.source_file_sha256) == 64, "source_file_sha256 must be a hex SHA-256 digest")
        require(self.boundary.area_m2 <= MISSION_AREA_MAX_M2 * (1 + 1e-9),
                f"boundary area {self.boundary.area_m2:.0f} m^2 exceeds 10 ha [BRIEF §1]")

    @property
    def area_m2(self) -> float:
        return self.boundary.area_m2


class MissionFileParser(Protocol):
    """Parser registered by name in the registry (format OQ-22). [ADIAT-inspired: algorithms.conf]"""

    name: str

    def can_parse(self, raw: bytes, filename: str) -> bool: ...

    def parse(self, raw: bytes, filename: str) -> ProcessResult[MissionDefinition]: ...
