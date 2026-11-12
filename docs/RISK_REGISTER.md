# Risk Register

Status: **Phase 1 draft**.
- Likelihood (L) and Impact (I) are on a 1–5 scale, judged qualitatively from the sources.
- Mitigations listed are **only** those the sources support. Anything else points to an IDEA or OQ for you to decide [TEAM-BRIEF §0.3].

## Video and link (Paper 1)

| ID | Risk | Evidence | L | I | Mitigation from the sources | Decision owner |
|---|---|---|---|---|---|---|
| RISK-V01 | **Our link may not provide L ≥ 4 independent fading blocks per GoP.** A low-altitude, line-of-sight, single-antenna, narrowband link may be close to static and flat, which makes the certified floor **infeasible** | [P1 Cor. 6, Table 9: L ≤ 2 infeasible; "a static, flat link provides none"] | 4 | 5 | Diversity from frequency selectivity, antennas or time variation within T_g [P1 §6.4]. Preflight gate P-1. Measure L on the real link (OQ-03) | you (hardware) |
| RISK-V02 | **Paper 1 loses to H.264 in its own pilot**: −3.3 to −3.5 dB vs zero-latency, about −7 dB vs default preset; floor block 1.90× credited; η ≈ 0.66. **Phase 4: −7.5 to −27 dB on our synthetic test videos** | [P1 Table 23, §D.5 H5, Table 11]; docs/VIDEO_PIPELINE.md §6 | 5 (measured) | 3: video is display-only (OQ-31); 5 if GCS detection on video were ever needed | Follow strictly per your decision (OQ-04). Paper's own roadmap: decoder-side MC (≥ 1 dB), parametric metadata (≤ 3 %), context-adaptive floor (≤ 1.3×) [P1 Table 13], none designed by the paper | you (OQ-04 answered) |
| RISK-V03 | **SNR feedback absent or late.** Margin rises from 3.2 dB (d = 0) to 6.1 dB (d = 1) to 11.2 dB (none); no feedback is infeasible at 10 dB nominal | [P1 Table 19, Thm 3] | 3 | 5 | SNR report every GoP on the highest-priority telemetry class (VIDEO §7). Measure ρ, σ_s, σ_m | you (OQ-03, OQ-14) |
| RISK-V04 | **Floor certificate omits clipping and channel-estimation error** | [P1 §B.1, §C.1, §8] | 5 (known gap) | 3 | Shown as a caveat in `CertifiedFloorDesign.includes_*`. Extension is paper roadmap phase 6 [P1 Table 13], not designed | you (Phase 3 scope) |
| RISK-V05 | **A8 (certificate monotone in SNR) not proved**; checked at one point | [P1 §C.2] | 2 | 4 | Re-check on our grid in Phase 3 | — |
| RISK-V06 | **Gaussian model assumptions (A1–A6)**; evidence is one pre-compressed animated clip | [P1 §8, §D.6] | 4 | 3 | Paper roadmap phase 1: ≥ 6 raw sequences, 4 motion classes [P1 Table 13]. Needs raw video from *our* camera (OQ-12) | you |
| RISK-V07 | **SDR-class radio needed** for the analogue layer; weight, power, integration effort | inferred from [P1 Prop. 8, §B.1, §C.1, E7] (OQ-10) | 4 | 4 | None in the sources. Decision OQ-02 / OQ-10 | you |
| RISK-V08 | **Four drones share spectrum.** Smaller W_i pushes the floor share up (58 % at 1 MHz, 10 dB; 97.8 % at 1 MHz, 5 dB) | [P1 Table 10]; multi-user not analysed (OQ-11) | 4 | 4 | None in the sources | you |
| RISK-V09 | **Floor code practicality.** Long codes needed; 10⁴-bit LDPC blocks mean segmentation (about 10× overhead) unless rateless | [P1 Prop. 13, §6.6] | 3 | 3 | Monolithic or rateless code (OQ-23) | you |
| RISK-V10 | **Latency.** At least T_g (267–320 ms at G = 8) plus processing before a GoP can be sent; L_max undefined | [P1 (L), Table 21] | 3 | 2 | G vs overhead trade [P1 Prop. 12]; set L_max (OQ-13) | you |
| RISK-V11 | **Encoder complexity unmeasured** on embedded hardware | [P1 §8] | 3 | 3 | Paper roadmap phase 7 (SDR bench, ops per sample vs H.264) [P1 Table 13] | — |
| RISK-V12 | **Not real time in Python:** about 1.1 s to encode + decode a 0.32 s GoP at 288×352 | docs/VIDEO_PIPELINE.md §5 | 5 (measured) | 4 | Compiled implementation behind the same contracts (ARCHITECTURE §10) | you (language/hardware) |
| RISK-V13 | **Decoder-side motion compensation gives no gain** as designed | docs/VIDEO_PIPELINE.md §4 | 5 (measured) | 2 | IDEA-13 (needs your decision) | you |

## Swarm, mission and platform (Paper 2 and Brief)

| ID | Risk | Evidence | L | I | Mitigation from the sources | Owner |
|---|---|---|---|---|---|---|
| RISK-S01 | **Weight.** LiDAR, Jetson-class compute and (if Paper 1) SDR on a 4.8 kg airframe; no breakdown; 19.2 kg fleet leaves 5.8 kg unallocated | [P2 Eq. 227] [BRIEF §2] | 4 | 5 (over 25 kg = no flight) | Weight table, ARCHITECTURE §9.1 (OQ-07) | you |
| RISK-S02 | **NMPC 8–12 ms solve time unvalidated**; 20 ms budget at 50 Hz | [P2 §10.2 "requires experimental validation"] | 3 | 4 | acados RTI, warm start [P2 §10.2]; benchmark on target hardware before flight | — |
| RISK-S03 | **Kit shortfall.** At most 4 deliveries with 4 single-kit drones vs up to 10 survivors; assignment problem infeasible | [BRIEF §1] vs [P2 §7.3] | 5 | 5 | None in the sources (OQ-01) | you |
| RISK-S04 | **Detector confidence uncalibrated**; frames treated as independent; dataset mostly unreviewed, with no flood scenes or dummies | [P2 Eq. 260–262] [DATASET: qa/class_balance.md] | 4 | 4 | Multi-drone confirmation and the 0.95 threshold [P2 §9.3]. IDEA-07/08/09 pending | you |
| RISK-S05 | **Paper 2 contradictions** (13 items, OQ-05) give undefined behaviour unless resolved | [P2 various] | 5 | 3 | Table-driven automaton and both cost forms logged, so the choice is a configuration decision | you |
| RISK-S06 | **Launch pad vs d_safe = 3 m**: hard CBF infeasible with 4 drones on a 3.66 m pad | [BRIEF §7] [P2 Eq. 216] | 5 | 4 | None in the sources (OQ-18; IDEA-11) | you |
| RISK-S07 | **Soft geofence.** Paper 2's fallback can accept a breach; the Brief requires staying inside and a breach failsafe | [P2 §9.4, §14.2.2] vs [BRIEF §7, §8] | 2 | 5 | None in the sources (OQ-17) | you |
| RISK-S08 | **Kit drop near real people**; drop height and offset undefined | [BRIEF §1] [P2 Eq. 235–238] | 3 | 5 | Terminal constraints and IBVS [P2 §12.2.2]; OQ-20 | you |
| RISK-S09 | **GCS-centralised auction**: link loss suspends allocation; comms loss triggers RTH | [P2 §7.3, §9.1, §13.2.2] | 3 | 3 | Decentralised alternative mentioned [P2 §2.4] (OQ-27) | you |
| RISK-S10 | **5-minute setup** relies on 60 s boot and mesh formation, unmeasured | [P2 §12.4] | 3 | 4 | Parallel preflight state machine [P2 §12.4]; rehearse | — |
| RISK-S11 | **Coverage time unknown** without camera and altitude figures; P2's 11 min is a target | [P2 §12.2.3] | 3 | 4 | Bound T ≥ A/(N·W_FOV·v_sweep) once OQ-21 is answered | you |
| RISK-S12 | **Unverified rule citations** in Paper 2 (8.x, Annexures, 25 marks) could mislead priorities | [P2 §2.1, §12, §13, §15] | 3 | 2 | Treated as unverified (OQ-06) | — |
| RISK-S13 | **Mission plan puts drones on crossing paths**: delivery transits cross other drones' sweeps at the same altitude, so the 3 m separation [P2 Eq. 216] depends entirely on the CBF layer, which is not built yet | docs/MISSION_SIM.md §4 (closest approach 0–0.6 m in kinematic runs) | 4 | 5 | Inter-agent CBF [P2 §8.3]; IDEA-16 | you |
| RISK-S14 | **Decoys pass the confirmation rule**: an object scored 0.7 on every frame is confirmed and receives a kit, because Paper 2 treats consecutive frames as independent | docs/MISSION_SIM.md §4, MS-14 | 3 | 4 | IDEA-07 (calibration), IDEA-09 (correlated evidence) | you |

## Licensing and process

| ID | Risk | Evidence | L | I | Mitigation | Owner |
|---|---|---|---|---|---|---|
| RISK-L01 | `yolov8n-pose.pt` (Ultralytics) is, to my knowledge, AGPL-3.0; onboard use may oblige source release. 7 dataset images are CC BY-SA 2.0 | [DATASET: README §7, LICENSE_LEDGER.csv] | 3 | 3 | Detector behind the `PersonDetector` interface, so it is swappable (OQ-08a) | you |
| RISK-L02 | ADIAT is GPL-3.0; copying code would impose GPL | [TEAM-BRIEF §4] | 1 | 4 | Clean-room patterns only; no file copied | — |
| RISK-P01 | Reference code for Paper 1 unavailable; reproduction may fail on transcription errors | [P1 §A, §E]; OQ-30 | 1 (after Phase 3) | 3 | **Phase 3:** equations re-extracted in UTF-8; 29 checks reproduce, 2 small and 2 real mismatches reported in REPRODUCTION_P1.md, none tuned | — |
| RISK-P02 | The synthetic experiments (Table 16, controller fixed point) don't reproduce in level, so their numbers can't be used to size *our* controller | REPRODUCTION_P1.md VT-13/18 | 5 (observed) | 2 (safety rests on the certified grid, not on these numbers) | Resize on our own model once OQ-03/12 are answered | you |
