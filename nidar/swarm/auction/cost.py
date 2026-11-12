"""Assignment cost terms. Paper 2 gives two forms (OQ-05c); both are implemented and the scenario names one.

Eq. 38  [P2 §2.4]: C = alpha |p_i - p_surv| / v_cruise + beta (1 / E_i) + gamma (1 - chi_payload).
Eq. 179 [P2 §7.3]: C = |p_i - p_surv| / v_cruise + alpha1 (1 - E_i / E_max) + alpha2 (1 - chi_payload)
                       + alpha3 Area(V_i \\ V_i_new) / Area(W).
No payload -> infinite cost [P2 Eq. 40, 181]. E_i is used as the fraction E_i / E_max in both forms so the
terms are unit-free (Eq. 38 writes 1 / E_i without units). The paper gives no weight values: they are
scenario settings.
"""
from __future__ import annotations

import math

import numpy as np

from nidar.common.contracts import AssignmentCostTerms, DroneStatus


def _time_to_intercept(status: DroneStatus, p_surv: np.ndarray, v_cruise: float) -> float:
    return float(np.linalg.norm(status.state.p[:2] - np.asarray(p_surv, dtype=float)[:2])) / v_cruise


def _energy_fraction(status: DroneStatus) -> float:
    return status.battery_energy_j / status.battery_energy_max_j


def cost_eq38(status: DroneStatus, p_surv: np.ndarray, v_cruise: float, weights: dict) -> AssignmentCostTerms:
    """[P2 Eq. 38-40]; weights: alpha, beta, gamma."""
    e = max(_energy_fraction(status), 1e-9)
    payload = 0.0 if status.payload_present else math.inf
    return AssignmentCostTerms(weights["alpha"] * _time_to_intercept(status, p_surv, v_cruise),
                               weights["beta"] / e, payload, None)


def cost_eq179(status: DroneStatus, p_surv: np.ndarray, v_cruise: float, weights: dict,
               abandoned_area_frac: float) -> AssignmentCostTerms:
    """[P2 Eq. 179-181]; weights: alpha1, alpha2 (unused once no-payload is infinite), alpha3."""
    payload = 0.0 if status.payload_present else math.inf
    return AssignmentCostTerms(_time_to_intercept(status, p_surv, v_cruise),
                               weights["alpha1"] * (1.0 - _energy_fraction(status)), payload,
                               weights["alpha3"] * abandoned_area_frac)


def total(terms: AssignmentCostTerms) -> float:
    return terms.time_to_intercept_s + terms.battery_term + terms.payload_term + (terms.abandonment_term or 0.0)
