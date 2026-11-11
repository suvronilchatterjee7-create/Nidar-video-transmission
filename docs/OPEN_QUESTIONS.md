# Open Questions — NIDAR RescueSwarm

Status: Phase 1 draft · Branch `docs/phase1-architecture` · Owner of every decision below: **the team lead (you)**.

**Rule** [TEAM-BRIEF §0.4]: when the sources disagree or say nothing, the architecture does **not** pick a side. Each item below is either:
- left as a named parameter with no default, or
- shown as alternatives behind one interface.

Each item says what it blocks.

Status values:
- **OPEN**: needs your decision.
- **BLOCKED-ON-INPUT**: needs data or hardware facts from you.
- **ANSWERED**: decided. The decision is quoted.

Tag key: see [ARCHITECTURE.md §0](ARCHITECTURE.md#0-conventions).

---

## A. Questions raised in the team brief (§7)

### OQ-01 · Kit count vs survivor count — OPEN
- **Sources:** [BRIEF Scenario, §1] says up to 10 survivors, and "deliver a survivor kit to each identified survivor". [P2 §1.3, §8.4] assumes one 200 g kit per drone. [P2 §1.2 Eq. 7] sets N = 4.
- **The problem:** Paper 2 can deliver at most 4 kits. Its assignment problem also requires Σᵢ aᵢⱼ = 1 for every survivor j [P2 Eq. 124 / Eq. 183]. When there are more unserviced survivors than drones still holding a kit, that problem is **infeasible**, not just short of kits. Paper 2 also returns a drone to search after it drops its only kit [P2 §7.3, Eq. 187], but that drone can no longer deliver.
- **Blocks:**
  - the payload mechanism design
  - the weight budget (OQ-07)
  - the auction formulation (`swarm/auction`)
  - mission timing, if drones must land to reload (forbidden by [BRIEF §3]: no swap after start)
- **Options visible in the sources:** none resolve this. Possible directions (not chosen): several kits per drone; more drones; accept partial delivery.

### OQ-02 · Which video method feeds the GCS live video — OPEN
- **Sources:** [P2 §12.1 / §15.1.1] says "H.265 hardware encoding with ROI", with bitrate boosted for the drone that has a candidate survivor. [P1 §5] specifies the hybrid floor + analogue refinement scheme. [TEAM-BRIEF §6.1 D5] requires the Paper 1 scheme.
- **Interaction:** the Paper 1 refinement layer sends continuous-amplitude symbols, so it cannot travel as packets through Paper 2's bit-rate scheduler (see OQ-14).
- **Architecture stance:** the GCS video panel reads decoded frames through a single `VideoSource` contract ([INTERFACES.md §7](INTERFACES.md#7-video-contracts)). The Paper 1 pipeline is designed in depth. The H.265 path is listed as a Paper 2 alternative and not designed.
- **Blocks:** whether `video/` also needs an H.265 adapter. It also determines the radio choice (OQ-03, OQ-10).
- **New evidence (Phase 4, docs/VIDEO_PIPELINE.md §6):** with ideal code and oracle rate, zero-latency H.264 beats our Paper 1 implementation by 7.5–11 dB (synthetic scene) and 18–27 dB (testsrc2). This is on low-entropy test content. The regime the paper argues for (fading without timely feedback) is still untested.

### OQ-03 · Radio / physical link — BLOCKED-ON-INPUT
- **Sources:** [P2 §12.1] gives "900 MHz LoRa or 5.8 GHz digital" and an example B_RF = 2 Mbps. [P1 §6.4 Cor. 6] needs L ≥ 4 independent fading blocks per GoP (group of pictures). [P1 §C.2 Thm 3, Table 19] needs timely SNR feedback. [P1 Table 9] assumes W = 5 MHz at 10 dB.
- **Facts needed from you:**
  - band
  - complex symbol rate W per drone
  - TX power and antenna count (diversity)
  - mean SNR range over a 10 ha site
  - large-scale correlation time and σ_s
  - SNR report noise σ_m
  - uplink path and delay d for SNR feedback
  - whether I/Q-level access exists (SDR)
- **Note:** LoRa cannot carry 2–10 Mbps video. A 2 Mbps link cannot carry four "HD" streams [P2 §12.1 text itself].
- **Blocks:** every numeric parameter of `video/` and `link/` in [VIDEO_SUBSYSTEM.md §12](VIDEO_SUBSYSTEM.md#12-parameter-register).

### OQ-04 · Follow Paper 1 even though its pilot lost to H.264 — ANSWERED
- **Decision (you, Phase 0):** "follow the papers strictly; record the risk; don't override."
- **Evidence:** [P1 §D.5 H5, Table 23] reports −3.3 to −3.5 dB vs zero-latency H.264, and about −7 dB vs the default preset.
- **Recorded as:** RISK-V02 in [RISK_REGISTER.md](RISK_REGISTER.md).

### OQ-05 · Paper 2 internal inconsistencies — OPEN (one decision per sub-item)

| ID | Topic | Variant A | Variant B (and C) | Blocks |
|---|---|---|---|---|
| 05a | Discrete mode set | {SEARCH, DELIVER, DEGRADED, RTH, EMERGENCY_LAND} [P2 §9.1, §11.2] | {NOMINAL, DEGRADED_LIDAR, DEGRADED_GPS, COMMS_LOSS, EMERGENCY} [P2 §13.1]. Also EMERGENCY_HOVER [P2 §13.2.3], which is in neither set | `onboard/automaton` |
| 05b | Comms timeouts | GCS heartbeat t_timeout = 3 s → RTH [P2 §9.1 Eq. 248] | t_critical = 5 s → RTH [P2 §14.1]. (The 200 ms drone-to-drone state-age guard [P2 §14.1] is a separate guard, the ghost buffer, and is not in conflict) | C2-loss failsafe |
| 05c | Auction cost | Eq. 38 [P2 §2.4]: time + β/E + γ(1−χ_payload) | Eq. 120 / 179 [P2 §5.3, §7.3]: time + α₁(1−E/E_max) + α₂(1−χ) + α₃·area-abandonment | `swarm/auction` |
| 05c′ | DWVT weight law | multiplicative w⁺ = 0.5·w⁻ on drop or battery < 30 % [P2 Eq. 29–30] | w = α₁E/E_max + α₂χ_search, with w_min floor [P2 Eq. 104, 107, 161, 163] | `swarm/dwvt` |
| 05d | GNSS gate | per-axis 3σ for N consecutive epochs [P2 §9.2 Eq. 256] | single-epoch χ²(3, 0.999) = 16.27 [P2 §13.2.2] | `onboard/estimation` |
| 05e | Terrain margin under LiDAR degradation | z_min + tr(P_pos), mixing m and m² [P2 §13.2.1] | z_min + z_unc, with z_unc a length [P2 §11.2.2, which corrects it] | terrain CBF |
| 05f | Mission time target | ≤ 11 min design / 15 min objective [P2 §12.2.3, §15.2.3] | Brief cap: 30 min flight [BRIEF §3] | timing budget, energy margin |
| 05g | Speed limit when LiDAR is degraded | 0.5·v_max [P2 Eq. 65, 151] | v_max·exp(−κ tr P) [P2 Eq. 252]; and v_max·exp(−κ_v(tr P − ε_lidar)) [P2 §13.2.1] | `onboard/automaton` |
| 05h | Ghost buffer | d_safe + k·Δt [P2 Eq. 63, 149] | d_safe + v_max·Δt + ½a_max·Δt² [P2 §14.1] | inter-agent CBF |
| 05i | Geofence normal direction | outward normals n_k [P2 §8.3 Eq. 224] | inward normals [P2 §11.1.3] | sign convention in `onboard/control/cbf` |
| 05j | Constraint priority | geofence is hard and above actuator limits [P2 §8.4 Table 1] | geofence is soft, below actuator limits [P2 §9.4, §14.2 Table 2] | lexicographic fallback; see also OQ-17 |
| 05k | Geotag confidence gate | flag if tr Σ > ε_tag [P2 Eq. 100] | promote if tr Σ ≤ ε_tag² [P2 §12.2.1, §15.2.1] | units of ε_tag |
| 05l | When a geotag reaches the GCS | "immediately broadcast" [P2 §2.1] | only after P > 0.95 confirmation [P2 §9.3] | GCS display of provisional tags ([BRIEF §4] requires "tagged location of detected survivors") |
| 05m | Sweep speed formula | v_sweep = W_FOV(1−overlap)/(t_int·f_frame) [P2 §12.2.3] gives metres, not m/s | — | coverage-time estimate |

### OQ-06 · Full rulebook — ANSWERED (with consequence)
- **Decision:** the 3-page Brief is the only rulebook available (you re-shared it in Phase 0).
- **Consequence:** these items cited by Paper 2 are **unverified** and are not used as requirements:
  - rule numbers 8.4, 8.13, 8.14, 8.16, 8.17, 8.19
  - Annexures 3 and 5
  - "25 marks per geotag" [P2 §2.1, §4.3]
- **Brief silences carried forward:** scoring weights, geotag tolerance, "near survivor" radius, altitude and speed limits, dummy appearance.

### OQ-07 · Weight budget — BLOCKED-ON-INPUT
- **Sources:** [BRIEF §2] caps the fleet at 25 kg. [P2 §8.4 Eq. 227] gives 4.8 kg per drone, so 4 × 4.8 = 19.2 kg. No breakdown is given.
- **Also not in Paper 2's mass:**
  - the SDR/radio front end that Paper 1 implies (OQ-10)
  - the optical-flow and barometer sensors (OQ-19)
  - any extra kits (OQ-01)
- **Blocks:** fleet size, kits per drone, sensor suite. Template in [ARCHITECTURE.md §9](ARCHITECTURE.md#9-budgets).

### OQ-08 · Prior dataset and website — ANSWERED, with follow-ups
- **Answer:** the repository you provided at `github.com/suvronilchatterjee7-create/NIDAR` contains:
  - `RescueSwarm_PoseSet_v0.1`: 300 images, 519 people, COCO-17 keypoints, posture and altitude-band labels
  - `yolov8n-pose.pt`
  - a showcase website
- **How the architecture uses them:** the dataset is the detector's training and evaluation source for D4. The website is not used at runtime.
- **Follow-up OQ-08a (licence), OPEN:** `yolov8n-pose.pt` is, to my knowledge, Ultralytics AGPL-3.0. Shipping it onboard may oblige us to publish our onboard source. Separately, 7 images are CC BY-SA 2.0. Accept, or plan a replacement? (RISK-L01)
- **Follow-up OQ-08b (suitability):** see OQ-25.

### OQ-09 · Number of simultaneous live feeds on the GCS — OPEN
- **Sources:** [BRIEF §4] says only "Live video feed display", which could mean one feed or one per drone. [P2 §12.1] mentions "four HD video streams" and dynamic boosting. [P1] is a single point-to-point link only.
- **Blocks:** the multiple-access design (OQ-11) and the GCS video panel layout.

---

## B. New questions found in Phase 0 / Phase 1

### OQ-10 · Paper 1 needs an SDR-class radio — OPEN
- **My inference (labelled as such):** the refinement layer sends continuous-amplitude symbols sᵢ = gᵢrᵢ [P1 Prop. 8]. It also needs a hard limiter with back-off [P1 §B.1], pilot-based estimation [P1 §C.1] and orthogonal spreading [P1 §5.1 E7]. All of this needs direct control of baseband I/Q samples. Off-the-shelf packet video links do not expose that.
- **Impact:** an SDR (or equivalent) at every drone and at the GCS, which adds weight and power (OQ-07).
- **Decision needed:** confirm SDR-class hardware is acceptable, or decide OQ-02 against Paper 1.

### OQ-11 · Several drones sharing the video channel — OPEN
- **Sources:** Paper 1 analyses one link [P1 §3.1]. With 4 drones transmitting, the band W must be shared somehow (frequency, time, or separate channels). Nothing in the sources says how.
- **Consequence:** a narrower W per drone raises the floor's share of channel uses. At 10 dB, [P1 Table 10] gives 11.6 % at 5 MHz but 58.1 % at 1 MHz.
- **Blocks:** W_i per drone and G (frames per GoP).

### OQ-12 · Video format and what "2 Mbps" means — OPEN
- **Sources:** T_min = 2 Mbps is an *equivalent* throughput on a reference scale: 720p25 at equal bits per sample [P1 §7.1, §D.2]. In the pilot, the credited floor was 489 kbit/s at 640×352, 25 fps [P1 Table 21].
- **Decisions needed:**
  - camera stream resolution and fps for the downlink
  - G (frames per GoP)
  - whether T_min is scaled to 720p25 as the paper does
- **Blocks:** k = G·N, T_g, B_F, and all sizing tables.

### OQ-13 · Latency budget L_max and floor outage ε_F — OPEN
- **Sources:** both are symbols only [P1 Problem 2 (L), (F)].
- **What ε_F means for us:** by [P1 Cor. 7] at T_g = 8/30 s, the expected floor violations per 30-minute flight per feed are about 1800/26.7 ≈ 67 at ε = 1e-2, about 6.7 at 1e-3, and about 0.7 at 1e-4. These figures assume independence across GoPs; slow fading clusters the violations [P1 Cor. 7].
- **Also open:** how the chance budget splits, ε_F = ε + ε_core + ε_q [P1 Thm 3–4].

### OQ-14 · Video and telemetry on the same link — OPEN
- **Sources:** [P2 §12.1] uses one bit-rate budget B_RF, with weights 10/5/1 for state/map/video. [P1 §3.1] budgets *channel uses* per GoP, n = (1−δ)W·T_g, with δ = "pilots and protocol overhead".
- **Undecided:**
  - one shared radio or a separate telemetry radio
  - if shared, does telemetry sit inside δ, or in a slice outside W?
  - the SNR feedback uplink (needed every GoP, [P1 A7]) must ride on the telemetry path
- **Architecture stance:** `link/` exposes a `ResourcePlan` per GoP. The telemetry slice is a named parameter with no default.

### OQ-15 · Paper 2's rate allocation is a degenerate linear programme — OPEN
- **Source:** [P2 §12.1 / §15.1.1] maximises Σ wᵀRᵢ subject only to Σ Rᵢ ≤ B_RF, with w = (10, 5, 1).
- **Problem:** a linear objective under only a sum constraint puts *all* capacity on the highest weight (state telemetry), so video and map get 0.
- **Decision needed:** minimum and maximum rate per stream, or another formulation. Neither source gives one.

### OQ-16 · Abort vs recall — OPEN
- **Sources:** [BRIEF §3, §4, §8] requires both a "safety abort" and an "emergency recall", and "abort the mission and recall all drones". [P2 §12.3.2, §14.3, §15.3.2] gives the GCS only [LOAD MISSION FILE, START MISSION, EMERGENCY SAFETY ABORT]. That is an omission, not a contradiction, so `gcs/` exposes all four Brief actions.
- **Still open — what each button does physically:**
  - recall → RTH all? (likely, by wording)
  - abort → RTH, land in place, or hover?
  - can an abort be followed by a recall?

### OQ-17 · Geofence breach failsafe and the "soft" geofence — OPEN
- **Sources:** [BRIEF §7, §8] says drones operate only inside the boundary, and requires a *geofence-breach failsafe*. Paper 2 only *prevents* a breach with a CBF [P2 §8.3, §11.1.3]. Its fallback lets the geofence become **soft** to avoid collision [P2 §9.4, §14.2.2]. It defines no reaction *after* a breach.
- **Decisions needed:**
  - action after a breach (RTH? hover-and-re-enter? land?)
  - whether the soft-geofence relaxation is acceptable under the Brief (links to 05j)

### OQ-18 · Launch pad size vs d_safe — OPEN
- **Sources:** the pad is 12 ft × 12 ft ≈ 3.66 m, and no part of any drone may be outside it during launch or landing [BRIEF §7]. Paper 2 has d_safe = 3.0 m between drones [P2 §8.3 Eq. 216], enforced as a hard CBF.
- **Why they clash:** with drone span D, the drone centres must lie inside a (3.66 − D) square. Four centres pairwise ≥ 3 m apart need a side of ≥ 3 m, so D ≤ 0.66 m. A 4.8 kg airframe is very likely wider than that.
- **Decision needed:** sequenced launch/landing (IDEA-11), an exemption on the pad, or a smaller d_safe.

### OQ-19 · Sensors used but not listed — OPEN
- **Source:** the degraded-mode fallback uses "optical-flow/IMU" and a "barometric altitude" [P2 §13.2.1, §13.2.3]. The sensor suite lists only IMU, LiDAR, RGB and GNSS [P2 §2.1].
- **Decision needed:** add optical flow and a barometer (weight, OQ-07), or drop those fallbacks.

### OQ-20 · Drop height, "near survivor", and real people — OPEN
- **Sources:**
  - [BRIEF §1] says "near" and doesn't define it; survivors may be real humans.
  - [P2 Eq. 235–236] sets a terminal constraint of ‖p − p_surv‖ ≤ 0.5 m and ‖v‖ ≤ 0.3 m/s.
  - [P2 §12.2.2] gives a 0.3 m IBVS target.
  - [P2 Eq. 237–238] gives free-fall drift.
  - z_min = 3 m terrain clearance [P2 §1.1].
- **Undefined:** drop height, the horizontal offset from a person (dropping 200 g *onto* a real person is a safety hazard), and whether 0.5 m or 0.3 m is the target.
- **Blocks:** delivery terminal constraints and the payload mechanism.

### OQ-21 · Camera, altitude and speed (coverage time) — BLOCKED-ON-INPUT
- **Source:** T ≥ 100 000 m² / (4·W_FOV·v_sweep) [P2 §12.2.3], with W_FOV = 2·z_rel·tan(FOV_h/2) [P2 Eq. 171].
- **Facts needed from you:** FOV, resolution, search altitude z_search, v_sweep. Also the detector's ground sampling needs: the dataset gives altitude *bands* only.

### OQ-22 · Mission file format — BLOCKED-ON-INPUT
- **Source:** [BRIEF §3] says only "mission file/boundary file". Format, coordinate system, and whether the launch zone is included are all unknown.
- **Architecture stance:** a parser registry in `gcs/mission_loader` behind a `MissionFileParser` protocol ([INTERFACES.md §2](INTERFACES.md#2-mission-file)), with no format assumed.

### OQ-23 · Floor channel-code choice — OPEN
- **Sources:**
  - [P1 §6.6] gives a long monolithic code vs a rateless code (needs stop feedback).
  - [P1 Prop. 13]: splitting into K segments multiplies the dispersion overhead about 10× (K = 64: 4.95 % vs 0.47 %).
  - Practical LDPC blocks are about 10⁴ bits [P1 §6.6].
- **Decision needed:** which code family, given what the radio and compute support.

### OQ-24 · Behaviour when the floor is infeasible — OPEN (current behaviour: hold last picture + flag)
- **Sources:** [P1 Table 23] reports "infeasible" at 2 and 4 dB, and with L ≤ 2 [P1 Table 9]. [P1 Table 13 phase 6] lists "analogue fallback below floor feasibility" as future work.
- **Decision needed:** what the GCS shows and the drone sends when no certified design fits. Options: refinement-only, a "no guaranteed video" banner, or no video.

### OQ-25 · Detector confidence vs Paper 2's Bayesian update — OPEN
- **Source:** [P2 Eq. 260] uses the CNN confidence directly as a likelihood, with K = 10 frames treated as independent evidence [P2 Eq. 262].
- **Dataset limits** (`RescueSwarm_PoseSet_v0.1`):
  - 63.8 % of labels are unreviewed model pre-labels
  - no flood or water scenes
  - no dummies
  - altitude given as bands only
- **Result:** calibration cannot be validated, and consecutive frames are correlated, which risks overconfidence. Recorded as RISK-S04 (Paper 2's Bayesian confirmation, Eq. 260, is unvalidated).

### OQ-26 · Python toolchain — PROVISIONAL (used in Phase 2; change it if you prefer)
- **Machine:** 3.15 (default), 3.14, 3.11.
- **Phase 2 used the proposal:** a project `.venv` on Python 3.11.9 with numpy 1.26.4, pytest 8.3.3 and ruff 0.6.9 (lint), pinned in `pyproject.toml`.
- **scipy was not needed in Phase 3.** The standard library and numpy cover Q⁻¹, erfc and quadrature, so no new dependency was added.

### OQ-27 · Who runs the auction — OPEN (minor)
- **Sources:** [P2 §5.3, §7.3] says it is centralised at the GCS. [P2 §2.4] says "for a decentralized swarm architecture, distributed consensus-based auction algorithms may alternatively be employed".
- **Why it matters:** during a GCS link loss the auction is suspended [P2 §13.2.2], and comms loss triggers RTH [P2 §9.1]. Centralised is the main text, so the architecture uses it. The decentralised path is not designed unless you ask.

### OQ-28 · Communication topology and where multi-drone fusion runs — OPEN
- **Sources:**
  - [P2 §3.4, §14.1] describes drone-to-drone state broadcast over a "local RF mesh".
  - [P2 §9.3] describes multi-drone evidence fusion *before* promotion.
  - [P2 §9.3] also says the geotag goes to the GCS only *after* confirmation.
- **Implication:** candidates must be shared drone-to-drone (mesh), or fused at the GCS (star), which contradicts "only after". Same family as 05l.

### OQ-29 · Flight controller vs companion computer split — OPEN
- **Sources:** [P2 §6.4 Exc. 4] mentions a "companion computer" receiving the payload trigger. The flight controller (autopilot) is never specified. [P2 §8.2] puts NMPC at 50 Hz on the companion computer.
- **Decision needed:** which failsafes ([BRIEF §8]) are enforced by the autopilot itself vs the companion computer, for independence when the companion computer fails.

### OQ-30 · Table 9 transcription check — RESOLVED (Phase 3)
- **Resolution:** the "Certified" column belongs to rows L = 4 / 8 / 16 / 64 (0.521 / 0.298 / 0.223 / 0.171), as Cor. 6 states. It is shifted one row down in the text extraction. Our certified search gives 0.515 / 0.296 / 0.221 / 0.170 (see REPRODUCTION_P1.md).

*Original question:*
- **Issue:** text extraction misaligns the "Certified" column of [P1 Table 9]. Phase 1 uses the unambiguous values in [P1 Cor. 6] (52 / 30 / 22 / 17 % for L = 4 / 8 / 16 / 64).
- **Phase 3 action:** re-check against the rendered PDF.

### OQ-31 · Live-video purpose vs detection — OPEN (confirm)
- **Reading of the sources:** detection runs onboard on raw camera frames [P2 §2.1, §4.3]. The GCS video is for operator display [BRIEF §4]. So Paper 1 video quality does **not** gate survivor detection or scoring.
- **Please confirm.** If GCS-side detection on the received video were wanted, D4 and D5 would be coupled and Paper 1's −3.3 dB result (RISK-V02) would become mission-critical.

### OQ-32 · Mismatch detector for the floor fallback — OPEN
- **Source:** [P1 Rem. 5] says the decoder "falls back to the floor reconstruction" if it *detects* mismatch, but not how.
- **Implemented (Phase 4):** the normalised innovation of the analogue observations, the larger of "all active" and "side-information-using" coefficients.
  - Clean video gives ≈ 1.0, so it is calibrated.
  - The threshold (`mismatch_threshold`) has **no default**; tests use 3.0.
- **Decision needed:** adopt this detector and pick the threshold, or choose another.

### OQ-33 · Floor quantiser step and reconstruction — OPEN (interpretation in use)
- **Source:** [P1 §5.2, A6] fixes the target D_i ≤ θ_F and the Gaussian test channel, but not the quantiser step.
- **Implemented:** Δ²/12 = θ_F λ/(λ−θ_F), reconstruction (1−θ_F/λ)·Q(c). At high resolution this meets D ≈ θ_F (tested). A6 violations near λ ≈ θ_F are not yet counted.
- **Alternative:** subtractive dither (IDEA-14).

### OQ-34 · Metadata coding range and region count — OPEN (interpretation in use)
- **Source:** [P1 §D.3] gives 1 dB / 1/32 steps and 12 + 5 bits per chunk, but not the dB range or how regions scale with frame size.
- **Implemented:**
  - code 0 = negligible
  - codes 1..63 = −41…+21 dB on x/255 − ½ pixels
  - regions scaled to the pilot's region size
- **Status:** reproduces the paper's 36,360 bits at 640×352.

### OQ-35 · GCS user-interface toolkit — OPEN
- **What's blocked:** the GCS video panel widget, and the rest of the GCS view layer. The video service behind it is done.
- **Constraints:** no web/cloud dependency [BRIEF §5]; single operator station [BRIEF §4].
- **Decision needed:** which desktop toolkit (e.g. Qt/PySide6 as ADIAT uses, or another).

---

## C. Summary of what blocks what

| Phase | Hard blockers | Soft (can stub with a named parameter) |
|---|---|---|
| Phase 2 (skeleton) | done; OQ-26 provisional | all others stubbed as named parameters |
| Phase 3 (video reference + channel simulator) | none for reproducing paper tables | OQ-03, 11, 12, 13 needed to size for *our* link |
| Mission simulator | OQ-01, 05a–c, 16, 17, 18, 21, 22 | 05d–m, 19, 20 |
| Hardware / flight | OQ-03, 07, 10, 20, 29 | — |
