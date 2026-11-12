"""Run simulated missions and print what happened.

Each scenario file in sim/scenarios/ describes one mission (fleet, kits, survivors, failures, operator inputs).
Values marked as placeholders in the files are NOT our hardware (OQ-07, OQ-21, OQ-25).
[P2 §5, §7, §9] [BRIEF §3, §8] [TEAM-BRIEF §6.1 D9]

Examples (from the repository root):
  python tools/run_mission.py                              # every scenario, one summary line each
  python tools/run_mission.py sim/scenarios/link_loss.json --timeline
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))   # run from a checkout without installing

from sim.mission.kinematic import MissionSimulator, Scenario  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Kinematic multi-drone mission simulator")
    ap.add_argument("scenarios", nargs="*", help="scenario JSON files (default: all in sim/scenarios)")
    ap.add_argument("--timeline", action="store_true", help="print the event timeline of each mission")
    a = ap.parse_args(argv)
    files = [Path(p) for p in a.scenarios] or sorted((ROOT / "sim" / "scenarios").glob("*.json"))
    print(f"{'scenario':<22} {'time':>6} {'<=30min':>7} {'cover':>6} {'tagged':>7} {'deliv':>5} {'no kit':>6} "
          f"{'false':>5} {'on pad':>6} {'min sep':>7} {'fence':>5}")
    for f in files:
        r = MissionSimulator().run(Scenario.load(f))
        pads = sum(bool(v["landed_in_pad"]) for v in r.drones.values())
        print(f"{r.scenario:<22} {r.mission_time_s:>5.0f}s {str(r.within_30_min):>7} {r.coverage_fraction:>6.3f} "
              f"{r.survivors_tagged:>3}/{r.survivors_total:<3} {r.survivors_delivered:>5} "
              f"{r.survivors_without_kit:>6} {r.false_tags:>5} {pads:>3}/{len(r.drones):<2} "
              f"{r.min_separation_m:>6.1f}m {r.geofence_violation_steps:>5}")
        if a.timeline:
            for t, msg in r.timeline:
                print(f"    {t:>7.1f}s  {msg}")
    print("min sep = closest approach between airborne drones away from the pad; no avoidance is simulated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
