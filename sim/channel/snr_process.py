"""Large-scale AR(1) SNR process with delayed noisy reports. [P1 §C.2 A7]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.stub import stub

WAITS_FOR = "Phase 3 approval (Paper 1 reference implementation)"


def simulate(
    gops: int, mean_db: float, rho: float, sigma_s: float, sigma_m: float, delay: int, seed: int
) -> tuple[np.ndarray, np.ndarray]:
    """Simulate. [P1 A7]"""
    raise stub(
        "sim/channel/snr_process.py:simulate",
        "P1 A7",
        WAITS_FOR,
    )
