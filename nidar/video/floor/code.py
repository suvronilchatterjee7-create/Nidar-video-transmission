"""Floor channel code behind one interface. The real code family (long block code vs rateless) is OQ-23.

``IdealOutageFloorCode`` is an *abstraction*, not a code: the floor block is delivered iff the information
accumulated over its n_F channel uses reaches the payload, sum_j log2(1 + gamma_j) >= B, the outage event
that the finite-blocklength certificate bounds [P1 §6.4, Lemma 5, §6.6]. It ignores dispersion (< 2 % at the
target scale [P1 Table 7]). Rate per use comes from a certified design (b_F / n_F) or another explicit source.
"""
from __future__ import annotations

import math
from typing import Protocol

import numpy as np

from nidar.common.contracts import CertifiedFloorDesign


class FloorCode(Protocol):
    name: str

    def uses_for(self, payload_bits: int) -> int: ...

    def delivered(self, payload_bits: int, use_snr: np.ndarray) -> bool: ...


class IdealOutageFloorCode:
    name = "ideal-outage abstraction (real code: OQ-23)"

    def __init__(self, rate_bits_per_use: float) -> None:
        if rate_bits_per_use <= 0:
            raise ValueError("rate must be > 0")
        self.rate = rate_bits_per_use

    @staticmethod
    def from_design(design: CertifiedFloorDesign) -> "IdealOutageFloorCode":
        """Use a certified design's rate b_F / n_F [P1 Thm 1, Prop. 18]."""
        return IdealOutageFloorCode(design.b_f_bits / design.n_f)

    def uses_for(self, payload_bits: int) -> int:
        return math.ceil(payload_bits / self.rate)

    def delivered(self, payload_bits: int, use_snr: np.ndarray) -> bool:
        """Outage test on the realised per-use SNRs of the floor's channel uses."""
        return float(np.log2(1.0 + np.asarray(use_snr, dtype=float)).sum()) >= payload_bits
