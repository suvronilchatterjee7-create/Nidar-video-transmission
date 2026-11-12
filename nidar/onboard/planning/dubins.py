"""Curvature-bounded turns between sweep lines.

Minimum turn radius R_min = v^2 / (g tan(phi_max)) [P2 Eq. 174]; turns use arcs with R >= R_min
[P2 Eq. 175]. ``u_turn_length`` gives the length of the 180-degree turn joining two parallel sweep lines:
a semicircle when the spacing is at least 2 R_min, otherwise a three-arc "bulb" turn of radius R_min
(standard Dubins result). The explicit turn geometry (``turn``) waits for the onboard trajectory phase.
"""
from __future__ import annotations

import math

import numpy as np

from nidar.common.stub import stub
from nidar.common.units import G_MPS2

WAITS_FOR = "explicit go-ahead for the onboard trajectory phase"


def min_turn_radius(v_cruise: float, phi_max_rad: float) -> float:
    """[P2 Eq. 174]"""
    if not 0.0 < phi_max_rad < math.pi / 2:
        raise ValueError("phi_max must be in (0, pi/2)")
    return v_cruise**2 / (G_MPS2 * math.tan(phi_max_rad))


def u_turn_length(spacing_m: float, r_min: float) -> float:
    """Path length of the U-turn between sweep lines ``spacing_m`` apart with turn radius >= r_min."""
    if spacing_m >= 2.0 * r_min:
        return math.pi * spacing_m / 2.0
    return r_min * (3.0 * math.pi - 4.0 * math.asin((2.0 * r_min + spacing_m) / (4.0 * r_min)))


def turn(p0: np.ndarray, h0: float, p1: np.ndarray, h1: float, r_min: float) -> np.ndarray:
    """Turn geometry between two poses. [P2 Eq. 175]"""
    raise stub("nidar/onboard/planning/dubins.py:turn", "P2 Eq. 175", WAITS_FOR)
