"""RGB-to-3D geotagging by ray casting into the TSDF, with first-order covariance.
[P2 §4.3 Eq. 88-100]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.contracts import Detection, DroneState, ProcessResult
from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


class RayCastGeotagger:
    """Implements ``Geotagger``."""

    def geotag(self, det: Detection, pose: DroneState, P: np.ndarray, terrain: object) -> ProcessResult:
        """[P2 Eq. 89-100]"""
        raise stub(
            "nidar/onboard/perception/geotag.py:RayCastGeotagger.geotag",
            "P2 Eq. 89-100",
            WAITS_FOR,
        )
