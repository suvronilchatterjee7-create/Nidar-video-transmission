"""Hybrid mass/inertia reset and feedforward at payload drop (m: 4.8 -> 4.6 kg, dT = -1.962 N).
[P2 §1.3 Eq. 13-16, §8.4 Eq. 227-234, §9.5 Eq. 269-273]

Phase 2 stub: every callable raises ``NotYetImplemented``.
"""

from __future__ import annotations

import numpy as np

from nidar.common.stub import stub

WAITS_FOR = "explicit go-ahead for the mission/onboard phases"


def thrust_feedforward_delta(m_payload_kg: float) -> float:
    """Thrust feedforward delta. [P2 Eq. 155 / 231-232]"""
    raise stub(
        "nidar/onboard/payload/hybrid_reset.py:thrust_feedforward_delta",
        "P2 Eq. 155 / 231-232",
        WAITS_FOR,
    )


def torque_feedforward(m_payload_kg: float, dr_cg: np.ndarray) -> np.ndarray:
    """Torque feedforward. [P2 Eq. 272]"""
    raise stub(
        "nidar/onboard/payload/hybrid_reset.py:torque_feedforward",
        "P2 Eq. 272",
        WAITS_FOR,
    )
