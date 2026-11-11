"""Radio abstraction (local RF only) plus an in-process loopback radio for simulation and tests.
Hardware is OQ-03 / OQ-10. [BRIEF §5] [P1 §3.1]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.contracts import ProcessResult
from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


class LoopbackRadio:
    """In-process radio for sim/tests; implements ``Radio``."""

    def send(self, channel: str, payload: bytes) -> ProcessResult:
        """[BRIEF §5]"""
        raise stub(
            "nidar/link/radio.py:LoopbackRadio.send",
            "BRIEF §5",
            WAITS_FOR,
        )

    def send_symbols(self, iq: np.ndarray) -> ProcessResult:
        """[P1 §3.1 Eq. 2]"""
        raise stub(
            "nidar/link/radio.py:LoopbackRadio.send_symbols",
            "P1 §3.1 Eq. 2",
            WAITS_FOR,
        )

    def receive(self, timeout_s: float) -> ProcessResult:
        """[BRIEF §5]"""
        raise stub(
            "nidar/link/radio.py:LoopbackRadio.receive",
            "BRIEF §5",
            WAITS_FOR,
        )

    def receive_symbols(self, n: int, timeout_s: float) -> ProcessResult:
        """[P1 §3.1 Eq. 2]"""
        raise stub(
            "nidar/link/radio.py:LoopbackRadio.receive_symbols",
            "P1 §3.1 Eq. 2",
            WAITS_FOR,
        )
