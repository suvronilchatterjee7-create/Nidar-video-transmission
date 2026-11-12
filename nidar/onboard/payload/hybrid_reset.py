"""Hybrid mass / inertia reset and feedforward at payload drop.

m+ = m- - m_payload, I+ = I- - I_payload [P2 Eq. 13-16, 153-154]; hover thrust feedforward changes by
-m_payload g = -1.962 N for the 0.2 kg kit [P2 Eq. 155, 231-232]; acceleration step at constant thrust
m_payload g / m+ = 0.427 m/s^2 for 4.8 -> 4.6 kg [P2 Eq. 230]; torque feedforward for a centre-of-gravity
shift tau_ff = m_payload (dr_cg x g) [P2 Eq. 272].
"""
from __future__ import annotations

import numpy as np

from nidar.common.units import G_MPS2

GRAVITY_VECTOR = np.array([0.0, 0.0, -G_MPS2])      # [P2 Eq. 10]


def mass_after_drop(m_before_kg: float, m_payload_kg: float) -> float:
    """[P2 Eq. 153]"""
    if not 0.0 < m_payload_kg < m_before_kg:
        raise ValueError("payload mass must be positive and below the vehicle mass")
    return m_before_kg - m_payload_kg


def inertia_after_drop(inertia_before: np.ndarray, inertia_payload: np.ndarray) -> np.ndarray:
    """[P2 Eq. 154]"""
    return np.asarray(inertia_before, dtype=float) - np.asarray(inertia_payload, dtype=float)


def thrust_feedforward_delta(m_payload_kg: float) -> float:
    """Change of the hover thrust feedforward, in newtons (negative) [P2 Eq. 155 / 231-232]."""
    return -m_payload_kg * G_MPS2


def acceleration_step(m_before_kg: float, m_payload_kg: float) -> float:
    """Upward acceleration if thrust is not adjusted: m_payload g / m+ [P2 Eq. 230]."""
    return m_payload_kg * G_MPS2 / mass_after_drop(m_before_kg, m_payload_kg)


def torque_feedforward(m_payload_kg: float, dr_cg: np.ndarray) -> np.ndarray:
    """tau_ff = m_payload (dr_cg x g) [P2 Eq. 272] (sign convention to be fixed with the body-frame model)."""
    return m_payload_kg * np.cross(np.asarray(dr_cg, dtype=float), GRAVITY_VECTOR)
