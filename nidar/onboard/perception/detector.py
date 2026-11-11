"""Person detector adapter. Model: YOLOv8-pose weights from the team repo [DATASET: yolov8n-pose.pt]
(licence OQ-08a). Output is the normalised ``Detection`` contract in source-frame pixels.
[P2 §4.3] [ADIAT-inspired: adapters.py, ONNX provider fallback]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.contracts import ProcessResult
from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


class YoloPoseDetector:
    """Implements ``PersonDetector``; runtime (ONNX/TensorRT) is swappable."""

    def detect(self, frame: np.ndarray, t: float) -> ProcessResult:
        """[P2 §4.3 (CNN detection, e.g. YOLOv8)]"""
        raise stub(
            "nidar/onboard/perception/detector.py:YoloPoseDetector.detect",
            "P2 §4.3 (CNN detection, e.g. YOLOv8)",
            WAITS_FOR,
        )
