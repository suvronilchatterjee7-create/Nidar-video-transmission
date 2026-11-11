"""Telemetry framing: state packets at about 20 Hz, map at 1 Hz, heartbeat, seq/ack repeat-until-acked
commands, SNR reports every GoP. [P2 §12.1] [P1 §C.2 A7] [BRIEF §8]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


def encode(message: object) -> bytes:
    """Encode. [P2 §12.1]"""
    raise stub(
        "nidar/link/framing.py:encode",
        "P2 §12.1",
        WAITS_FOR,
    )


def decode(raw: bytes) -> object:
    """Decode. [P2 §12.1]"""
    raise stub(
        "nidar/link/framing.py:decode",
        "P2 §12.1",
        WAITS_FOR,
    )
