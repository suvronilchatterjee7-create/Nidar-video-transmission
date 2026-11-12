"""Declarative preflight gate table for the 300 s setup window [BRIEF §3] [P2 §12.4].

Each gate is a named check returning PASS / FAIL / PENDING; START is allowed only when every gate passes, and
a gate that cannot be evaluated is PENDING, never silently skipped [ADIAT-inspired: failure isolation, errors
that name the operation]. Gates and their sources:
  mission_loaded          boundary loaded and <= 10 ha            [BRIEF §1, §3]
  fleet_size              at least two drones reporting          [BRIEF §1]
  fleet_weight            declared all-up weight <= 25 kg        [BRIEF §2]
  link_up                 every drone heard within the timeout   [P2 §12.4 step 1]
  estimator               tr(P_pos) <= eps_lidar on every drone  [P2 §12.4 step 4]
  gnss                    GNSS accepted on every drone           [P2 §12.4 step 4]
  payload                 a kit on board every drone             [P2 §12.4 step 3]
  battery                 energy above the minimum fraction      (setting; needed by the low-battery failsafe)
  video_floor             a certified floor design fits          [P1 Prop. 18, Cor. 6]
Thresholds have no defaults: they are settings (eps_lidar 0.5 m^2 is Paper 2's representative value).
"""
from __future__ import annotations

from typing import Callable, Mapping

from nidar.common.contracts import DroneStatus, MissionDefinition
from nidar.common.units import FLEET_MAX_KG, MIN_DRONES

PASS, FAIL, PENDING = "PASS", "FAIL", "PENDING"


class PreflightRunner:
    def __init__(self, eps_lidar_m2: float, min_battery_frac: float, link_timeout_s: float) -> None:
        self.eps_lidar_m2 = eps_lidar_m2
        self.min_battery_frac = min_battery_frac
        self.link_timeout_s = link_timeout_s

    def run(self, mission: MissionDefinition | None, statuses: Mapping[int, DroneStatus], now: float = 0.0,
            fleet_weight_kg: float | None = None, video_floor_ok: Callable[[], bool] | None = None) -> dict:
        """Evaluate every gate. ``statuses``: drone_id -> latest DroneStatus."""
        s = list(statuses.values())

        def all_drones(pred: Callable[[DroneStatus], bool]) -> str:
            return PENDING if not s else (PASS if all(pred(x) for x in s) else FAIL)

        gates = {
            "mission_loaded": PASS if mission is not None else PENDING,
            "fleet_size": PASS if len(s) >= MIN_DRONES else FAIL,
            "fleet_weight": PENDING if fleet_weight_kg is None else (PASS if fleet_weight_kg <= FLEET_MAX_KG else FAIL),
            "link_up": all_drones(lambda x: now - x.state.t_source <= self.link_timeout_s),
            "estimator": all_drones(lambda x: x.estimator.trace_pos_m2 <= self.eps_lidar_m2),
            "gnss": all_drones(lambda x: x.estimator.gnss_accepted),
            "payload": all_drones(lambda x: x.payload_present),
            "battery": all_drones(lambda x: x.battery_energy_j / x.battery_energy_max_j >= self.min_battery_frac),
            "video_floor": PENDING if video_floor_ok is None else (PASS if video_floor_ok() else FAIL),
        }
        return gates

    @staticmethod
    def ready(gates: Mapping[str, str], required: frozenset[str] | None = None) -> bool:
        """True when every required gate is PASS (all gates if ``required`` is None)."""
        names = gates.keys() if required is None else required
        return all(gates.get(n) == PASS for n in names)
