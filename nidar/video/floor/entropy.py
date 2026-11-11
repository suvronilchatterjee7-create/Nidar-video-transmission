"""Static-model arithmetic coder for the floor's quantiser indices.

The model for each chunk is fixed by the protected metadata only (lambda_j, step Delta_j): no adaptation and
no state from earlier GoPs, so the floor stays firewalled [P1 §5.1 E4]. Distribution family: Laplacian with
variance lambda, discretised to the quantiser bins (the paper's pilot used a Laplacian-model code length
[P1 Table 22]). Symbols |k| <= K are coded directly; larger ones use an escape plus an Exp-Golomb tail coded
as equiprobable bits. Coder: 32-bit integer arithmetic coding (Witten-Neal-Cleary renormalisation).
"""
from __future__ import annotations

import bisect
import math

import numpy as np

TOTAL_BITS = 16
_FULL = (1 << 32) - 1
_HALF = 1 << 31
_QUARTER = 1 << 30
K_MAX = 255


def _laplace_cdf(x: float, b: float) -> float:
    return 0.5 * math.exp(x / b) if x < 0 else 1.0 - 0.5 * math.exp(-x / b)


class SymbolModel:
    """Frequency table over k in [-K, K] plus ESCAPE (last symbol)."""

    def __init__(self, lam: float, step: float) -> None:
        b = math.sqrt(max(lam, 1e-300) / 2.0)
        self.K = int(min(K_MAX, max(2, math.ceil(6.0 * math.sqrt(lam) / step))))
        n_sym = 2 * self.K + 2
        budget = (1 << TOTAL_BITS) - n_sym
        probs = []
        for k in range(-self.K, self.K + 1):
            probs.append(_laplace_cdf((k + 0.5) * step, b) - _laplace_cdf((k - 0.5) * step, b))
        probs.append(max(0.0, 1.0 - sum(probs)))
        freqs = [int(p * budget) + 1 for p in probs]
        self.cum = [0]
        for f in freqs:
            self.cum.append(self.cum[-1] + f)
        self.total = self.cum[-1]

    def interval(self, sym: int) -> tuple[int, int]:
        return self.cum[sym], self.cum[sym + 1]

    def find(self, target: int) -> int:
        return bisect.bisect_right(self.cum, target) - 1


class _Encoder:
    def __init__(self) -> None:
        self.low, self.high, self.pending, self.bits = 0, _FULL, 0, []

    def _emit(self, bit: int) -> None:
        self.bits.append(bit)
        self.bits.extend([1 - bit] * self.pending)
        self.pending = 0

    def encode(self, lo: int, hi: int, total: int) -> None:
        rng = self.high - self.low + 1
        self.high = self.low + rng * hi // total - 1
        self.low = self.low + rng * lo // total
        while True:
            if self.high < _HALF:
                self._emit(0)
            elif self.low >= _HALF:
                self._emit(1)
                self.low -= _HALF
                self.high -= _HALF
            elif self.low >= _QUARTER and self.high < 3 * _QUARTER:
                self.pending += 1
                self.low -= _QUARTER
                self.high -= _QUARTER
            else:
                break
            self.low = 2 * self.low
            self.high = 2 * self.high + 1

    def finish(self) -> bytes:
        self.pending += 1
        self._emit(0 if self.low < _QUARTER else 1)
        bits = self.bits + [0] * (-len(self.bits) % 8)
        out = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for b in bits[i:i + 8]:
                byte = (byte << 1) | b
            out.append(byte)
        return bytes(out)


class _Decoder:
    def __init__(self, data: bytes) -> None:
        self.bits = [(byte >> (7 - i)) & 1 for byte in data for i in range(8)]
        self.pos = 0
        self.low, self.high, self.value = 0, _FULL, 0
        for _ in range(32):
            self.value = (self.value << 1) | self._next()

    def _next(self) -> int:
        b = self.bits[self.pos] if self.pos < len(self.bits) else 0
        self.pos += 1
        return b

    def target(self, total: int) -> int:
        rng = self.high - self.low + 1
        return ((self.value - self.low + 1) * total - 1) // rng

    def consume(self, lo: int, hi: int, total: int) -> None:
        rng = self.high - self.low + 1
        self.high = self.low + rng * hi // total - 1
        self.low = self.low + rng * lo // total
        while True:
            if self.high < _HALF:
                pass
            elif self.low >= _HALF:
                self.low -= _HALF
                self.high -= _HALF
                self.value -= _HALF
            elif self.low >= _QUARTER and self.high < 3 * _QUARTER:
                self.low -= _QUARTER
                self.high -= _QUARTER
                self.value -= _QUARTER
            else:
                break
            self.low = 2 * self.low
            self.high = 2 * self.high + 1
            self.value = (self.value << 1) | self._next()


def _models(lam: np.ndarray, steps: np.ndarray, chunk_ids: np.ndarray) -> dict[int, SymbolModel]:
    out: dict[int, SymbolModel] = {}
    for c in np.unique(chunk_ids):
        out[int(c)] = SymbolModel(float(lam[c]), float(steps[c]))
    return out


def encode(indices: np.ndarray, chunk_ids: np.ndarray, lam: np.ndarray, steps: np.ndarray) -> bytes:
    """Code ``indices`` (coded coefficients in order) with the chunk models given by per-chunk lam/steps."""
    models = _models(lam, steps, chunk_ids)
    enc = _Encoder()
    for k, c in zip(indices.tolist(), chunk_ids.tolist(), strict=True):
        m = models[c]
        if -m.K <= k <= m.K:
            enc.encode(*m.interval(k + m.K), m.total)
        else:
            enc.encode(*m.interval(2 * m.K + 1), m.total)
            enc.encode(0 if k > 0 else 1, 1 if k > 0 else 2, 2)        # sign
            mag = abs(k) - m.K - 1                                     # Exp-Golomb order 0 of mag
            v = mag + 1
            nb = v.bit_length()
            for _ in range(nb - 1):
                enc.encode(0, 1, 2)
            for i in range(nb - 1, -1, -1):
                bit = (v >> i) & 1
                enc.encode(bit, bit + 1, 2)
    return enc.finish()


def decode(data: bytes, chunk_ids: np.ndarray, lam: np.ndarray, steps: np.ndarray) -> np.ndarray:
    models = _models(lam, steps, chunk_ids)
    dec = _Decoder(data)
    out = np.empty(len(chunk_ids), dtype=np.int64)

    def bit() -> int:
        b = dec.target(2)
        dec.consume(b, b + 1, 2)
        return b

    for n, c in enumerate(chunk_ids.tolist()):
        m = models[c]
        s = m.find(dec.target(m.total))
        dec.consume(*m.interval(s), m.total)
        if s < 2 * m.K + 1:
            out[n] = s - m.K
            continue
        sign = bit()
        zeros = 0
        while bit() == 0:
            zeros += 1
        v = 1
        for _ in range(zeros):
            v = (v << 1) | bit()
        mag = v - 1 + m.K + 1
        out[n] = -mag if sign else mag
    return out


def model_code_length_bits(indices: np.ndarray, chunk_ids: np.ndarray, lam: np.ndarray, steps: np.ndarray) -> float:
    """Ideal -log2 p code length under the same model (to compare with the actual coder output)."""
    models = _models(lam, steps, chunk_ids)
    bits = 0.0
    for k, c in zip(indices.tolist(), chunk_ids.tolist(), strict=True):
        m = models[c]
        s = k + m.K if -m.K <= k <= m.K else 2 * m.K + 1
        lo, hi = m.interval(s)
        bits += -math.log2((hi - lo) / m.total)
    return bits
