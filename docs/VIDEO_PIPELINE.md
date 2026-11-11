# Video Pipeline: Implementation and End-to-End Results (Phase 4)

Status: **Phase 4 result** · Branch `phase4/video-pipeline` · Date 2026-11-11.
Design: [VIDEO_SUBSYSTEM.md](VIDEO_SUBSYSTEM.md). Maths reproduction: [REPRODUCTION_P1.md](REPRODUCTION_P1.md).

> **Read this first.** Every number below comes from **simulation on synthetic test video**:
> - a generated moving scene, and ffmpeg's `testsrc2` pattern
> - the Paper 1 "pilot profile" channel (`paper_pilot_profile`)
>
> None of it is evidence about our camera or our radio (OQ-03, OQ-12). Those are still undecided.

## 1. What now exists

| Stage | Module | Status |
|---|---|---|
| E1 transform: Haar / DCT-II in time ⊗ 8×8 DCT [P1 Def. 4] | `video/transform.py` | ✅ implemented, tested (CT-10) |
| E2 variance field, metadata (12 + 5 bits) [P1 §D.3] | `video/variance_field.py` | ✅ reproduces the paper's 2,880 chunks / 36,360 bits at 640×352 (CT-11) |
| E3 water level [P1 Def. 7] | `video/gop_model.py`, `floor/designer.py` | ✅ |
| E4 floor quantiser, static-model arithmetic coder, CRC [P1 E4, Rem. 7] | `floor/{quantiser, entropy, crc}.py` | ✅ lossless round trip; output within 0.2 % of the model code length |
| Floor channel code [P1 §6.6] | `floor/code.py` | ⚠️ **abstraction only** (ideal outage test). A real code family is OQ-23 |
| E5–E6 residual, open-loop gains [P1 Prop. 8, Rem. 6] | `video/gop_model.py` | ✅ deterministic, so encoder and decoder agree without sending gains |
| E7 spreading + mapping, limiter [P1 E7, Lemma 6] | `refinement/{spreader, limiter}.py` | ✅ |
| Pilots + MMSE channel estimate [P1 §C.1] | `video/receiver.py` (D1) | ✅ |
| D2–D5 decoder: side information, Lemma 9, conditional mean, fallback [P1 Prop. 9, Rem. 5] | `video/receiver.py` | ✅ |
| Encoder / decoder orchestration | `video/encoder.py`, `video/receiver.py` | ✅ |
| End-to-end simulator: fading, pilots, floor outage | `sim/video/end_to_end.py` | ✅ |
| Test video, H.264 baseline (local ffmpeg/libx264) | `sim/video/{test_video, h264_baseline}.py` | ✅ |
| GCS video service: per-drone source, RGB, staleness, floor counter | `gcs/services/video_service.py` | ✅ service only. **The on-screen widget waits for the GCS UI toolkit (OQ-35)** |
| Loopback radio | `link/radio.py` | ✅ simulation only. **Real SDR driver: OQ-03 / OQ-10** |

## 2. Choices the paper does not make (all named, none hidden)

| # | Choice | Why | Where |
|---|---|---|---|
| C1 | Pixels scaled to x/255 − ½; metadata code 0 = "negligible", codes 1..63 = −41…+21 dB | Makes "12 bits per chunk" concrete. A first range (−36…+27 dB) clamped quiet chunks and made the model 4–5 dB pessimistic, so it was corrected | `variance_field.py` |
| C2 | Number of spatial regions is a setting; the profile keeps the pilot's region size (160×88 luma) | The paper's 4×4 regions at small frames made the metadata alone exceed the floor | `config.py` |
| C3 | Floor quantiser step chosen so Δ²/12 equals the test-channel noise θ_F λ/(λ−θ_F); reconstruction (1−θ_F/λ)·Q(c) | The paper gives the target (A6) and the test channel, but not the step | `floor/quantiser.py`; OQ-33 |
| C4 | Laplacian static entropy model per chunk | The paper's pilot used a Laplacian code length | `floor/entropy.py` |
| C5 | θ_F sent as 8 raw bytes inside the floor | Both ends must build bit-identical entropy tables, even on different CPUs | `encoder.py` |
| C6 | Gains come from the model's steady state (Eq. 9 + Prop. 3), iterated with Prop. 8 per chunk, from the current GoP's metadata only | Keeps the gains free of past-GoP state, like the floor. The decoder's actual side information is used only in Eq. 20 | `gop_model.py` |
| C7 | Block-diagonal Hadamard over power-of-two segments | Orthogonal with no padding. Plain power-of-two padding discarded up to half the dimensions (found and fixed) | `spreader.py` |
| C8 | Mismatch test (Rem. 5): normalised innovation, max of "all active" and "side-information-using" coefficients, above a threshold | The paper says "if the decoder detects mismatch" but not how. The threshold has no default | `receiver.py`; OQ-32 |
| C9 | Floor lost → hold the last good picture, flag `floor_ok = False` | The metadata travels inside the floor, so without it the analogue layer cannot be decoded | `receiver.py`; OQ-24 |
| C10 | Unit transmit power per data use; floor power ratio is a setting (profile: 1) | γ_F is the controller's output [P1 §C.3]. The profile does not run the controller | `config.py` |

## 3. End-to-end results, AWGN, 288×352, 25 fps, G = 8 (synthetic scene, 6 GoPs per point)

Floor sized at the true SNR (oracle, as in the paper's pilot).

| SNR (dB) | Floors decoded | Full PSNR (mean) | Floor-only PSNR | Model PSNR | Model − measured | T_eq (Mbps-eq) | Floor share | β_up |
|---|---|---|---|---|---|---|---|---|
| 2 | 3 / 6 | 36.28 | 35.42 | 36.27 | −0.01 | 2.80 | 0.92 | 0.83 |
| 4 | 6 / 6 | 37.37 | 36.08 | 37.60 | +0.23 | 3.54 | 0.69 | 0.83 |
| 6 | 6 / 6 | 38.38 | 36.08 | 38.69 | +0.31 | 4.82 | 0.54 | 0.80 |
| 8 | 6 / 6 | 39.18 | 36.08 | 39.61 | +0.43 | 6.08 | 0.44 | 0.81 |
| 10 | 6 / 6 | 39.84 | 36.08 | 40.36 | +0.52 | 7.21 | 0.36 | 0.84 |
| 12 | 6 / 6 | 40.36 | 36.08 | 40.97 | +0.61 | 8.18 | 0.31 | 0.87 |

What this shows, measured against the paper's own claims [P1 §D.5]:
- **H1 (floor holds when decoded):** ✅. Full ≥ floor-only in every decoded GoP, and floor-only is constant (≈ 36.1 dB) across SNR.
- **H2 (model predicts measured quality):** ✅ within 0.61 dB (paper: 0.18–0.36 dB on its clip). The model is slightly optimistic at high SNR.
- **Graceful degradation:** ✅. PSNR and T_eq rise smoothly with SNR. At 2 dB half the floors no longer fit, which matches the paper's "infeasible below about 4–6 dB" [P1 Table 22].
- **Ceiling:** T_eq reaches about 8.2 Mbps-eq at 12 dB, so not 10 Mbps here (the paper's η ≈ 0.66 shows the same shape).
- **β_up = 0.80–0.87:** like the paper (0.78–0.84). Truncated components dominate the distortion at this bandwidth ratio (≈ 0.17).

## 4. Other paths exercised

| Experiment | Result |
|---|---|
| Block fading L = 8 with N_p = 6 pilots, floor at the ideal 1 %-outage rate | Works. 5 of 6 floors delivered; the lost GoP was held and flagged; decoded GoPs PSNR 37.1 dB |
| Hard limiter at the Table 15 back-off (4.4 dB) | −0.1 dB at equal mean power (39.74 vs 39.84 dB). The PAPR benefit is not measured here |
| Scene cut | No damage: the encoder measures a ≈ 0 on the new scene, so the decoder ignores the stale prediction |
| Fallback (CT-13): decoder's previous reconstruction corrupted | Detector fires (NIS ≫ 3) and output = floor-only. On clean video NIS ≈ 0.9–1.0 (the noise model is well calibrated), so 0 false fallbacks in 16 GoPs |
| **Decoder-side motion search** (±16 px, guided by the decoded floor) | **No gain** (−0.1 dB) vs zero motion, for both slow and fast motion. **Paper target ≥ 1 dB [Table 13 ph. 3]: not reached.** Cause: a_j is measured at the encoder against a zero-motion prediction (no encoder motion search, by design), so a better decoder prediction is still weighted by a small a_j. See IDEA-13 |

## 5. Latency and complexity (VT-20: measured, not judged; L_max is OQ-13)

Pure Python and numpy on this PC, 288×352, G = 8 (T_g = 320 ms):
- **Encode:** about 0.41 s per GoP.
- **Decode:** about 0.66 s per GoP with zero motion, about 1.0 s with block motion search.

**Total ≈ 1.1 s for a 0.32 s GoP. This is not real time.** A compiled implementation is required for flight, as ARCHITECTURE §10 already planned (RISK-V12). The encoder uses no motion search; the paper's complexity claim remains unmeasured on embedded hardware (RISK-V11).

## 6. Comparison with zero-latency H.264 (the paper's H5)

Settings: libx264 two-pass, `-tune zerolatency`, GoP 8, no B-frames, at the capacity-matched rate n·C(γ)/T_g. That is ideal code and oracle rate, which favours H.264, exactly as in the paper.

| Test video | SNR | Hybrid | H.264 zero-latency | Gap |
|---|---|---|---|---|
| Synthetic scene | 6 / 10 / 12 dB | 38.38 / 39.84 / 40.36 | 45.89 / 49.98 / 51.61 | **−7.5 / −10.2 / −11.2 dB** |
| ffmpeg testsrc2 | 6 / 10 / 12 dB | 30.78 / 31.70 / 32.04 | 49.31 / 56.09 / 58.96 | **−18.5 / −24.4 / −26.9 dB** |

- **Paper's result:** −3.3 to −3.5 dB on its clip. Ours is worse, on content the paper itself says favours a digital codec: low entropy, easily motion-predicted, synthetic graphics [P1 §7.3].
- **Our pipeline is not the cause:** it agrees with the paper's own model to within 0.6 dB (H2).
- **Not tested here:** this comparison uses an ideal code and oracle rate. Under fading **without** timely feedback, H.264 hits the cliff. That regime is the paper's untested hypothesis (i)–(ii), and it is the next experiment if you want the case for Paper 1 tested.
- **Bearing on decisions:** this is the strongest evidence so far for **OQ-02** (H.265 vs Paper 1 for the GCS video) and **RISK-V02**.

## 7. Still not done (and why)

- **Real floor channel code** (LDPC or rateless): the code family is your decision (OQ-23). The simulation uses the ideal outage test the certificate bounds.
- **SDR / radio driver:** no hardware chosen (OQ-03, OQ-10).
- **GCS video widget:** no UI toolkit chosen (OQ-35). The service layer behind it is done.
- **Certificate with clipping and estimation error:** the paper does not specify how to do it (P-7).
- **Real drone footage:** none available (OQ-12, IDEA-08).
- **Multi-drone spectrum sharing:** OQ-11.
- **Controller in the loop:** the floor power ratio is fixed in the profile. The controller is implemented and tested separately (Phase 3).
