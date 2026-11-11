"""CRC inside the floor payload: undetected errors become detected except w.p. 2^-r. [P1 Rem. 7]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


def append_crc(payload: bytes, r_bits: int) -> bytes:
    """Append crc. [P1 Rem. 7]"""
    raise stub(
        "nidar/video/floor/crc.py:append_crc",
        "P1 Rem. 7",
        WAITS_FOR,
    )


def check_crc(block: bytes, r_bits: int) -> tuple[bool, bytes]:
    """Check crc. [P1 Rem. 7]"""
    raise stub(
        "nidar/video/floor/crc.py:check_crc",
        "P1 Rem. 7",
        WAITS_FOR,
    )
