# Mission Simulator and Swarm Logic (Phase 5)

Status: **Phase 5 result** · Branch `phase5/mission-sim` · Date 2026-11-12.
Design: [ARCHITECTURE.md §6](ARCHITECTURE.md#6-key-flows-and-sequences).

> **Read this first.** This is a **kinematic** simulator: drones are points moving at set speeds at one altitude.
> - There is **no** flight dynamics, state estimator, terrain map, NMPC or collision avoidance.
> - It tests the **mission logic**: area division, search, detection → confirmation → auction → delivery → return, the failsafes and the operator buttons, plus timing.
> - Speeds, altitude, camera field of view, battery endurance and detector quality are **placeholders**, not our hardware (OQ-07, OQ-21, OQ-25). Every one is stated in the scenario files.

## 1. Team decisions used (2026-11-12)

| Question | Decision |
|---|---|
| OQ-01 kits vs survivors | Kits per drone is a scenario setting. The baseline is Paper 2's 4 drones × 1 kit; extra survivors are tagged and reported as "no kit left" |
| OQ-16 abort vs recall | Recall = everyone returns and lands on the pad. Abort = everyone lands where they are |
| OQ-05 Paper 2 conflicts | Every variant is a setting. The baseline uses the later sections: cost Eq. 179, linear weight law Eq. 107, 5 s GCS timeout |
| OQ-22 mission file | GeoJSON polygon (lon/lat projected to local metres; optional launch-zone feature) |

## 2. What is now built

| Piece | File | Source | Notes |
|---|---|---|---|
| Survivor auction (Hungarian) | `nidar/swarm/auction/hungarian.py` | [P2 Eq. 183, 125] | Serves as many survivors as possible; the rest are reported, not dropped (Paper 2's version is infeasible when survivors > kits). Tested against brute force (PT-15) |
| Auction cost, both forms | `nidar/swarm/auction/cost.py` | [P2 Eq. 38, 179] | No payload → infinite cost [Eq. 181]; weights are settings (the paper gives none) |
| Weighted Voronoi area partition, Lloyd centroids, weight laws, hysteresis, speed damping | `nidar/swarm/dwvt.py` | [P2 Eq. 29-30, 107, 127, 129, 159, 165, 167] | On a raster of the area (weighted cells have curved edges). Initial cells: farthest-point seeding + Lloyd, because all drones start on the pad |
| Bayesian survivor confirmation | `nidar/swarm/confirmation.py` | [P2 Eq. 258-265] | Prior 0.01, K = 10 frames, P > 0.95. Choices stated in the file: association radius r_tol, gap that resets K, inverse-covariance position fusion |
| Lawn-mower coverage, footprint, spacing | `nidar/onboard/planning/coverage_bcd.py` | [P2 Eq. 114, 171-173] | Bands of width W(1−overlap); non-convex cells split into runs; **every sweep is clipped to the boundary** |
| Turn radius, U-turn length | `nidar/onboard/planning/dubins.py` | [P2 Eq. 174-175] | Turn geometry itself is still a stub |
| Payload-drop mass and thrust feedforward | `nidar/onboard/payload/hybrid_reset.py` | [P2 Eq. 153-155, 230, 272] | −1.962 N, +0.427 m/s² for 4.8 → 4.6 kg |
| Failsafe guards; abort / recall meaning | `nidar/onboard/automaton/guards.py` | [P2 Eq. 245-249] [BRIEF §8] | |
| Priority multiplexer | `nidar/link/priority_mux.py` | [P2 §12.1] | Strict priority state > map > video (Paper 2's linear programme is degenerate, OQ-15) |
| Per-GoP resource plan | `nidar/link/resource_plan.py` | [P1 §3.1] [P2 §12.1] | |
| GeoJSON mission loader | `nidar/gcs/mission_loader/geojson.py` | [BRIEF §3, §7] | Registered by default |
| Preflight gate table | `nidar/gcs/preflight.py` | [P2 §12.4] [BRIEF §1-§3] | 9 gates; START only when all pass |
| GCS global state + display predictor | `nidar/gcs/global_state.py` | [P2 §12.1, §14.3] | Out-of-order packets ignored; prediction for display only |
| Partition and auction services | `nidar/gcs/services/{partition,auction}_service.py` | [P2 §7.1, §7.3] | Weight law and cost form are settings |
| **Mission simulator** | `sim/mission/kinematic.py` | [P2 §5, §7, §9] [BRIEF §3-§8] | Drives all of the above |
| Scenarios | `sim/scenarios/*.json` | | 10 scenarios; `"_base"` inheritance |
| Runner | `tools/run_mission.py` | | One line per scenario, `--timeline` for events |

**What one simulated mission does:**
1. **Load and start:** the GCS loads the GeoJSON boundary through the operator gate, splits the area into equal cells, and the operator presses START.
2. **Search:** each drone takes off and sweeps its cell. The camera covers a disc of radius W/2 under the drone.
3. **Detect:** each frame (30 fps), a survivor under the camera is detected with probability `p_detect` and a noisy confidence. False alarms appear at `fp_rate_hz`.
4. **Confirm:** each drone confirms survivors on board (10 frames, > 95 %). A confirmed tag reaches the GCS if the drone's link is up. Duplicates within r_tol are merged, and other drones are told.
5. **Auction:** the GCS runs the auction among searching drones that still have a kit. When no kit is left anywhere, the survivor is marked "no kit left".
6. **Deliver:** the winner flies to the tag, hovers for `delivery_dwell_s`, and releases. Its old area is re-partitioned among the others.
7. **Finish:** when the area is covered and nothing is pending, everyone returns and lands on the pad.
8. **Failsafes at any time:** low battery → return; GCS link lost beyond the timeout → return; recall → return; abort → land in place.

## 3. Results (`python tools/run_mission.py`)

The boundary is a 9.88 ha pentagon. Placeholder values: altitude 20 m, 60° FOV (footprint 23 m, spacing 20.8 m), 4 m/s sweep, 8 m/s transit, 20 min endurance.

| Scenario | Time | Coverage | Tagged | Delivered | No kit | False tags | On pad | Closest approach |
|---|---|---|---|---|---|---|---|---|
| baseline (4 × 1 kit) | 629 s | 1.000 | 10/10 | 4 | 6 | 0 | 4/4 | 0.4 m |
| kits_3_per_drone | 632 s | 1.000 | 10/10 | **10** | 0 | 0 | 4/4 | 0.0 m |
| two_drones | 902 s | 1.000 | 10/10 | 2 | 8 | 0 | 2/2 | 4.0 m |
| link_loss (drone 2, 150–400 s) | 759 s | 1.000 | 10/10 | 3 | 7 | 0 | 4/4 | 0.6 m |
| low_battery (330 s endurance) | 308 s | 0.469 | 3/10 | 3 | 0 | 0 | 4/4 | 0.4 m |
| recall at 200 s | 238 s | 0.355 | 2/10 | 2 | 0 | 0 | 4/4 | 0.4 m |
| abort at 200 s | 210 s | 0.355 | 2/10 | 2 | 0 | 0 | 0/4 (landed in place) | 0.4 m |
| manual_input_rejected | 629 s | 1.000 | 10/10 | 4 | 6 | 0 | 4/4 | 0.4 m |
| decoy_debris | 666 s | 1.000 | 10/10 | 3 | 7 | **1** | 4/4 | 0.4 m |
| p2_early_variants (Eq. 38, multiplicative, 3 s) | 584 s | 1.000 | 10/10 | 4 | 6 | 0 | 4/4 | 0.0 m |

All runs stay inside the geofence (0 steps outside) and finish inside 30 minutes. The ideal coverage bound A / (N·W·v_sweep) [P2 §12.2.3] is 267 s for the baseline; the real mission takes 2.4× that, because of turns, transits, deliveries and re-planning.

## 4. Findings the team must weigh

1. **Kits decide the score, not the search.**
   - With 1 kit per drone, 6 of 10 survivors get no kit.
   - With 3 kits per drone, all 10 are served in almost the same time (632 s vs 629 s).
   - What is uncertain is the payload mass and mechanism (OQ-07, OQ-20).
2. **Drones cross each other's paths.**
   - A drone flying to a delivery passes through other drones' sweep areas at the same altitude; the closest approach is 0–0.6 m in most runs.
   - Paper 2 relies on control barrier functions in the flight controller for the 3 m separation, and that layer is not built.
   - The plan itself does not deconflict (RISK-S13, IDEA-16).
3. **A decoy gets a kit.**
   - An object the detector scores 0.7 on every frame passes the 0.95 rule after about 10 frames, because Paper 2 counts consecutive frames as independent evidence.
   - One of the 4 kits was wasted on it (RISK-S14; IDEA-07, IDEA-09).
4. **Timing has room.**
   - Even 2 drones finish in 15 min, with placeholder speeds.
   - Paper 2's ≤ 11 min target holds only for 4 drones at these speeds, and only for the mission logic.

## 5. What the simulator does not do (yet)

- **Dynamics and control:** no flight dynamics, NMPC or control barrier functions, so it measures separation and geofence but cannot enforce them.
- **Perception:** no estimator, terrain map or perception errors beyond a Gaussian geotag error.
- **Degraded sensing:** no LiDAR or GNSS degradation, so the Paper 2 degraded modes are untested (OQ-05a mode table, OQ-19).
- **Geofence breach:** no breach failsafe action, because none is decided (OQ-17).
- **Launch and landing:** no launch/landing sequencing on the pad (OQ-18). Pad separation is excluded from the measurement.
- **Setup:** the 300 s setup timeline is not timed (MS-02).
- **Video:** the video link is not attached to the mission run. It is simulated separately ([VIDEO_PIPELINE.md](VIDEO_PIPELINE.md)).
