"""CRC inside the floor payload: undetected decoding errors become detected ones except w.p. 2^-r, which is
absorbed into eps_F [P1 Rem. 7]. r = 16 (CRC-CCITT) or 32 (CRC-32), standard-library implementations; the
length r itself is open (docs/VIDEO_SUBSYSTEM.md §12).
"""
from __future__ import annotations

import binascii
import zlib


def _crc(payload: bytes, r_bits: int) -> bytes:
    if r_bits == 32:
        return zlib.crc32(payload).to_bytes(4, "big")
    if r_bits == 16:
        return binascii.crc_hqx(payload, 0xFFFF).to_bytes(2, "big")
    raise ValueError("r_bits must be 16 or 32")


def append_crc(payload: bytes, r_bits: int) -> bytes:
    return payload + _crc(payload, r_bits)


def check_crc(block: bytes, r_bits: int) -> tuple[bool, bytes]:
    n = r_bits // 8
    if len(block) < n:
        return False, b""
    payload, tag = block[:-n], block[-n:]
    return _crc(payload, r_bits) == tag, payload
