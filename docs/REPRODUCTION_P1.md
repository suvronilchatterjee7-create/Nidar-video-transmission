# Paper 1 Reproduction Report (Phase 3)

Status: **Phase 3 result** · Branch `phase3/video-reference` · Date 2026-11-11

**What was done.** Paper 1's closed forms and certificate machinery were re-implemented from the equations. The paper's reference code (`floorlab.py`, etc.) is not available.

**Comparison method:**
- Our numbers are compared with every published table the prompt listed: Tables 5, 7, 8, 9, 10, 14, 15, 16, 17, 18, 19 and 20.
- **Nothing was tuned to force a match** [USER-PROMPT §8 Phase 3].
- Where a number does not reproduce, the test is `xfail(strict=True)` with our measured value in the reason. If a later change makes it match, the test turns red (XPASS), so the report must then be updated.

**Equations.** They were taken from a UTF-8 re-extraction of the PDF, which preserves the Greek symbols. The Phase 1 transcription notes for Eq. 19 and Eq. 20 are resolved; see [VIDEO_SUBSYSTEM.md §4.7, §4.13](VIDEO_SUBSYSTEM.md).

**Dependencies.** numpy plus the Python standard library (`statistics.NormalDist` for Q⁻¹, `math.erfc`, numpy Gauss–Laguerre). **scipy was not needed and was not installed.**

**Tests:**
- `tests/paper1/test_vt_reproduction.py` and `tests/paper1/test_channel_and_controller.py`.
- The slow Monte-Carlo cases are marked `slow` and run with `python tools/check.py --full`.

**Legend:**

| Mark | Meaning |
|---|---|
| ✅ | reproduced at the paper's printed precision |
| ✅ MC | reproduced within Monte-Carlo noise (tolerance stated) |
| ⚠️ | small mismatch, conclusion unchanged |
| ❌ | not reproduced |
| ∅ | not reproducible as published (inputs unstated); the proved property was checked instead |

## Summary

| VT | Paper item | Paper value(s) | Ours | Result |
|---|---|---|---|---|
| VT-01 | Table 5, firewall price (5 rows × 3) | e.g. a = 0.9: 3.322 / 2.154 / 1.168 | identical | ✅ |
| VT-02 | Prop. 3 / Table 14, Kalman fixed point | 0.164001746899620 | 0.164001746899620 (closed form = iteration to 1e-14) | ✅ |
| VT-03 | Eq. 18 / Table 14, posterior variance | 0.009615384615 | 0.009615384615 | ✅ |
| VT-03 | Prop. 9, conditional mean | — | MC: unbiased, error variance = D within 1 % | ✅ (extra check) |
| VT-04 | Prop. 8 / Table 14, allocation vs constrained optimiser | gap 8.1e-11 | KKT conditions + no improving power transfer on 20 instances | ∅ method differs (no scipy optimiser); optimality verified |
| VT-05 | Lemma 4 / Table 14, density sampler (m = 50, γ = 10, 4e5) | mean 119.90, var 90.78 (theory 119.89, 90.91) | mean within 5 SE, var within 1 % of theory | ✅ MC |
| VT-06 | Table 7, sizing overhead (24 cells) | e.g. 0.47 \| 0.35 | all 24 identical | ✅ |
| VT-06 | Table 8, block sizes | 154,897 / 154,706 | 154,897 / 154,706 | ✅ |
| VT-07 | Table 8, ε̂ (1e6 draws) | 5.22e-3; 2.98e-2; 5.10e-4; 7.48e-3 | 5.26e-3; 3.00e-2; 4.59e-4; 7.42e-3 | ✅ MC (3rd row −10 %, about 2.3 standard errors) |
| VT-07 | Table 8, ε̄ (row 1) | 5.61e-3 | 5.645e-3 (on our ε̂); KL bound on the paper's ε̂ = 5.61e-3 | ✅ |
| VT-07 | §6.3, V-rule miss factors | 6 and 15 | 6.0 and 14.8 | ✅ MC |
| VT-08 | Table 9, ideal, L = 4 / 8 / 16 / 64 / 256 / ∞ | 0.435 / 0.271 / 0.212 / 0.167 / 0.151 / 0.138 | 0.436 / 0.2715 / 0.212 / 0.167 / 0.151 / 0.138 | ✅ MC (≤ 0.6 %) |
| VT-08 | Table 9, ideal, L = 1 | 27.74 | **27.85** (exact closed form) | ⚠️ −0.4 %, unexplained |
| VT-08 | Table 9, ideal, L = 2 | 1.409 | **1.397** (exact quadrature) | ⚠️ −0.9 %, unexplained; "L ≤ 2 infeasible" still holds |
| VT-08 | Table 9 / Cor. 6, certified, L = 4 / 8 / 16 / 64 | 0.521 / 0.298 / 0.223 / 0.171 | 0.515 / 0.296 / 0.221 / 0.170 | ✅ MC (≤ 1.2 %; ours slightly smaller) |
| VT-08 | §C.2, A8 check at L = 16, n_F = 297,376, 8..12 dB | 2.1e-2, 3.2e-3, 3.7e-4, 4e-5, 0 | 2.09e-2, 3.10e-3, 3.60e-4, 5.0e-5, 0 | ✅ MC |
| VT-09 | Table 10, AWGN floor share (9 cells) | e.g. 58.1 / 11.6 / 2.9 | identical | ✅ |
| VT-10 | Prop. 13, segmentation | 0.47 % / 4.95 % | 0.47 % / 4.95 % | ✅ |
| VT-11 | §6.6, ideal rateless, L = 4 / 16 / 64 | 14.6 / 13.9 / 13.8 % | 14.6 / 13.9 / 13.8 % | ✅ MC |
| VT-12 | Table 15, optimal back-off (5 rows × 3) | e.g. 20 dB: 4.41 / 14.34 / 1.25 | identical | ✅ |
| VT-12 | Table 20, limiter vs MC (4e6 draws) | \|Δα\| ≤ 3e-4, \|Δσ_d²\| ≤ 2e-5 | \|Δα\| ≤ 9.3e-4, \|Δσ_d²\| ≤ 9.1e-4: within 5 standard errors | ✅ MC (consistent; looser than the paper's single run) |
| VT-13 | Table 16 inputs: θ_F, credited, B_F/k | 0.206 / 0.0482 / 0.093 | 0.2063 / 0.0482 / 0.0930 | ✅ (fixes the index convention, below) |
| VT-13 | Table 16, n_F/n and f(γ_F) columns | e.g. 10 dB: 0.223 / 16.38 | identical (8 rows) | ✅ |
| VT-13 | Table 16, T_eq, distortion, 2ζ/(ξν_c), optimum | 9.776 Mbps @ 10 dB; optimum 10.5 dB; D = 5.399e-3; price 10.40 @ 10 dB | **10.66 Mbps; optimum 10.0 dB; D = 4.89e-3; price 8.43** | ❌ set-up underspecified (below) |
| VT-13 | Structure: one crossing of Eq. 32 below the sweep optimum; flat objective | crossing 9–9.5 dB | crossing ≈ 8.6 dB, T_eq within 2 % over 8–11 dB | ✅ structure only |
| VT-14 | Table 17, regret (300 random m = 60 instances) | worst 1.0018 / 1.0064 / 1.0238 / 1.0622 | worst 1.0021 / 1.0113 / 1.0402 / 1.1072, all ≤ (1+δ)² | ∅ instance distribution unstated; the bound (Prop. 15) holds |
| VT-15 | Table 18, optimal pilots (12 cells) and rates | e.g. m = 100 @ 10 dB → 6, 2.552 | all 12 pilot counts identical; rates within ±0.002 | ✅ (we integrate exactly; the paper used 4e5 MC draws) |
| VT-15 | Table 18, perfect-CSI row | 1.716 / 2.906 / 5.884 | 1.716 / 2.907 / 5.886 | ✅ |
| VT-16 | Prop. 16 / Table 20, allocation with estimation error | gap 4e-14; 3.025342 vs 3.025335 | KKT/no-improving-transfer on 10 instances; Eq. 37 ceiling holds; → Prop. 8 within 1e-4 at σ² = 1e-6 | ∅ instances unstated; properties verified |
| VT-17 | Table 19, margin rule (6 rows × 4) | e.g. d = 1: 1.632 / 6.07 / 60.1 / 42.1 | 1.633 / 6.07 / 60.2 / 42.2 | ✅ (±1 in the last digit) |
| VT-17 | Eq. 39, sensitivity | 12.3 / 8.7 / 6.4 / 4.9 % | identical | ✅ |
| VT-17 | **New:** Thm 3's prediction step by simulation (A7 true) | — | P[s_g < γ_d] = 1.02 % / 0.98 % / 0.98 % for d = 0 / 1 / 4 at η = 1 % | ✅ new evidence |
| VT-18 | §C.3, undamped oscillation ratios | −0.59 … −0.51, s ≈ −0.52 | −0.57 … −0.51 | ✅ |
| VT-18 | β = 0.66 settles in 2 steps from 6 and 14 dB | yes | yes | ✅ |
| VT-18 | Fixed point | 9.41 dB | **≈ 9.0 dB** | ❌ same set-up gap as VT-13 |
| VT-19 | Cor. 7, violation intervals | 26.7 / 267 / 2,667 / 26,667 s | identical | ✅ |

**Score.** Of the items checked:
- **29** reproduce: exactly, or within Monte-Carlo noise.
- **2** are small numeric mismatches with the conclusion unchanged (Table 9, L = 1 and L = 2).
- **2** are not reproduced (Table 16 throughput level; controller fixed point). Both trace to one underspecified set-up.
- **3** cannot be reproduced as published, because the random-instance distributions or optimiser are not stated. For these the property the paper proves was verified instead.

## The two "not reproduced" items (VT-13 / VT-18)

Paper 1 §B.2 describes the synthetic sweep only in outline. We implemented exactly what is written and **chose** the following where it says nothing (each choice is in `sim/video/synthetic_model.py`):

1. **Index of λ_i = 10³(1 + i/20)⁻².** The paper does not say where i starts. i = 0..k−1 is the only one of {0, 1} that gives the stated θ_F = 0.206 and B_F/k = 0.093. That identifies it from published intermediates; it is not a fit to the result.
2. **Channel budget.** The synthetic GoP gets the 720p30, G = 8 budget per coefficient: n = W·T_g·k / k_720p. This reproduces the n_F/n column exactly.
3. **Floor payload.** B_F = R_intra(D_F), i.e. credited bits plus the firewall price, with no Δ_q or metadata. This matches the stated 0.093 bit per coefficient.
4. **Energy and noise convention for the refinement layer.** This is **not stated**. Energy n·P̄ with P̄ = 10, ν_c = 1, and the floor using n_F·γ_F. The refinement uses the rest over M = 2(n − n_F) real dimensions, with noise ν = ν_c/2 per real dimension.
   - A diagnostic probe with ν = ν_c per real dimension gives 8.61 Mbps instead of 10.66.
   - The paper's 9.776 lies **between** the two conventions, so neither standard reading reproduces it.
   - The remaining gap is most likely in this unstated convention, or in how T_eq is "scaled to 720p". We did not search further, because that would become tuning.

What *does* reproduce:
- the analytic columns
- the existence and uniqueness of the Eq. 32 crossing, below the sweep optimum
- the flatness of the objective near the optimum
- the controller's oscillation ratio and two-step settling at β = 0.66

**What this means for the design:** VT-13 and VT-18 are illustrative experiments, and the paper says so ("The numbers illustrate structure; they are not a performance claim", [P1 §B.2]). The floor guarantee (Thm 2–4) does not depend on them. The controller's safety comes from the certified grid (Prop. 18, tested by CT-12 with a deliberately divergent map). It does not come from the fixed-point value.

## Small mismatches (VT-08, L = 1 and 2)

- **L = 1** has a closed form: R_ε = log₂(1 + γ̄·(−ln(1−ε))). That gives 27.85, not 27.74.
- **L = 2**, computed by exact quadrature, gives 1.397, not 1.409.
- **Scale factor:** the two cells differ in opposite directions, so no single scale factor (e.g. a different n) explains both.
- **Effect:** both values are > 1, so Corollary 6's conclusion ("L ≤ 2 infeasible") is unaffected.

## Not covered in Phase 3 (still stubs)

These need decisions you haven't made yet (video format OQ-12, radio OQ-03/10, floor code OQ-23):
- the transform, variance-field estimation, quantiser, entropy coder, CRC and spreader
- encoder/decoder orchestration on real video

**Pilot PSNR results.** Table 23 and the H.264 comparison (H5) were not attempted. They need the raw clip, an H.264 encoder and the chunk layout of §D.3.

**Certificate gap.** The certificate still excludes clipping and channel-estimation error (P-7). The sampler was not extended, because the paper does not specify how.

## Reproduce

```bash
.venv\Scripts\python tools\check.py --full
```

The fast gate (`tools/check.py`) skips the 9 `slow` tests:
- the certified Table 9 search: 4 values, about 1.5 minutes
- the synthetic sweep and controller: about 1.5 minutes
