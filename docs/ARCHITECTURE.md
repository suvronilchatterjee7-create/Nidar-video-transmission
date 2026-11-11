# NIDAR RescueSwarm — System Architecture

Status: **Phase 1 draft for review** · Branch `docs/phase1-architecture` · Date 2026-11-11

Companion documents:
- [VIDEO_SUBSYSTEM.md](VIDEO_SUBSYSTEM.md)
- [INTERFACES.md](INTERFACES.md)
- [TRACEABILITY.md](TRACEABILITY.md)
- [REPO_LAYOUT.md](REPO_LAYOUT.md)
- [RISK_REGISTER.md](RISK_REGISTER.md)
- [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)
- [IDEAS_PENDING.md](IDEAS_PENDING.md)

---

## 0. Conventions

### 0.1 Traceability tags
Every design decision carries one or more tags:

| Tag | Meaning | Location |
|---|---|---|
| `[BRIEF §n]` | Mission Brief section n (Scenario, §1–§8) | `docs/sources/mission_brief.pdf` |
| `[P1 §x / Eq. y / Prop. z / Thm t / Table k]` | Paper 1, video transmission. §A–§E are the paper's lettered sections after §9 | `docs/sources/paper1_video_transmission.pdf` |
| `[P2 §x / Eq. y]` | Paper 2, swarm model. Where the PDF repeats a section, both copies are cited, e.g. `§5.3/§7.3` | `docs/sources/paper2_swarm_model.pdf` |
| `[ADIAT-inspired: file/pattern]` | Method taken from ADIAT (GPL-3.0) as a *pattern*; our code is a clean-room re-implementation | upstream repo, commit `00bf118` |
| `[TEAM-BRIEF §x]` | The team lead's internal project brief: process rules, deliverables D1–D10, language and layout choices. It is not published in this repository | team lead |
| `[DATASET: path]` | Your team repo `suvronilchatterjee7-create/NIDAR` | GitHub |
| `OQ-nn` | Undecided: see [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md). The design leaves a named slot and no default | — |
| `IDEA-nn` | **Not adopted**: see [IDEAS_PENDING.md](IDEAS_PENDING.md) | — |

### 0.2 Evidence levels
Used in [TRACEABILITY.md](TRACEABILITY.md) and throughout:

- **PROVED**: a theorem or proposition in a source, true *under its stated assumptions*. The assumptions are always listed next to the claim.
- **SIMULATED**: a number the source reports from its own numerics or pilot. It is not yet reproduced by us.
- **REPRODUCED**: a number the source reports that our own implementation reproduces (Phase 3; [REPRODUCTION_P1.md](REPRODUCTION_P1.md)). This shows our code matches the paper; it does **not** make the paper's model true for our link.
- **TARGET**: a design target the source itself calls unvalidated (e.g. 0.3 m drop accuracy, 8–12 ms NMPC, ≤ 11 min).
- **REQUIRED**: a hard rule from the Brief. It is evidenced only by a future test.
- **OPEN**: blocked on an OQ item.

No document in this repo presents a TARGET as a guarantee [TEAM-BRIEF §0.5].

---

## 1. Scope

**In scope:** the architecture of a collaborative autonomous multi-drone search-and-delivery system. It has:
- one ground control station [BRIEF §1–§8]
- a mission layer per Paper 2
- a GCS live-video link per Paper 1

**Out of scope:**
- airframe and propulsion design
- the flight-controller firmware internals (OQ-29)
- anything in [IDEAS_PENDING.md](IDEAS_PENDING.md)

**Hard environmental rule:** no GSM / LTE / 5G / public Wi-Fi / internet / cloud, and no tether, at runtime [BRIEF §5]. No component may assume DNS, NTP-over-internet, a cloud broker or a signalling server. This includes the ADIAT flight viewer's Cloudflare Worker, which is excluded [TEAM-BRIEF §4.1.11].

---

## 2. System context

```mermaid
flowchart LR
    ORG["Organisers<br/>mission/boundary file at setup<br/>[BRIEF §3]"]
    OP["Single operator<br/>LOAD · START · ABORT · RECALL<br/>[BRIEF §3, §4, §8]"]
    GCS["Ground Control Station<br/>(one instance)<br/>[BRIEF §4]"]
    subgraph FLEET["Drone fleet  N >= 2  (P2 assumes N = 4)  AUW <= 25 kg  [BRIEF §2] [P2 Eq. 7]"]
      D1["Drone 1"]
      D2["Drone 2"]
      D3["Drone 3"]
      D4["Drone 4"]
    end
    AREA["Search area <= 10 ha<br/>up to 10 survivors<br/>[BRIEF Scenario, §1]"]
    PAD["12 ft x 12 ft launch/landing pad<br/>[BRIEF §7]"]

    ORG -- "mission file (format: OQ-22)" --> OP
    OP -- "4 permitted actions only" --> GCS
    GCS <-- "team-owned local RF only [BRIEF §5]<br/>telemetry + SNR feedback + video (OQ-14)" --> FLEET
    D1 <-. "inter-drone state broadcast [P2 §14.1] (topology OQ-28)" .-> D2
    FLEET -- "scout · geotag · drop kit" --> AREA
    FLEET -- "launch / land" --> PAD
```

**Actors and their limits:**
- **Organisers:** provide the mission file only at setup [BRIEF §3].
- **Setup crew:** at most 2 people for at most 300 s [BRIEF §3, §6].
- **Operator:** exactly 1, at the GCS. The only inputs are load mission file, start mission, safety abort and emergency recall [BRIEF §3, §4, §8]. Paper 2's GCS lists only three buttons [P2 §12.3.2]. Recall is added because the Brief requires it (OQ-16 covers what each button does).

---

## 3. Layered design

Four runtime layers plus a shared `common` layer. The layering rules are adapted from ADIAT:
- controllers do UI wiring only
- services hold logic and I/O
- helpers are cross-cutting only
- generated UI files are never hand-edited

[ADIAT-inspired: `ADIAT-standards` §2.1]

```mermaid
flowchart TB
  subgraph L4["Simulation & Test layer  (offline only)  [TEAM-BRIEF §6.1 D9]"]
    SIMCH["sim/channel<br/>block-Rayleigh, delayed SNR<br/>[P1 Table 13 ph.1-2] [P1 A7]"]
    SIMMIS["sim/mission<br/>multi-drone mission sim [P2 §1-§14]"]
    TESTS["tests/<br/>paper-table reproduction"]
  end
  subgraph L3["GCS layer  (one instance)  [BRIEF §4] [P2 §12, §15]"]
    GML["mission_loader"]
    GPL["preflight state machine [P2 §12.4]"]
    GAU["auction service [P2 §5.3/§7.3]"]
    GDW["DWVT partition service [P2 §5.1/§7.1]"]
    GSM["global state matrix + display predictor [P2 §12.1, §14.3]"]
    GUI["operator UI: 4 actions, map, status, survivors, delivery, progress, video [BRIEF §4]"]
    GVD["video receiver/decoder [P1 §5.1 D1-D5]"]
  end
  subgraph L2["Link & Video layer  [BRIEF §5] [P1] [P2 §12.1]"]
    RAD["radio abstraction (OQ-03, OQ-10)"]
    SCH["resource planner / priority mux [P2 §12.1] [P1 §3.1] (OQ-14, OQ-15)"]
    VENC["video encoder: transform, floor, refinement [P1 §5.1 E1-E7]"]
    VCTL["SNR predictor, margin rule, controller [P1 §C.2-C.3]"]
  end
  subgraph L1["Onboard Autonomy layer  (per drone)  [P2 §1-§14]"]
    PER["perception: ESKF, NDT, TSDF, detector, geotag [P2 §2.1, §4]"]
    CNF["survivor confirmation (Bayesian) [P2 §9.3]"]
    PLN["planning: BCD + Dubins, min-snap [P2 §5.2/§7.2, §8.1]"]
    CTL["control: NMPC + CBF + lexicographic fallback [P2 §8.2-§8.5]"]
    SHA["hybrid automaton / failsafes [P2 §9, §13] [BRIEF §8]"]
    PAY["payload release + hybrid mass reset [P2 §8.4, §9.5]"]
  end
  subgraph L0["common  (contracts, units, config registry, logging)  [ADIAT-inspired: contracts.py, algorithms.conf, LoggerService]"]
    C0["typed contracts · SI units · registry · logger · versioned mission log"]
  end
  L1 --- L2
  L2 --- L3
  L4 -. "drives L1-L3 through the same contracts" .-> L1
  L0 --- L1 & L2 & L3 & L4
```

**Layer responsibilities:**

| Layer | Owns | Must not | Tags |
|---|---|---|---|
| Onboard Autonomy | state estimation, perception, confirmation, local planning, control, failsafes, payload | depend on the GCS for safety; any failsafe must work with the link down | [P2 §9.1 Eq. 247–249] [BRIEF §8] |
| Link & Video | radio access, resource split per GoP, telemetry framing, Paper 1 encoder side, SNR-report handling | make mission decisions | [P1 §5, §C] [P2 §12.1] |
| GCS | mission ingest, preflight, DWVT partition, auction, global state, display, Paper 1 decoder | offer any operator control beyond the 4 Brief actions | [BRIEF §3–§4] [P2 §12.3.2, §14.3] |
| Simulation & Test | channel and mission simulators, reproduction of the papers' tables, scenario files | be imported by runtime code | [TEAM-BRIEF §6.1 D9] [P1 Table 13] |
| common | contracts, units, registry, logging, persistence | contain feature workflows | [ADIAT-inspired: `ADIAT-standards` §2.1 helpers rule] |

**Where computation runs** (all per [P2] unless marked):
- **DWVT partition and survivor auction:** the GCS [P2 §5.3, §7.1 "continuously recalculated by the GCS"].
- **Geotag and confirmation:** onboard [P2 §4.3, §9.3]. The topology for multi-drone fusion is OQ-28.
- **Coverage paths (BCD):** computed initially at the GCS during setup [P2 §12.4 step 2]. After that they are re-planned onboard from the drone's assigned cell; the split is not stated explicitly, so it is held behind the `CoveragePlanner` interface.
- **NMPC, CBF, ESKF:** onboard, 50 Hz / 200 Hz [P2 §8.2, §2.1].

---

## 4. Component diagram

```mermaid
flowchart LR
  subgraph DRONE["Drone i  (x N)"]
    IMU["IMU 200 Hz"] --> ESKF
    LID["LiDAR 10 Hz"] --> NDT["NDT scan match [P2 §4.2]"] --> ESKF
    GNSS["GNSS 10 Hz"] --> GATE["innovation gate (OQ-05d)"] --> ESKF["ES-EKF 15-dim error state [P2 §4.1]"]
    LID --> TSDF["TSDF terrain [P2 §4.2]"]
    CAM["RGB 30 Hz [P2 §2.1]"] --> DET["person detector (YOLOv8-pose weights) [P2 §4.3] [DATASET: yolov8n-pose.pt]"]
    DET --> GEO["ray cast into TSDF + covariance [P2 §4.3 Eq. 88-100]"]
    ESKF --> GEO
    TSDF --> GEO
    GEO --> BAY["Bayesian confirmation [P2 §9.3]"]
    ESKF --> SHA["hybrid automaton [P2 §9.1/§13.1]"]
    BAT["battery monitor"] --> SHA
    SHA --> PLAN["coverage + min-snap planner [P2 §7.2, §8.1]"]
    PLAN --> NMPC["NMPC 50 Hz + CBF [P2 §8.2-§8.3]"]
    ESKF --> NMPC
    NMPC --> FC["flight controller (OQ-29)"]
    PAYM["payload mechanism + HW trigger [P2 §6.4 Exc.4]"] --> NMPC
    CAM --> VENC["Paper 1 video encoder [P1 §5.1 E1-E7]"]
    VENC --> TX["radio TX (SDR-class, OQ-10)"]
    BAY --> TEL["telemetry framer"]
    SHA --> TEL
    TEL --> TX
    RXU["radio RX: commands, SNR report, assignments"] --> SHA
    RXU --> VCTL["SNR predictor + controller [P1 §C.2-§C.3]"] --> VENC
  end
  subgraph GCSB["GCS"]
    RXG["radio RX"] --> DEMUX["demux telemetry / video"]
    DEMUX --> GSTATE["global state matrix N x 13 [P2 §12.1]"]
    DEMUX --> VDEC["Paper 1 decoder: floor, Kalman SI, cond. mean [P1 §5.4]"]
    RXG --> SNRM["SNR estimate per drone [P1 §5.1 D1]"] --> FB["SNR report uplink [P1 A7]"]
    GSTATE --> AUC["auction (Hungarian) [P2 §7.3]"]
    GSTATE --> DWVT["DWVT + Lloyd [P2 §7.1]"]
    AUC --> CMD["assignment uplink"]
    DWVT --> CMD
    UI["operator UI [BRIEF §4]"] --> CMD
    GSTATE --> UI
    VDEC --> UI
    MIS["mission loader (OQ-22)"] --> DWVT
  end
  TX == "RF (local only)" ==> RXG
  FB == "RF" ==> RXU
  CMD == "RF" ==> RXU
```

---

## 5. Deployment view

| Node | Hardware (status) | Software | Tags |
|---|---|---|---|
| Drone i | Airframe about 4.8 kg loaded (TARGET from P2); IMU, LiDAR, RGB, GNSS (listed); optical flow + barometer (OQ-19); companion computer "Jetson-class" (TARGET); flight controller (OQ-29); SDR-class radio (OQ-10); payload mechanism (OQ-01, OQ-20) | `onboard/*`, `swarm/confirmation`, `link/*` (drone side), `video/encoder*` | [P2 §2.1, §8.2, §8.4] |
| GCS | Laptop/PC (spec unknown); radio front end (OQ-03) | `gcs/*`, `swarm/dwvt`, `swarm/auction`, `link/*` (ground side), `video/decoder*` | [P2 §12] [BRIEF §4] |
| Dev / CI | Developer PC, offline | `sim/*`, `tests/*` | [TEAM-BRIEF §6.2] |

---

## 6. Key flows and sequences

### 6(a) Setup: 5-minute window [BRIEF §3, §6] [P2 §12.4]

```mermaid
sequenceDiagram
    autonumber
    participant Crew as Setup crew (<=2) [BRIEF §6]
    participant OP as Operator
    participant GCS
    participant D as Drones 1..N
    Note over Crew,D: t = 0 s, setup clock starts. Mission file handed over now [BRIEF §3]
    Crew->>D: power on
    D->>D: boot, IMU/ESKF init, LiDAR init [P2 §12.4 step 1, 0-60 s]
    D-->>GCS: link up, heartbeat (local RF only) [BRIEF §5]
    OP->>GCS: LOAD MISSION FILE (permitted action 1) [BRIEF §3]
    GCS->>GCS: parse (OQ-22), validate polygon, build geofence B [P2 §12.3.3]
    GCS->>GCS: initial DWVT partition + BCD waypoints [P2 §12.4 step 2, 60-120 s]
    GCS-->>D: geofence B, launch zone Z, cells V_i, waypoint sets
    GCS->>D: self-test request: CBF consistency, ESC, payload interface [P2 §12.4 step 3, 120-180 s]
    D-->>GCS: self-test report
    D-->>GCS: ESKF tr(P_pos) <= eps_lidar, GNSS check [P2 §12.4 step 4, 180-240 s]
    GCS->>GCS: video link check: certified floor design exists for measured SNR [P1 Prop. 18] (OQ-24 if none)
    GCS-->>OP: READY (all gates green) or BLOCKED (named gate)
    OP->>GCS: START MISSION (permitted action 2) [BRIEF §3]
    GCS->>D: mission start, t_mission = 0
    Note over GCS,D: from here the operator may only ABORT or RECALL [BRIEF §3, §8]
```

- The preflight gate list is a declarative table in `gcs/preflight`, so a missing gate fails the setup visibly instead of being skipped silently [ADIAT-inspired: failure isolation, errors that name the operation].
- The time slots are Paper 2's [P2 §12.4]. Whether they fit our hardware is OPEN (boot time unmeasured).

### 6(b) Search sweep [BRIEF §3, §4] [P2 §5, §7, §8]

```mermaid
sequenceDiagram
    autonumber
    participant GCS
    participant Di as Drone i
    participant Dj as Drone j
    loop every partition update (GCS)
      GCS->>GCS: w_i(t) from battery + search flag (law: OQ-05c') [P2 Eq. 104/161]
      GCS->>GCS: weighted Voronoi V_i(t) [P2 Eq. 159], Lloyd centroid with density phi [P2 Eq. 165-168]
      GCS-->>Di: V_i(t) (hysteresis band applied) [P2 §5.4 Eq. 127]
    end
    Di->>Di: BCD of V_i into monotone sub-cells [P2 §7.2 Eq. 170]
    Di->>Di: sweep spacing <= W_FOV (1 - overlap), overlap in [0, 0.15] [P2 Eq. 171-173]
    Di->>Di: Dubins turns R >= v^2 / (g tan phi_max) [P2 Eq. 174-175]
    Di->>Di: min-snap B-spline QP (OSQP) [P2 §8.1 Eq. 188-198]
    loop 50 Hz
      Di->>Di: NMPC from x_hat_k, CBF inter-agent / terrain / geofence [P2 §8.2-§8.3]
    end
    loop state broadcast
      Di-->>Dj: state x_i (age guard, ghost buffer if stale) [P2 §14.1]
      Di-->>GCS: state x_i, battery, CBF status at ~20 Hz [P2 §12.1]
    end
    Di->>Di: v_ref = v_max tanh(kappa d_i) near cell boundary [P2 Eq. 129]
```

### 6(c) Detection → confirmation → geotag → auction → drop → return

```mermaid
sequenceDiagram
    autonumber
    participant Di as Drone i (detecting)
    participant Dj as Drone j
    participant GCS
    participant Dk as Drone k (assigned)
    participant OP as Operator display
    Di->>Di: detector on RGB frame -> bbox, keypoints, confidence (source-frame pixels) [P2 §4.3] [ADIAT-inspired: StreamDetection]
    Di->>Di: ray r_c = K^-1 u, root-find f(p_cam + s r_c) = 0 in TSDF (Brent/secant) [P2 Eq. 89-94]
    Di->>Di: p_surv = p + R(q)(R_cam p_cam + t_cam), Sigma_surv by Jacobians [P2 Eq. 96, 99]
    alt tr(Sigma_surv) exceeds gate (form: OQ-05k)
        Di->>Di: Low Confidence, re-observe [P2 Eq. 100]
    end
    Di->>Di: belief grid update P(S|D) [P2 Eq. 260], K >= 10 consistent frames [P2 Eq. 261-262]
    opt another drone observes within r_tol (topology OQ-28)
        Dj-->>Di: candidate evidence [P2 Eq. 263]
    end
    alt P(S|D_1:m) > 0.95  [P2 Eq. 264-265]
        Di-->>GCS: confirmed geotag p_surv, Sigma_surv
        Note over Di,GCS: provisional tags shown or not: OQ-05l
    end
    GCS->>GCS: cost matrix C (form: OQ-05c), infinite cost if payload gone [P2 Eq. 181]
    GCS->>GCS: Hungarian assignment [P2 Eq. 183]. Infeasible if survivors > kit-holders: OQ-01
    GCS-->>Dk: assignment (survivor j)
    GCS-->>OP: survivor tagged, assigned drone k [BRIEF §4]
    Dk->>Dk: chi_search = 0, leaves sweep, min-snap to intercept [P2 Eq. 185-186]
    GCS->>GCS: DWVT redistributes V_k [P2 §7.3]
    Dk->>Dk: terminal approach: IBVS within 3 m [P2 §12.2.2], constraints |p - p_surv| <= 0.5 m, |v| <= 0.3 m/s [P2 Eq. 235-236] (drop height and offset: OQ-20)
    Dk->>Dk: release, HW trigger, m -= 0.2 kg, T_ff -= 1.962 N, I reset, CG torque FF [P2 Eq. 231-234, 272]
    Dk-->>GCS: delivery event (survivor j, time, position)
    GCS-->>OP: kit delivered by drone k [BRIEF §4]
    Dk->>Dk: chi_search = 1, resume search, or RTH if no kit left (OQ-01)
    Note over Dk: at mission end or on a failsafe, RTH to pad with p_xy(t_land) in Z, v = 0 [P2 §12.3.1, §15.3.1]
```

### 6(d) Video: GoP encode → channel → decode → display [P1 §5.1]

Summary only. The full design is in [VIDEO_SUBSYSTEM.md](VIDEO_SUBSYSTEM.md).

```mermaid
sequenceDiagram
    autonumber
    participant CAM as Camera
    participant ENC as Drone encoder [P1 §5.1 E1-E7]
    participant CH as RF channel (block fading) [P1 §6.1]
    participant DEC as GCS decoder [P1 §5.1 D1-D5]
    participant UI as GCS video panel [BRIEF §4]
    participant FB as SNR feedback path [P1 A7]
    CAM->>ENC: G frames (one GoP, duration T_g = G / f_v) [P1 §3.1]
    ENC->>ENC: E1 orthonormal transform c = Theta x [P1 Def. 4]
    ENC->>ENC: E2 variance field (lambda, omega, a) as metadata [P1 A3, A5]
    FB-->>ENC: delayed noisy SNR report s_hat (g-d) [P1 A7]
    ENC->>ENC: pick certified floor design from grid G via margin rule + controller [P1 Thm 3, Eq. 40, Prop. 18]
    ENC->>ENC: E3-E4 floor: water level theta_F, quantise, entropy code, CRC, channel code (no past-GoP data) [P1 Def. 7, Prop. 7, Rem. 7]
    ENC->>ENC: E5-E6 residual and analogue gains [P1 Prop. 8/16], limiter back-off [P1 Lemma 6]
    ENC->>ENC: E7 orthogonal spreading, map to n_A uses, pilots [P1 §C.1]
    ENC->>CH: n_F floor uses + n_A analogue uses + pilots
    CH->>DEC: received symbols
    DEC->>DEC: D1 estimate channel, equalise (noise variances) [P1 §C.1]
    DEC->>DEC: D2 decode floor, success flag
    DEC->>DEC: D3 side info z = a * MC(x_hat prev) (decoder-side motion comp.) [P1 §5.1 D3]
    DEC->>DEC: D4 conditional mean [P1 Prop. 9 Eq. 20]. Fallback to floor-only on mismatch [P1 Rem. 5]
    DEC->>DEC: D5 inverse transform, update D_i(g) [P1 Lemma 3]
    DEC->>UI: frames + floor-decoded flag + model T_eq estimate
    DEC-->>FB: SNR estimate for next GoPs (uplink)
```

### 6(e) Failsafe paths [BRIEF §8] [P2 §9, §11.2, §13, §14]

All failsafes are **onboard-initiated**, or accepted onboard from the GCS. None needs the operator except abort and recall [BRIEF §3].

**(e1) Low battery → RTH** [BRIEF §8] [P2 §9.1 Eq. 245–246, §11.2.4]
```mermaid
sequenceDiagram
    participant D as Drone i
    participant GCS
    D->>D: guard E_i(t) <= E_req(p_i) + E_margin [P2 Eq. 245]
    D->>D: mode -> RTH, abort sweep, min-snap to pad Z [P2 Eq. 246]
    D-->>GCS: mode change event
    GCS->>GCS: w_i -> w_min, redistribute V_i [P2 §11.2.4]
    GCS-->>GCS: auction excludes drone i
    D->>D: land in Z with v = 0 [P2 §12.3.1] (pad sequencing: OQ-18)
```

**(e2) Loss of command-and-control link → RTH** [BRIEF §8] [P2 §9.1 Eq. 247–249, §14.1]
```mermaid
sequenceDiagram
    participant D as Drone i
    participant GCS
    Note over D,GCS: heartbeat stops
    D->>D: t_GCS > t_timeout (3 s [P2 Eq. 248] vs 5 s [P2 §14.1]: OQ-05b)
    D->>D: mode -> RTH, stop auction participation, LIO/LVIO navigation [P2 §9.1]
    D->>D: follow precomputed terrain-aware safe corridor to pad [P2 §9.1, §14.1]
    GCS->>GCS: drone i marked LINK LOST, display predictor dims after staleness [P2 §14.3] [ADIAT-inspired: HUD dims when stale]
```
Note: how the "precomputed safe corridor" is computed, and when, is not specified in [P2]. It is an interface slot in `onboard/planning` (OQ-05 family).

**(e3) Geofence** [BRIEF §7, §8] [P2 §8.3 Eq. 224–225, §11.1.3, §12.3.3]
```mermaid
flowchart LR
    A["Prevent: geofence CBF in NMPC (normal sign: OQ-05i)"] --> B{"NMPC-CBF feasible?"}
    B -- yes --> A
    B -- no --> C["lexicographic fallback (priority order: OQ-05j)"]
    C --> D{"breach detected? p_xy not in B"}
    D -- no --> A
    D -- yes --> E["BREACH FAILSAFE: action undefined in sources (OQ-17)"]
```

**(e4) Mission abort by the operator** [BRIEF §3, §8] [P2 §12.3.2]
```mermaid
sequenceDiagram
    participant OP as Operator
    participant GCS
    participant D as All drones
    OP->>GCS: SAFETY ABORT (permitted action 3)
    GCS->>D: ABORT broadcast (repeated until acked)
    D->>D: action on ABORT: RTH / land in place / hover (OQ-16)
    D-->>GCS: ack + mode
    GCS-->>OP: per-drone abort status
```

**(e5) Emergency recall by the operator** [BRIEF §3, §8]
```mermaid
sequenceDiagram
    participant OP as Operator
    participant GCS
    participant D as All drones
    OP->>GCS: EMERGENCY RECALL (permitted action 4)
    GCS->>D: RECALL broadcast (repeated until acked)
    D->>D: mode -> RTH, "recall all drones" [BRIEF §8], exact semantics OQ-16
    D-->>GCS: ack, then landing reports
```

**(e6) Paper 2 degraded modes**, kept separate from the Brief's minimum set [P2 §9.2, §11.2, §13.2, §14]

| Guard | Source | Reaction | Open |
|---|---|---|---|
| tr(P_pos) > ε_lidar (0.5 m² representative) | [P2 §13.2.1] | gate LiDAR (R → ∞); reduce v_max; widen terrain margin | velocity law 05g; margin units 05e; fallback sensors OQ-19 |
| GNSS innovation fails gate | [P2 §9.2, §13.2.2] | reject GNSS; LIO/VIO; GCS freezes this drone's cell; auction suspended for it | gate form 05d |
| tr(P_pos) > ε_critical and GPS gated | [P2 §13.2.3] | EMERGENCY_HOVER; w_i → 0; resume when tr(P_pos) ≤ ε_lidar | mode-set membership 05a |
| neighbour state age > 200 ms | [P2 §14.1] | ghost buffer added to d_safe | formula 05h |
| NMPC-CBF infeasible | [P2 §8.5, §9.4, §14.2] | disturbance observer feedforward, then lexicographic relaxation, then safe state (hover / emergency land) | priority order 05j |
| payload jam / asymmetric drop | [P2 §3.4.3, §9.5] | CG torque feedforward; tracking relaxed before safety | — |

**Mode automaton.** Paper 2 gives two incompatible mode sets (OQ-05a). `onboard/automaton` is therefore built as a **table-driven** automaton: modes, guards, reset maps and priorities are loaded from a registered mode table [ADIAT-inspired: config-driven registry]. Both Paper 2 variants are encoded as candidate tables. Neither is the default until you choose.

---

## 7. Mission-level state (GCS view)

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> MISSION_LOADED: LOAD MISSION FILE [BRIEF §3]
    MISSION_LOADED --> PREFLIGHT: auto [P2 §12.4]
    PREFLIGHT --> READY: all gates pass
    PREFLIGHT --> BLOCKED: named gate fails
    BLOCKED --> PREFLIGHT: crew fixes during setup (<=300 s)
    READY --> RUNNING: START MISSION [BRIEF §3]
    RUNNING --> RECALLING: EMERGENCY RECALL [BRIEF §8]
    RUNNING --> ABORTING: SAFETY ABORT [BRIEF §8] (semantics OQ-16)
    RUNNING --> RETURNING: all reachable survivors serviced or coverage complete [BRIEF §3]
    RETURNING --> COMPLETE: all drones landed in Z [BRIEF §7]
    RECALLING --> COMPLETE
    ABORTING --> COMPLETE
    COMPLETE --> [*]
```
- The display shows mission elapsed time against the 30-minute cap [BRIEF §3], plus Paper 2's TARGET of 11 min (OQ-05f).
- The criterion for "coverage complete" (all cells swept once at the chosen overlap) is derived from [P2 §7.2]. Whether it should also require "no confirmed survivor unserviced" depends on OQ-01.

---

## 8. Cross-cutting design

| Concern | Decision | Tags |
|---|---|---|
| Contracts | One normalised result shape per stream type (`ProcessResult[T]`) with `error_message`. Adapters wrap any component that does not natively produce it. Orchestrators never crash on a bad item | [ADIAT-inspired: `streaming/contracts.py`, `adapters.py`, `StreamAnalyzeService.process_frame` try/except] |
| Pixel coordinates | Detections are always in **source-frame pixels**, top-left origin. Consumers never need to know the processing resolution | [ADIAT-inspired: `StreamDetection` docstring] |
| Registry | JSON registry maps component names to module, class and platforms (`onboard` / `gcs` / `sim`). No hard-coded routing tables. Unknown names fail loudly | [ADIAT-inspired: `algorithms.conf`, ADIAT-standards §2.3] |
| Units and frames | SI throughout; local inertial frame F_I (ENU assumed, pending OQ-22 for the geodetic datum); body frame F_B; quaternion body→inertial | [P2 §1.2 Eq. 8–9] |
| Time | Every message carries a source timestamp. GCS fuses by timestamp, with interpolation for display only | [P2 §12.1, §14.3] |
| Logging | One central logger service. Errors name the component, operation and input (drone id, GoP index, file). No bare `print` in runtime paths | [ADIAT-inspired: `LoggerService`, ADIAT-standards §2.4] |
| Persistence | Versioned, backward-compatible mission log: states, detections, tags, assignments, deliveries, video statistics. Used for replay in `sim/` | [ADIAT-inspired: versioned result files] [TEAM-BRIEF §6.1 D10] |
| Low-latency capture | Drop stale frames; frame-rate cap; one worker per pipeline; thread-safe config updates. Applies to the detector input and the video encoder input | [ADIAT-inspired: StreamAnalyze capture pattern] |
| Detection post-filters | Temporal voting, NMS and clustering are **only** what Paper 2's K-frame consistency and r_tol fusion require. Extra filters (aspect ratio, region masks) are not adopted unless you ask | [P2 Eq. 261–263] [ADIAT-inspired: post-filters] |
| Tiled detection | ADIAT's tiled ONNX inference with provider fallback is held as a detector **implementation option** behind the detector interface. Not required by Paper 2 | [ADIAT-inspired: `AIPersonDetectorService`] |
| Batch/offline processing | Worker pool with per-item timeout, failure isolation and fast cancel, for `sim/` sweeps and certificate sampling | [ADIAT-inspired: AnalyzeService] |
| Tests | Deterministic (fixed seeds), offline, no network. Lint gate. Traceability check fails if a requirement has no module or test (Phase 2) | [ADIAT-inspired: ADIAT-standards tests] [TEAM-BRIEF §8 Phase 2] |
| Licensing | No ADIAT source copied; patterns re-implemented clean-room. YOLOv8 weights licence flagged (OQ-08a) | [TEAM-BRIEF §4] |

---

## 9. Budgets

### 9.1 Weight [BRIEF §2] (OQ-07)
| Item | Per drone | Source | Status |
|---|---|---|---|
| All-up loaded mass | 4.8 kg | [P2 Eq. 227] | TARGET |
| Payload | 0.2 kg | [BRIEF §2] [P2 Eq. 229] | REQUIRED |
| Airframe, motors, ESCs, battery | — | none | OPEN |
| LiDAR, RGB, IMU, GNSS | — | [P2 §2.1] lists them, no mass | OPEN |
| Companion computer (Jetson-class) | — | [P2 §10.2] | OPEN |
| SDR-class radio for Paper 1 | — | inferred (OQ-10) | OPEN |
| Optical flow + barometer | — | [P2 §13.2] (OQ-19) | OPEN |
| **Fleet total (N = 4)** | **19.2 kg ≤ 25 kg** | arithmetic on [P2 Eq. 227] | TARGET; 5.8 kg margin, unallocated |

### 9.2 Time [BRIEF §3] [P2 §12.2.3]
- Hard cap: 30 min flight [BRIEF §3].
- Ideal coverage lower bound: T ≥ A / (N·W_FOV·v_sweep), with A = 100 000 m² [P2 §12.2.3]. Not evaluable (OQ-21).
- Paper 2's targets: ≤ 11 min design, 15 min objective (TARGET, OQ-05f).
- Setup: ≤ 300 s, using the Paper 2 slot plan [P2 §12.4] (TARGET).

### 9.3 Link
- Per drone, per GoP: n = (1 − δ)·W_i·T_g channel uses, split into pilots, floor n_F, refinement n_A, and telemetry (placement OQ-14) [P1 §3.1, §6.5].
- Telemetry demand [P2 §12.1]: state at 20 Hz per drone, map at 1 Hz. Packet sizes are not given in the sources, so the bit rate is OPEN.
- SNR feedback: at least one report per GoP per drone, uplink [P1 A7, Thm 3].

---

## 10. Language and tooling [TEAM-BRIEF §6.2]

| Part | Language | Why | Tags |
|---|---|---|---|
| Paper 1 maths, certificates, channel simulator, mission simulator, GCS logic, tests | **Python 3** with numpy/scipy (version: OQ-26) | Matches the paper's own reference approach (closed forms + Monte Carlo) and the standard scientific stack. Fast to verify against tables | [TEAM-BRIEF §6.2] [P1 §A] |
| NMPC 50 Hz with RK4, SQP-RTI | Generated C via acados/CasADi, called through a Python interface in simulation | P2 names CasADi/acados. Python alone cannot be assumed to meet 20 ms; the 8–12 ms claim is unvalidated | [P2 §8.2, §10.2] |
| ESKF 200 Hz IMU propagation, NDT, TSDF | C++ (or an existing compiled library) behind the `Estimator` / `TerrainMap` interfaces | Rate and point-cloud volume. Python reference used only in simulation | [P2 §2.1, §4.2] |
| Video baseband: spreading, mapping, pilots, limiter at W Msym/s; floor channel code | Compiled / SDR toolchain (choice tied to OQ-03, OQ-10, OQ-23) | Real-time sample rates in the MHz range. Python implements the *reference* maths only | [P1 §5.1 E7, §B.1, §C.1, §6.6] |
| Detector inference | ONNX / TensorRT on the companion computer behind the `PersonDetector` interface | Model is YOLOv8-pose [DATASET]; runtime kept swappable | [P2 §4.3] [ADIAT-inspired: provider fallback] |
| GCS UI | Python (desktop UI toolkit TBD in Phase 2; no web/cloud dependency) | Single local operator station | [BRIEF §4, §5] |

Rule: every real-time component sits behind a Protocol in `INTERFACES.md`, so the Python reference and the compiled implementation are interchangeable and tested against the same contract tests [TEAM-BRIEF §6.2].

---

## 11. What is proved, simulated, or only targeted (headline)

| Claim | Level | Assumptions / caveat | Tag |
|---|---|---|---|
| Floor holds: P[T_eq < T_min] ≤ ε_F for every GoP | PROVED (conditional) | A1–A6; i.i.d. Gaussian codebook; independent Rayleigh blocks; perfect CSI. Clipping and estimation error **not** in the certificate | [P1 Thm 2, §8] |
| Same, with delayed SNR feedback and any controller trajectory | PROVED (conditional) | adds A7–A8; A8 checked at one design point only | [P1 Thm 3–4, Prop. 18] |
| Floor needs L ≥ 4; floor share 52 / 30 / 22 / 17 % for L = 4 / 8 / 16 / 64 | SIMULATED | W = 5 MHz, T_g = 8/30 s, 10 dB, ε = 1e-3 | [P1 Cor. 6, Table 9] |
| Efficiency η ≈ 0.65–0.66; 3.3–3.5 dB below zero-latency H.264 | SIMULATED (one clip) | AWGN, oracle SNR, no fading, one noise draw | [P1 Table 11, 23] |
| Inter-agent / terrain / geofence safety | PROVED (conditional) | NMPC-CBF feasible; valid model and estimates | [P2 §6.3, §8.3, §11.1] |
| NMPC 8–12 ms on Jetson Orin NX | TARGET | "requires experimental validation" | [P2 §10.2] |
| Drop accuracy 0.3 m | TARGET | "design target unless independently demonstrated" | [P2 §12.2.2] |
| Mission ≤ 11 min | TARGET | ideal bound plus overheads | [P2 §12.2.3] |
| All Brief rules | REQUIRED | verified only by future tests | [BRIEF §1–§8] |
