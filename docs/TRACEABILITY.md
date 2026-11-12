# Traceability Matrix

Status: **Phase 1 draft**.
- Every requirement maps to: source → module → test → evidence level [TEAM-BRIEF §6.1 D10].
- Module paths follow [REPO_LAYOUT.md](REPO_LAYOUT.md).
- Test IDs are **planned**; none exist yet.
- In Phase 2, `tests/traceability/` parses this table and fails if any row lacks a module or a test.

**Evidence levels** ([ARCHITECTURE.md §0.2](ARCHITECTURE.md#02-evidence-levels)):
- PROVED (conditional on the stated assumptions)
- REPRODUCED (our implementation matches the source's published number; see docs/REPRODUCTION_P1.md)
- SIMULATED (source's own numbers, not yet reproduced by us)
- TARGET (source says unvalidated)
- REQUIRED (Brief rule, awaiting test)
- OPEN (blocked on an OQ)

**Test ID prefixes:**

| Prefix | Meaning |
|---|---|
| `VT-nn` | Paper 1 reproduction ([VIDEO_SUBSYSTEM.md §11](VIDEO_SUBSYSTEM.md#11-verification-plan-phase-3-only-after-approval-team-brief-8-phase-3)) |
| `PT-nn` | Paper 2 closed-form or unit checks |
| `MS-nn` | Mission-simulator scenario tests |
| `CT-nn` | Contract / interface tests |
| `GT-nn` | GCS behaviour tests |
| `HW-nn` | Hardware or field tests (out of software scope; listed for completeness) |

## 1. Deliverables → requirements

| Deliverable [TEAM-BRIEF §6.1] | Requirements |
|---|---|
| D1 Multi-drone collaborative system ≤ 25 kg | R-B01, R-B02, R-B03, R-B04, R-B09 |
| D2 Single GCS, display set, 4 actions | R-B05, R-B07, R-B10, R-B11a–f, R-P2-19, R-P2-20 |
| D3 Autonomous coverage, allocation, drop, return ≤ 30 min | R-B06, R-B09, R-B18, R-P2-06…R-P2-10, R-P2-13, R-P2-22, R-P2-24 |
| D4 Detection, 3-D geotag with covariance, Bayesian confirmation | R-P2-04, R-P2-05, R-P2-03 |
| D5 Paper 1 video | R-P1-01…R-P1-16 |
| D6 Local-only comms, degradation, priority mux | R-B12, R-P2-17, R-P2-18, R-P1-08 |
| D7 Failsafes and modes | R-B16, R-B17, R-B14, R-B15, R-P2-14, R-P2-15, R-P2-16 |
| D8 5-minute setup pipeline | R-B05, R-B13, R-P2-21 |
| D9 Verification and simulators | VT-01…VT-19, the `sim/channel` and `sim/mission` rows below |
| D10 Traceability and honesty | this file, `tests/traceability/` |

## 2. Mission Brief requirements

| ID | Requirement | Source | Module(s) | Test(s) | Evidence |
|---|---|---|---|---|---|
| R-B01 | ≥ 2 drones in one collaborative system | [BRIEF §1, §4] | `swarm/*`, `gcs/global_state` | MS-01 (N = 2 and N = 4 runs) | REQUIRED; SIMULATED (kinematic mission sim, Phase 5): 2 and 4 drones complete |
| R-B02 | Team-built airframes, no RTF | [BRIEF §2] | — (hardware) | HW-01 | REQUIRED |
| R-B03 | Fleet AUW ≤ 25 kg | [BRIEF §2] | — (hardware; budget in ARCHITECTURE §9.1) | HW-02 weigh-in | OPEN (OQ-07) |
| R-B04 | Payload 200 g, 20×10×5 cm box | [BRIEF §2] | `onboard/payload` | PT-05 mass reset uses 0.2 kg; HW-03 | REQUIRED |
| R-B05 | Mission file loaded at setup; ≤ 300 s setup | [BRIEF §3] | `gcs/mission_loader`, `gcs/preflight` | GT-01 parse + validate; MS-02 setup timeline ≤ 300 s (sim) | OPEN (setup timing); GeoJSON loader implemented (OQ-22 decided for now) |
| R-B06 | Autonomous scout → coordinate → detect → geotag → assign → drop → return within 30 min | [BRIEF §3] | `onboard/*`, `swarm/*`, `gcs/services` | MS-03 end-to-end scenario, with timing | REQUIRED; SIMULATED (kinematic mission sim, Phase 5): baseline 629 s with placeholder speeds; P2 ≤ 11 min is TARGET |
| R-B07 | Operator inputs limited to load / start / abort / recall | [BRIEF §3, §4] | `gcs/controllers`, `common/contracts` `OperatorAction` | GT-02: UI exposes exactly 4 actions; GT-03: no other command path into `GcsCommand` | REQUIRED; gate tested, manual inputs rejected in sim |
| R-B08 | No swap after start | [BRIEF §3] | — (procedure) | HW-04 | REQUIRED |
| R-B09 | Area division, task allocation, parallel scouting, delivery assignment, shared progress | [BRIEF §4] | `swarm/dwvt`, `swarm/auction`, `gcs/global_state` | MS-04 | REQUIRED; SIMULATED (kinematic mission sim, Phase 5) |
| R-B10 | Single GCS; no separate control systems | [BRIEF §4] | `gcs/` (single instance) | GT-04: second GCS instance refused | REQUIRED |
| R-B11a | Display: mission file / boundary loading | [BRIEF §4] | `gcs/views`, `GcsDisplayModel.mission_loaded` | GT-05 | REQUIRED; display model filled by the sim (widget OQ-35) |
| R-B11b | Display: live location and status of all drones | [BRIEF §4] | `gcs/global_state` | GT-06 | REQUIRED; implemented |
| R-B11c | Display: tagged survivor locations | [BRIEF §4] | `GcsDisplayModel.survivors` | GT-07 | SIMULATED (confirmed tags shown); provisional tags OPEN (OQ-05l) |
| R-B11d | Display: kit delivery status per drone | [BRIEF §4] | `DeliveryEvent`, `gcs/views` | GT-08 | REQUIRED; filled by the sim |
| R-B11e | Display: progress and completion | [BRIEF §4] | `GcsDisplayModel.coverage_fraction`, `GcsDisplayModel.mission_phase` | GT-09 | REQUIRED; filled by the sim |
| R-B11f | Display: live video | [BRIEF §4] | `VideoSource`, `video/receiver`, `gcs/services/video_service` | GT-11; VT series | OPEN (OQ-02, OQ-09, OQ-35 widget); service implemented |
| R-B12 | No external network; local RF only; no tethers | [BRIEF §5] | `link/radio` | CT-01: no socket to a non-local address in the runtime package (static check); HW-05 | REQUIRED |
| R-B13 | ≤ 2 setup people; 1 operator | [BRIEF §6] | — (procedure) | HW-06 rehearsal | REQUIRED |
| R-B14 | Launch and land inside the 12 ft pad; nothing outside | [BRIEF §7] | `onboard/planning` terminal constraint, `gcs/preflight` | MS-05 landing inside Z; PT-08 terminal constraint | SIMULATED (kinematic mission sim, Phase 5): all land in Z; pad separation OPEN (OQ-18) |
| R-B15 | Operate only inside the boundary | [BRIEF §7] | `onboard/control/cbf` (geofence) | PT-06 CBF keeps the boundary in sim; MS-06 gust case | OPEN (OQ-05i, 05j, 17) |
| R-B16 | Failsafes: RTH, low battery, C2 loss, geofence breach, abort, recall | [BRIEF §8] | `onboard/automaton`, `onboard/planning/safe_corridor` | MS-07…MS-12 (one per failsafe) | SIMULATED (kinematic mission sim, Phase 5): RTH, low battery, link loss, abort, recall; geofence-breach action OPEN (OQ-17) |
| R-B17 | Operator can abort and recall all drones | [BRIEF §8] | `gcs/controllers`, `link/framing` (repeat until acked) | GT-12; MS-11, MS-12 | SIMULATED (kinematic mission sim, Phase 5) (OQ-16 decided: recall = pad, abort = land in place) |
| R-B18 | Detect and geotag up to 10 survivors; kit to each identified one | [BRIEF Scenario, §1] | `onboard/perception`, `swarm/auction`, `onboard/payload` | MS-13 with 10 survivors | SIMULATED (kinematic mission sim, Phase 5): 10 tagged; kits per drone is a setting (OQ-01 decided) |

## 3. Paper 1 requirements (video)

| ID | Requirement | Source | Module(s) | Test(s) | Evidence |
|---|---|---|---|---|---|
| R-P1-01 | Chance-constrained floor P[T_eq < T_min] ≤ ε_F per GoP | [P1 Problem 2 (F), Thm 2] | `video/floor/*`, `video/certificates/*` | VT-06, VT-07, VT-08; channel-sim outage count | PROVED (A1–A6); certificate numbers REPRODUCED (Tables 7–10, ≤1.2 %; L≤2 ideal cells −0.4/−0.9 %) |
| R-P1-02 | Ceiling tracking up to 10 Mbps-eq | [P1 Problem 2 (R)] | `video/refinement/*`, `video/control/controller` | VT-13, VT-18 | SIMULATED (η ≈ 0.66, one clip); synthetic sweep NOT REPRODUCED in level (structure only) |
| R-P1-03 | Orthonormal spatio-temporal transform, no encoder motion search | [P1 Def. 4, Lemma 2] | `video/transform` | CT-10 orthonormality, distortion invariance | PROVED; implemented and tested (Phase 4) |
| R-P1-04 | Variance field and protected metadata | [P1 A3, A5, §D.3, Lemma 9] | `video/variance_field` | CT-11 quantisation round-trip; size vs 36,360-bit pilot figure | REPRODUCED (2,880 chunks, 36,360 bits) |
| R-P1-05 | Firewalled floor, sized by water level and Eq. 16–17 | [P1 Def. 7, Prop. 6–7] | `video/floor/designer` | VT-01 | PROVED; Table 5 REPRODUCED exactly |
| R-P1-06 | Certified finite-blocklength floor block | [P1 Thm 1, Prop. 11–12, Rem. 7–8] | `video/certificates/*`, `tools/build_certified_grid` | VT-05, VT-06, VT-07 | PROVED (i.i.d., Rayleigh, perfect CSI); Tables 7–8 REPRODUCED |
| R-P1-07 | Refinement allocation with side information, estimation error, limiter | [P1 Prop. 8, Prop. 16, Lemma 6, Rem. 6] | `video/refinement/*` | VT-03, VT-04, VT-12, VT-16, VT-14 | PROVED; Table 15 REPRODUCED exactly; Table 17 bound verified (instances unstated) |
| R-P1-08 | Timely SNR feedback and margin rule | [P1 A7, Lemma 8, Thm 3, Table 19] | `video/control/snr_predictor`, `link/framing` `SnrReport` | VT-17; channel-sim with delay d | PROVED (A7–A8; A8 unproved in general); Table 19 REPRODUCED; A8 point check REPRODUCED |
| R-P1-09 | Controller restricted to a certified grid | [P1 Eq. 32, Eq. 40, Prop. 17–18, Thm 4] | `video/control/controller`, `video/certificates/grid` | VT-13, VT-18; CT-12: output ∈ grid always | PROVED; grid membership tested; controller dynamics REPRODUCED, fixed point 9.0 vs 9.41 dB NOT |
| R-P1-10 | Decoder: Kalman side info, conditional mean, floor fallback | [P1 Lemma 3, Prop. 3, Prop. 9, Rem. 5] | `video/decoder` | VT-02, VT-03; CT-13 fallback on mismatch | PROVED (Gaussian model); Eq. 10, 18, 20 REPRODUCED; orchestration OPEN (OQ-12) |
| R-P1-11 | Diversity L ≥ 4 exposed as a gate | [P1 Cor. 6] | `gcs/preflight`, `CertifiedFloorDesign.L` | VT-08; GT-13 gate refuses L < design L | SIMULATED; OPEN for our link (OQ-03) |
| R-P1-12 | Latency T_g + τ_proc ≤ L_max | [P1 (L)] | `video/encoder`, `video/receiver` | VT-20 latency budget (needs L_max) | OPEN (OQ-13); measured ≈1.1 s per 0.32 s GoP in Python (not real time) |
| R-P1-13 | Pilots and channel estimation | [P1 §C.1 Eq. 35, Table 18] | `video/pilots` | VT-15 | REPRODUCED (Table 18: all pilot counts, rates ±0.003) |
| R-P1-14 | Quality accounting (T_eq, β_up, violation counter) | [P1 Def. 6, Prop. 10, Cor. 7] | `video/quality` | VT-19; GT-11 | PROVED (definitions); Cor. 7 REPRODUCED |
| R-P1-15 | Fading and delayed-feedback channel simulator | [P1 Table 13 ph. 1–2, A7, §6.4] | `sim/channel` | CT-14 statistics (block gains Exp(1), AR(1) moments) | — (tool, implemented Phase 3) |
| R-P1-16 | End-to-end link: floor holds when decoded (H1), model predicts quality (H2), comparison with a digital codec (H5) | [P1 §D.1, §D.5] | `sim/video/end_to_end`, `video/receiver`, `video/encoder` | VT-21 H1, VT-22 H2, VT-23 H5 | SIMULATED by us on test video: H1 ✅, H2 ✅ (≤0.61 dB), H5 not supported (−7.5…−27 dB) |

## 4. Paper 2 requirements (swarm, mission)

| ID | Requirement | Source | Module(s) | Test(s) | Evidence |
|---|---|---|---|---|---|
| R-P2-01 | 13-dim state; Newton–Euler; hybrid mass/inertia jump | [P2 §1.2–§1.3, Eq. 8–16] | `common/contracts/state`, `onboard/payload/hybrid_reset`, `sim/mission` | PT-01 quaternion norm preserved; PT-05 Δm = 0.2 kg, ΔT = 1.962 N, Δa ≈ 0.427 m/s² | PROVED (arithmetic) |
| R-P2-02 | ES-EKF 15-dim error state; IMU 200 Hz; LiDAR / GNSS updates | [P2 §2.1, §4.1, Eq. 68–76] | `onboard/estimation/eskf` | PT-02 consistency (NEES) in sim | TARGET |
| R-P2-03 | NDT scan matching; TSDF terrain | [P2 §4.2, Eq. 77–87] | `onboard/estimation/ndt`, `onboard/mapping/tsdf` | PT-03 on synthetic terrain | TARGET |
| R-P2-04 | Ray-cast geotag with covariance; Low-Confidence re-observation | [P2 §4.3, Eq. 88–100] | `onboard/perception/geotag` | PT-04 known-pose geometry; covariance propagation vs Monte Carlo | PROVED (first order) / OPEN gate form (05k) |
| R-P2-05 | Bayesian confirmation: prior 0.01, K = 10, multi-drone fusion, promote at P > 0.95 | [P2 §9.3, Eq. 258–265] | `swarm/confirmation` | PT-09 update arithmetic; MS-14 false-positive scenario | TARGET; MS-14 shows a 0.7-confidence decoy gets confirmed (OQ-25) |
| R-P2-06 | DWVT partition + Lloyd density | [P2 §5.1/§7.1, Eq. 157–168] | `swarm/dwvt` | PT-10 cells tile W; PT-11 smaller w → smaller cell | PROVED (geometry); both weight laws selectable, linear is baseline |
| R-P2-07 | BCD + Dubins coverage; spacing ≤ W_FOV(1 − overlap) | [P2 §5.2/§7.2, Eq. 169–175] | `onboard/planning/coverage_bcd`, `onboard/planning/dubins` | PT-12 full coverage of a test polygon; PT-13 R_min formula | PROVED (geometry) |
| R-P2-08 | Boundary hysteresis and tanh speed damping | [P2 §5.4, Eq. 126–131] | `swarm/dwvt`, `onboard/planning` | PT-14 no chattering under injected noise | TARGET; hysteresis tested |
| R-P2-09 | GCS min-cost assignment (Hungarian) | [P2 §5.3/§7.3, Eq. 176–187] | `swarm/auction/*`, `gcs/services/auction_service` | PT-15 vs brute force for N ≤ 4; PT-16 infeasible case reported (OQ-01) | PROVED (optimality, tested vs brute force); both cost forms selectable, Eq. 179 baseline |
| R-P2-10 | Min-snap B-spline QP with kinematic and terrain limits | [P2 §8.1/§10.1, Eq. 188–198] | `onboard/planning/minsnap` | PT-17 waypoint interpolation and limits | PROVED (QP) / TARGET timing |
| R-P2-11 | NMPC 50 Hz, N_h = 20, RK4, SQP-RTI | [P2 §8.2/§10.2, Eq. 199–208] | `onboard/control/nmpc` | PT-18 tracking in sim; HW-07 timing on target (8–12 ms claim) | TARGET |
| R-P2-12 | CBFs: inter-agent (d_safe 3 m), terrain, geofence | [P2 §8.3/§11.1, Eq. 209–226] | `onboard/control/cbf` | PT-06, PT-19 two-drone head-on | PROVED (conditional on feasibility) |
| R-P2-13 | Payload-drop feedforward; terminal ≤ 0.5 m, ≤ 0.3 m/s; IBVS within 3 m | [P2 §8.4, §9.5, §12.2.2, Eq. 227–238, 272] | `onboard/payload`, `onboard/control` | PT-05, PT-08; HW-08 drop accuracy | TARGET (0.3 m) / OPEN (OQ-20) |
| R-P2-14 | Lexicographic infeasibility handling + disturbance observer | [P2 §8.5, §9.4, §14.2] | `onboard/control/lexicographic`, `onboard/control/disturbance_observer` | PT-20 infeasible-QP injection → safe state | OPEN (priority 05j) |
| R-P2-15 | Hybrid automaton: low battery → RTH, comms loss → RTH | [P2 §9.1, §11.2, §14.1, Eq. 243–249] | `onboard/automaton` | MS-07, MS-08 | SIMULATED (kinematic mission sim, Phase 5); mode table and timeout are settings (OQ-05a/b) |
| R-P2-16 | Degraded modes: LiDAR, GNSS, blind hover | [P2 §9.2, §13.2, Eq. 250–257] | `onboard/automaton`, `onboard/estimation/gates` | MS-15…MS-17 | OPEN (05d, 05e, 05g, OQ-19) |
| R-P2-17 | Ghost buffer on stale neighbour state (> 200 ms) | [P2 §3.4, §6.4, §14.1] | `onboard/control/cbf` | PT-21 buffer grows with age | OPEN (05h) |
| R-P2-18 | Priority multiplexing state (20 Hz) > map (1 Hz) > video | [P2 §12.1/§15.1.1] | `link/priority_mux`, `link/resource_plan` | CT-15 ordering preserved under overload | OPEN (rates OQ-15, OQ-14); strict priority implemented |
| R-P2-19 | GCS N×13 state matrix; timestamp interpolation; display-only predictor | [P2 §12.1, §14.3] | `gcs/global_state` | GT-14 predictor not fed back to control (static import check) | PROVED (by construction) |
| R-P2-20 | Restricted operator UI | [P2 §12.3.2, §14.3, §15.3.2] | `gcs/controllers` | GT-02 | REQUIRED (plus recall, OQ-16) |
| R-P2-21 | 5-minute preflight state machine | [P2 §12.4/§15.4] | `gcs/preflight` | MS-02 | TARGET (slot times); gate table implemented |
| R-P2-22 | RTH terminal: inside Z, zero velocity | [P2 §12.3.1, §15.3.1] | `onboard/planning/minsnap` | PT-08 | PROVED (constraint) / OPEN (OQ-18) |
| R-P2-23 | Coverage-time bound | [P2 §12.2.3, §15.2.3] | `sim/mission` report | MS-16 computes the bound once OQ-21 is answered | OPEN (camera values OQ-21); bound computed per run |
| R-P2-24 | Mission ≤ 11 min design target | [P2 §12.2.3] | `sim/mission` | MS-03 timing | TARGET (OQ-05f) |

## 5. Methodology (ADIAT-inspired) rows

| ID | Practice | Source | Module | Test |
|---|---|---|---|---|
| R-M01 | Normalised contract + adapters; orchestrator never crashes | [ADIAT-inspired: `contracts.py`, `adapters.py`, `StreamAnalyzeService`] | `common/contracts/base` | CT-02 fault injection: bad item → `error_message`, pipeline continues |
| R-M02 | Config-driven registry; unknown names fail loudly; registered classes match their interface | [ADIAT-inspired: `algorithms.conf`] | `common/registry` | CT-03, CT-08 |
| R-M03 | Central logging with context | [ADIAT-inspired: `LoggerService`] | `common/logging` | CT-04 lint: no `print` in runtime packages |
| R-M04 | Versioned, backward-compatible mission log | [ADIAT-inspired: result files] | `common/missionlog` | CT-05 read v1 with v2 reader |
| R-M05 | Deterministic offline tests | [ADIAT-inspired: tests] [TEAM-BRIEF §9] | `tests/` | CT-06 seed audit; no network in the test environment |
| R-M06 | Source-frame pixel coordinates for detections | [ADIAT-inspired: `StreamDetection`] | `common/contracts/perception` | CT-07 |

## 6. Coverage check (manual, Phase 1)
- Every Brief section §1–§8 appears in at least one row: §1 R-B01/18; §2 R-B02–04; §3 R-B05–08; §4 R-B09–11; §5 R-B12; §6 R-B13; §7 R-B14–15; §8 R-B16–17. ✔
- Every D1–D10 deliverable maps to at least one requirement (§1 above). ✔
- 22 of the 62 requirement rows (Brief + P1 + P2) are OPEN, fully or in part. Each one names its OQ.
- All OQ / IDEA / RISK references and cross-document anchors resolve (script check, 2026-11-11).
