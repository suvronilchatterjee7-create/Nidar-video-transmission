# Ideas Pending — NIDAR RescueSwarm

Rule [USER-PROMPT §0.3]: any idea **not** supported by the Mission Brief, Paper 1 or Paper 2 goes here first. Nothing on this page is implemented or assumed by any other document. **You decide.**

The architecture docs refer to these ideas only as "see IDEA-nn (not adopted)".

Status values:
- **PENDING**: waiting for your decision.
- **ADOPTED**: you approved it. It then gets a tag `[IDEA-nn, approved <date>]`.
- **REJECTED**: you declined it.

| ID | Idea | Why it helps | Cost / risk | Serves | Status |
|---|---|---|---|---|---|
| IDEA-01 | **Posture-aware triage.** Use the dataset's `lying` posture label (YOLOv8-pose keypoints) as a priority term in the survivor auction or the DWVT density kernel | Likely casualties get kits first. The dataset and model already provide the label | Adds a term to the auction cost [P2 Eq. 38/179] that neither paper defines. Posture accuracy from above is unmeasured (63.8 % of labels are unreviewed). A wrong `lying` call delays others | D3, D4, [BRIEF Scenario] "first few minutes are critical" | PENDING |
| IDEA-02 | **De-duplicated detection gallery at the GCS.** One stable `track_key` per confirmed survivor with a small thumbnail [ADIAT-inspired: `flight_viewer_plan.md` gallery] | Operator sees *what* was tagged, not just a dot. Helps judge false positives | Thumbnails cost link capacity, which is not budgeted in [P2 §12.1]. The Brief requires only "tagged location", not images | D2 | PENDING |
| IDEA-03 | **Pairing code + short authentication string** between the GCS and each drone at setup [ADIAT-inspired: `FlightPairingDialog`, SAS], using local signalling only (no Cloudflare) | Stops cross-talk with another team's radio. Confirms the right drones are linked | Adds setup seconds inside the 300 s window [BRIEF §3]. Not required by any source | D6, D8 | PENDING |
| IDEA-04 | **Bandwidth boost for the drone with a candidate survivor, on the Paper 1 link.** Give that drone a larger share of W, the hybrid analogue of P2's H.265 bitrate boost | Matches [P2 §12.1] intent under the Paper 1 method | Paper 1 has no multi-user analysis (OQ-11). Changing W_i changes which certified floor design applies [P1 Prop. 18] | D5, D6 | PENDING |
| IDEA-05 | **Telemetry carried inside Paper 1's overhead fraction δ** of n = (1−δ)W·T_g | Single radio and single resource plan; nothing to coordinate between two radios | P1 defines δ only as "pilots and protocol overhead" [P1 §3.1]. Puts safety-critical telemetry on the same RF chain as video | D6 | PENDING (also OQ-14) |
| IDEA-06 | **A separate low-rate telemetry radio**, with video on its own radio | Telemetry and C2 survive video-link problems. Matches P2's "LoRa *or* 5.8 GHz" wording read as two radios | Extra mass and power (OQ-07). Two RF chains to integrate | D6, D7 | PENDING (also OQ-14) |
| IDEA-07 | **Confidence calibration of the detector** (e.g. temperature scaling on a held-out split) before the confidence is used in [P2 Eq. 260] | Makes the Bayesian update meaningful; reduces false dispatches | Needs reviewed labels and flood-like images we do not have yet (OQ-25) | D4 | PENDING |
| IDEA-08 | **Dataset extension**: flood and water scenes, dummies, known-altitude nadir frames from our own camera | Closes the gap between `RescueSwarm_PoseSet_v0.1` and the competition scene ([BRIEF Scenario], "real humans or dummies") | Collection and labelling effort; licensing ledger upkeep | D4, D9 | PENDING |
| IDEA-09 | **Correlated-evidence correction** in the Bayesian confirmation: discount consecutive frames from the same drone | [P2 Eq. 260–262] treats 10 frames at 30 Hz as independent, which risks overconfidence | Changes P2's update law; needs a correlation model we don't have | D4 | PENDING |
| IDEA-10 | **Analogue-only video fallback** when no certified floor design fits (refinement-only, clearly labelled "no floor guarantee") | Operator still sees *something* at low SNR. Listed by Paper 1 as future work, not designed [P1 Table 13 phase 6] | No guarantee. Paper 1 measured 24.85 dB at 2 dB SNR for linear-only [P1 Table 23] | D2, D5 | PENDING (also OQ-24) |
| IDEA-11 | **Sequenced launch and landing slots** on the 12 ft pad, so only one drone is moving in or near the pad at a time | Resolves the pad vs d_safe clash (OQ-18) without weakening the inter-agent CBF in flight | Adds launch and landing time to the mission clock | D1, D7, [BRIEF §7] | PENDING |
| IDEA-12 | **Re-observation scheduling** in the auction: a drone flagged "Low Confidence" [P2 Eq. 100] is held for re-observation and not re-tasked | Avoids dropping a kit on a badly localised tag | Paper 2 says re-observation happens but doesn't say how it interacts with the auction | D3, D4 | PENDING |

## Ideas deliberately **not** listed
These come straight from a source, so they are in the architecture, not here:
- Rateless floor coding: [P1 §6.6], as an alternative; the choice is OQ-23.
- Decentralised auction: [P2 §2.4]; OQ-27.
- ROI H.265: [P2 §12.1]; OQ-02.
