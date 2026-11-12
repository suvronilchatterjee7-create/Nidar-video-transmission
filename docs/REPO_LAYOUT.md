# Repository Layout

Status: **Phase 2 skeleton created** on branch `phase2/skeleton` (see "Phase 2 status" at the end).

**Starting point:** the tree you suggested [TEAM-BRIEF §6.2].
**Adaptations**, each justified in the table further down:
- `swarm/` is split from `onboard/` along the GCS vs drone line.
- `video/` is split into encoder / decoder / certificates.
- `tools/` is added for offline certificate-grid generation.

```
NiDaR/
├── docs/
│   ├── sources/                        # the 3 source PDFs (copies)  [TEAM-BRIEF §10]
│   ├── ARCHITECTURE.md  VIDEO_SUBSYSTEM.md  INTERFACES.md  TRACEABILITY.md
│   ├── REPO_LAYOUT.md  RISK_REGISTER.md  OPEN_QUESTIONS.md  IDEAS_PENDING.md
├── nidar/
│   ├── common/
│   │   ├── contracts/                  # INTERFACES.md as code: base, mission, state, perception, swarm, link, video, gcs
│   │   ├── units.py                    # SI helpers, frames, quaternion utils
│   │   ├── registry.py + registry.json # name -> module/class/platforms/sources   [ADIAT-inspired: algorithms.conf]
│   │   ├── logging.py                  # central logger, contextual errors   [ADIAT-inspired: LoggerService]
│   │   └── missionlog.py               # versioned, append-only mission log   [ADIAT-inspired: versioned results]
│   ├── onboard/                        # runs on each drone   [P2 §1-§14]
│   │   ├── estimation/                 # eskf.py, ndt.py, gates.py (OQ-05d)
│   │   ├── mapping/                    # tsdf.py
│   │   ├── perception/                 # detector.py (adapter over YOLOv8-pose), geotag.py
│   │   ├── planning/                   # coverage_bcd.py, dubins.py, minsnap.py, safe_corridor.py
│   │   ├── control/                    # nmpc.py (interface + acados binding), cbf.py, lexicographic.py, disturbance_observer.py
│   │   ├── automaton/                  # table-driven SHA; mode_tables/ holds both P2 variants (OQ-05a)
│   │   └── payload/                    # release.py, hybrid_reset.py   [P2 §8.4, §9.5]
│   ├── swarm/                          # multi-agent logic   [P2 §5, §7, §9.3]
│   │   ├── dwvt.py                     # weighted Voronoi + Lloyd + hysteresis (GCS)
│   │   ├── auction/                    # cost.py (both forms, OQ-05c), hungarian.py (GCS)
│   │   └── confirmation.py             # Bayesian belief grid + fusion (onboard)
│   ├── link/                           # [BRIEF §5] [P2 §12.1] [P1 §3.1]
│   │   ├── radio.py                    # Radio protocol + loopback/sim radio
│   │   ├── framing.py                  # telemetry messages, seq/ack, heartbeat
│   │   ├── resource_plan.py            # per-GoP channel-use split (telemetry slice: OQ-14)
│   │   └── priority_mux.py             # P2 state > map > video ordering (rates: OQ-15)
│   ├── video/                          # Paper 1   [P1]
│   │   ├── transform.py                # Def. 4
│   │   ├── variance_field.py           # A3, §D.3, Lemma 9
│   │   ├── floor/                      # designer.py (Def. 7), quantiser.py, entropy.py, crc.py
│   │   ├── certificates/               # info_density.py (Eq. 22-24), dt_bound.py (Eq. 25, Thm 1),
│   │   │                               # kl_certificate.py (Prop. 11), sizing.py (Eq. 26-27),
│   │   │                               # outage.py (Rayleigh L-block quantiles), grid.py (Prop. 18)
│   │   ├── refinement/                 # allocator.py (Prop. 8/16, Lemma 7), limiter.py (Lemma 6), spreader.py
│   │   ├── pilots.py                   # Eq. 35
│   │   ├── control/                    # snr_predictor.py (Lemma 8, Thm 3), controller.py (Eq. 32, 40)
│   │   ├── encoder.py                  # E1-E7 orchestration
│   │   ├── decoder.py                  # D1-D5, Kalman bank (Lemma 3, Prop. 3), cond. mean (Prop. 9), fallback
│   │   └── quality.py                  # T_eq (Def. 6), beta_up (Prop. 10), violation counter (Cor. 7)
│   └── gcs/                            # single operator station   [BRIEF §4]
│       ├── mission_loader/             # parser registry (OQ-22)
│       ├── preflight.py                # gate table   [P2 §12.4]
│       ├── global_state.py             # N x 13 matrix + display predictor   [P2 §12.1, §14.3]
│       ├── services/                   # partition_service.py, auction_service.py, video_service.py
│       ├── controllers/                # UI wiring only   [ADIAT-inspired: layering]
│       └── views/                      # UI; generated files never hand-edited
├── sim/                                # offline only
│   ├── channel/                        # block Rayleigh, AR(1) SNR, delayed/noisy reports   [P1 Table 13 ph. 1-2, A7]
│   ├── mission/                        # kinematic multi-drone sim driving onboard/ + gcs/ via contracts
│   └── scenarios/                      # boundary files, survivor placements, seeds
├── tools/
│   └── build_certified_grid.py         # offline Prop. 11 sampling -> versioned grid artefact
├── tests/
│   ├── unit/                           # per module
│   ├── paper1/                         # VT-01 … VT-19   (VIDEO_SUBSYSTEM.md §11)
│   ├── paper2/                         # closed-form checks, e.g. Eq. 155 (1.962 N), Eq. 174, Eq. 230 (0.427 m/s^2)
│   ├── contracts/                      # same tests run on Python reference and compiled implementations
│   └── traceability/                   # fails if a requirement lacks module or test   [TEAM-BRIEF §8 Phase 2]
├── pyproject.toml                      # deps pinned; toolchain OQ-26
└── .gitignore
```

## Justification of the deviations

| Change vs suggested tree | Why | Tag |
|---|---|---|
| `swarm/` holds both GCS-run code (DWVT, auction) and onboard code (confirmation) | Paper 2 places DWVT and the auction at the GCS and confirmation onboard; keeping the *algorithms* together stops them drifting apart. Deployment is chosen by registry `platforms` | [P2 §5.3, §7.1, §9.3] [ADIAT-inspired: registry platforms] |
| `video/certificates/` as its own package | The certificate is the safety argument [P1 Thm 1–4]. It must be testable on its own and reused offline by `tools/` | [P1 Prop. 11, Prop. 18] |
| `tools/build_certified_grid.py` | The grid is computed offline. Runtime only *loads* it, so runtime safety does not depend on runtime sampling | [P1 Prop. 18] |
| `onboard/automaton/mode_tables/` | Two incompatible Paper 2 mode sets. Table-driven, so the choice is data, not code | OQ-05a [ADIAT-inspired: config-driven] |
| `gcs/controllers` + `views` + `services` split | UI wiring separated from logic | [ADIAT-inspired: ADIAT-standards §2.1] |
| `tests/contracts/` | Same contract tests on the Python reference and the compiled implementation | [TEAM-BRIEF §6.2 "keep onboard real-time components behind interfaces"] |

## Phase 2 status

**Implemented, real code with tests:**

| Area | Files | What works |
|---|---|---|
| Contracts | `nidar/common/contracts/{base,mission,state,perception,swarm,link,video,gcs,components}.py` | Every type in INTERFACES.md as a frozen dataclass or Protocol, with validation (shapes, ranges, unit quaternion, CCW polygon ≤ 10 ha, source-frame bbox, ResourcePlan sums, certified-design rule p̄ ≤ ε_core/2) |
| Isolation | `run_isolated` in `contracts/base.py` | Failure becomes `error_message` naming component, operation and input; the pipeline continues |
| Registry | `nidar/common/registry.py`, `registry.json` (26 components) | Loads, validates source tags and evidence levels, resolves by platform, fails loudly |
| Logging | `nidar/common/logging.py` | Namespaced loggers; `ContextError` |
| Mission log | `nidar/common/missionlog.py` | Versioned JSONL; migrations; refuses newer schemas; never overwrites |
| Units | `nidar/common/units.py` | Brief and Paper 2 constants; quaternion and dB helpers |
| Operator gate | `nidar/gcs/controllers/operator_actions.py` | Exactly 4 Brief actions, enabled by mission phase |
| Mission loader | `nidar/gcs/mission_loader/` | Parser registry. No parser yet (OQ-22): fails cleanly, naming the file |
| Mode tables | `nidar/onboard/automaton/` | Both Paper 2 variants load as candidates; no active table (OQ-05a) |
| Gates | `tools/check.py`, `.github/workflows/ci.yml`, `pyproject.toml` | ruff lint (incl. no-print) + pytest |

**Stubs:** 53 modules, every callable raising `NotYetImplemented` with its source equation:
- `onboard/*`, `swarm/*`, `link/*`, `video/*`
- `gcs/preflight.py`, `gcs/global_state.py`, `gcs/services/*`
- `sim/*`
- `tools/build_certified_grid.py`

**Tests:** 244 pass. They cover:
- contracts
- isolation
- registry ↔ interface conformance
- mission log
- operator gate
- static rules: no network imports in runtime (CT-01), no `print` (CT-04), layering, display predictor not used by onboard (GT-14), and every module docstring carrying a source tag
- **the traceability gate**

**The traceability gate** (`tests/traceability/`) reads `docs/TRACEABILITY.md` and fails if any requirement:
- has no resolvable module, or
- has no test ID registered in `tests/test_index.json`

It also fails if an "implemented" test ID points at a missing test.

**Index status:** 92 test IDs in total. 9 are implemented; the others are planned with their phase.

**Additions vs the tree above:**
- `contracts/components.py`: the INTERFACES §9 protocols
- `gcs/controllers/operator_actions.py`
- `tests/test_index.json`
- `tools/check.py`

## Phase 3 status (branch `phase3/video-reference`)

**Implemented and verified against Paper 1's tables** (see [REPRODUCTION_P1.md](REPRODUCTION_P1.md)):

| Area | Files |
|---|---|
| Certificates | `video/certificates/{info_density, sizing, dt_bound, kl_certificate, outage, grid}.py` |
| Floor | `video/floor/designer.py` |
| Decoder closed forms | `video/decoder.py`: Eq. 10, 18, 20 |
| Refinement | `video/refinement/{allocator, limiter}.py` |
| Pilots and quality | `video/pilots.py`, `video/quality.py` |
| Control | `video/control/{snr_predictor, controller}.py` |
| Channel simulator | `sim/channel/{block_fading, snr_process}.py` |
| Synthetic experiment | `sim/video/synthetic_model.py` (new) |
| Grid builder | `tools/build_certified_grid.py` |

**Tests:** `tests/paper1/`, with VT-01..VT-19, CT-12 and CT-14 implemented.
- Slow Monte-Carlo cases run with `tools/check.py --full`.
- 30 of the 92 test IDs are now implemented.

**Still stubs:**
- `video/{transform, variance_field, encoder}.py`
- `video/floor/{quantiser, entropy, crc}.py`
- `video/refinement/spreader.py`
- `HybridDecoder.decode`

These wait for the video-format and radio decisions (OQ-12, OQ-03/10, OQ-23).

## Phase 4 status (branch `phase4/video-pipeline`)

**The Paper 1 video link is now built end to end in software.** Results are in [VIDEO_PIPELINE.md](VIDEO_PIPELINE.md).

| Area | Files |
|---|---|
| Video pipeline | `video/{transform, variance_field, config, gop_model, encoder, receiver}.py`; `video/floor/{quantiser, entropy, crc, code}.py`; `video/refinement/spreader.py` |
| End-to-end simulation and test video | `sim/video/{end_to_end, test_video, h264_baseline}.py` (H.264 via the local ffmpeg) |
| GCS video service | `gcs/services/video_service.py` |
| Loopback radio | `link/radio.py` |

**Tests:** `tests/video/` (CT-10, CT-11, CT-13, GT-11, VT-21..VT-23). 37 of the 95 test IDs are now implemented.

**Still open by decision:**
- the real floor code (OQ-23)
- the SDR driver (OQ-03/10)
- the GCS widget toolkit (OQ-35)
- the remaining Phase 4 interpretations (OQ-32..34)

## Phase 5 status (branch `phase5/mission-sim`)

**The swarm and GCS mission logic now run in a kinematic multi-drone mission simulator.** Results are in [MISSION_SIM.md](MISSION_SIM.md).

| Area | Files |
|---|---|
| Swarm | `swarm/dwvt.py`, `swarm/confirmation.py`, `swarm/auction/{cost, hungarian}.py` |
| Onboard (pure logic) | `onboard/planning/{coverage_bcd, dubins}.py`, `onboard/payload/hybrid_reset.py`, `onboard/automaton/guards.py` |
| Link | `link/{priority_mux, resource_plan}.py` |
| GCS | `gcs/mission_loader/geojson.py`, `gcs/preflight.py`, `gcs/global_state.py`, `gcs/services/{partition, auction}_service.py` |
| Simulation | `sim/mission/kinematic.py`, `sim/scenarios/*.json` (10 scenarios + GeoJSON boundary) |
| Tools | `tools/run_mission.py` |

**Tests:** `tests/mission/`. 65 of the 95 test IDs are now implemented; 530 fast tests pass.

**Decided by the team (2026-11-12):** OQ-01 (kits per drone is a setting), OQ-05 (all variants selectable, later sections as baseline), OQ-16 (recall = pad, abort = land in place), OQ-22 (GeoJSON).

**Still stubs:** estimator, NDT, TSDF, detector, geotagger, min-snap, NMPC, CBFs, lexicographic fallback, disturbance observer, payload release driver, mode-table automaton, safe corridor, framing.

## What is *not* in the repo
- ADIAT source: patterns only, clean-room [TEAM-BRIEF §4].
- The dataset images or weights: they are referenced by path or URL to your NIDAR repo [DATASET]. They are not vendored, because of size (98 MB) and licence (OQ-08a).
- Any cloud, deployment or website code: there is no runtime network [BRIEF §5].
