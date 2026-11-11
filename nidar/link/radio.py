"""Radio abstraction (local RF only) plus an in-process loopback radio for simulation and tests.

``LoopbackRadio`` implements the ``Radio`` protocol with in-memory queues: what one end sends, the other
end receives, in order, with optional deterministic packet loss. It never opens a socket [BRIEF §5].
The real radio (band, bandwidth, SDR class) is OQ-03 / OQ-10; its driver will implement the same protocol.
[P1 §3.1]
"""
from __future__ import annotations

import time
from collections import deque

import numpy as np

from nidar.common.contracts import ProcessResult


class LoopbackRadio:
    """Two LoopbackRadio objects created by ``pair()`` talk to each other."""

    def __init__(self, loss_ratio: float = 0.0, seed: int = 0) -> None:
        if not 0.0 <= loss_ratio < 1.0:
            raise ValueError("loss_ratio must be in [0, 1)")
        self._inbox: deque[tuple[str, bytes]] = deque()
        self._symbols: deque[np.ndarray] = deque()
        self._peer: LoopbackRadio | None = None
        self._loss = loss_ratio
        self._rng = np.random.default_rng(seed)

    @staticmethod
    def pair(loss_ratio: float = 0.0, seed: int = 0) -> tuple["LoopbackRadio", "LoopbackRadio"]:
        a, b = LoopbackRadio(loss_ratio, seed), LoopbackRadio(loss_ratio, seed + 1)
        a._peer, b._peer = b, a
        return a, b

    def _deliver(self) -> bool:
        return self._peer is not None and self._rng.random() >= self._loss

    def send(self, channel: str, payload: bytes) -> ProcessResult[None]:
        t0 = time.monotonic()
        if self._peer is None:
            return ProcessResult.failure("[link.radio] send failed: radio not paired", t0)
        if self._deliver():
            self._peer._inbox.append((channel, bytes(payload)))
        return ProcessResult(None, ProcessResult.success(0, t0).timings)

    def send_symbols(self, iq: np.ndarray) -> ProcessResult[None]:
        t0 = time.monotonic()
        if self._peer is None:
            return ProcessResult.failure("[link.radio] send_symbols failed: radio not paired", t0)
        if self._deliver():
            self._peer._symbols.append(np.array(iq, dtype=complex, copy=True))
        return ProcessResult(None, ProcessResult.success(0, t0).timings)

    def receive(self, timeout_s: float) -> ProcessResult[tuple[str, bytes]]:
        t0 = time.monotonic()
        if not self._inbox:
            return ProcessResult.failure(f"[link.radio] receive: nothing within {timeout_s} s", t0)
        return ProcessResult.success(self._inbox.popleft(), t0)

    def receive_symbols(self, n: int, timeout_s: float) -> ProcessResult[np.ndarray]:
        t0 = time.monotonic()
        if not self._symbols:
            return ProcessResult.failure(f"[link.radio] receive_symbols: nothing within {timeout_s} s", t0)
        block = self._symbols.popleft()
        return ProcessResult.success(block[:n], t0)
