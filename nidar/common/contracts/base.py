"""Normalised result shape and validation helpers for every contract.

Every service call returns ``ProcessResult[T]``; a failing item yields ``error_message`` and the
pipeline continues. [ADIAT-inspired: streaming/contracts.py StreamProcessResult,
StreamAnalyzeService.process_frame try/except] (docs/INTERFACES.md §1)
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Generic, Optional, TypeVar

import numpy as np

from nidar.common.logging import get_logger

T = TypeVar("T")
SCHEMA_VERSION = 1  # bump on any wire-format change; readers stay backward compatible [ADIAT-inspired]
DroneId = int        # 1..N   [P2 Eq. 7, Eq. 160]

_log = get_logger("common.contracts")


@dataclass(frozen=True)
class StageTimings:
    """Wall-clock bounds of one processing call. [ADIAT-inspired: StageTimings]"""

    t_start: float
    t_end: float
    skipped: bool = False

    @property
    def duration_s(self) -> float:
        return self.t_end - self.t_start


@dataclass(frozen=True)
class ProcessResult(Generic[T]):
    """Normalised output of every service call. [ADIAT-inspired: StreamProcessResult]"""

    payload: Optional[T]
    timings: StageTimings
    error_message: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error_message is None and self.payload is not None

    @staticmethod
    def success(payload: T, t_start: float, t_end: float | None = None) -> "ProcessResult[T]":
        return ProcessResult(payload, StageTimings(t_start, time.monotonic() if t_end is None else t_end))

    @staticmethod
    def failure(message: str, t_start: float, t_end: float | None = None) -> "ProcessResult[T]":
        return ProcessResult(None, StageTimings(t_start, time.monotonic() if t_end is None else t_end), message)


def run_isolated(component: str, operation: str, fn: Callable[[], T], **inputs: object) -> ProcessResult[T]:
    """Call ``fn`` and never raise: exceptions become ``error_message`` naming component,
    operation and inputs. A stub (``NotYetImplemented``) is reported the same way.
    [ADIAT-inspired: failure isolation; errors that name the file/algorithm/operation]
    """
    t0 = time.monotonic()
    try:
        return ProcessResult.success(fn(), t0)
    except Exception as exc:  # noqa: BLE001 - isolation boundary by design
        detail = ", ".join(f"{k}={v!r}" for k, v in inputs.items())
        msg = f"[{component}] {operation} failed ({detail}): {type(exc).__name__}: {exc}"
        _log.error(msg)
        return ProcessResult.failure(msg, t0)


# --- validation helpers used by contract __post_init__ ---------------------------------------
def as_array(name: str, value: object, shape: tuple[int, ...]) -> np.ndarray:
    """Return a read-only float array of exactly ``shape``; -1 in ``shape`` means any length."""
    arr = np.array(value, dtype=float)
    if arr.ndim != len(shape) or any(s != -1 and s != a for s, a in zip(shape, arr.shape, strict=False)):
        raise ValueError(f"{name}: expected shape {shape}, got {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name}: contains non-finite values")
    arr.setflags(write=False)
    return arr


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)
