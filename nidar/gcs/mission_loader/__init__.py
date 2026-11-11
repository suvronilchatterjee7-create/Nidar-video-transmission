"""Mission-file loading through a parser registry.

The organiser file format is unknown (OQ-22), so no parser is registered yet and loading an unknown
format fails with a message that names the file. [BRIEF §3] [ADIAT-inspired: config-driven registry,
errors that name the file]
"""
from __future__ import annotations

import hashlib
import time

from nidar.common.contracts import MissionDefinition, MissionFileParser, ProcessResult

_PARSERS: dict[str, MissionFileParser] = {}


def register_parser(parser: MissionFileParser) -> None:
    if parser.name in _PARSERS:
        raise ValueError(f"mission parser {parser.name!r} already registered")
    _PARSERS[parser.name] = parser


def registered_parsers() -> list[str]:
    return sorted(_PARSERS)


def sha256_hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load(raw: bytes, filename: str) -> ProcessResult[MissionDefinition]:
    """Pick the first registered parser that accepts the file; never raises."""
    t0 = time.monotonic()
    candidates = [p for p in _PARSERS.values() if p.can_parse(raw, filename)]
    if not candidates:
        return ProcessResult.failure(
            f"[gcs.mission_loader] load failed (file={filename!r}): no registered parser accepts this file; "
            f"registered={registered_parsers()} (format is OQ-22)", t0)
    return candidates[0].parse(raw, filename)
