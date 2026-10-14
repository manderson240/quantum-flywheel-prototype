# rcs wave 6 STATUS (2026-09-26)
PREREG sha16 a27ffaeac26a1ce3 (frozen 12:15:11). Every job cost $0.00. Deviations are D1–D10. The hardware reference is d36 = 2.2408e-3 ± 5.57e-5.

1. **Validation.**
   - V3 (61q pipeline check) passed after the D1 key fix: BlueQubit puts qubit 0 leftmost, and the corrected score is 10000/10000.
   - V1 (16q exact) passed at 100000/100000.
   - V2 (16q, BlueQubit vs our own MPS at χ = 4/8/16) came out **INCONSISTENT**.
     - BlueQubit gave 0.19931 / 0.02820 / 0.61836; our own MPS gave 0.004645 / 0.006235 / 0.02442.
     - The ratios are 42.9, 4.52 and 25.3, and the BlueQubit values are not monotone in χ.
     - By §9, our own MPS therefore carries the verdict.
2. **BlueQubit collapsed runs (post-hoc, D6/D8).**
   - In 7 of 11 plain 61q d36 mirror runs, the service returned the exact ideal survival of 1, with an mps_build time of 1.8–6.5 s. That includes χ = 16, where our own MPS gives 2.5e-10.
   - The other 4 runs evolved, with build times of 165–850 s.
   - These observations are consistent with the service simplifying U·U† before it simulates. That is an inference, not a direct observation, and we do not know what triggers it.
   - All 4 attempts on instance 1 collapsed.
3. **BlueQubit evolved runs (post-hoc filter; instances 0 and 2; instance 1 NOT RUN).** At d36, χ = 256, the runs returned the input 1 and 3 times out of 2e5 shots each.
   - IVW estimate: 7.500e-6. z = 39.96. Ratio 298.8.
   - Poisson 95% range for the ratio: 88–822.
   - At χ = 128 both runs gave ≤ 1/2e5, so the ratio is > 448.
4. **Our own MPS (the headline, as the §9 substitute).**
   - At d36, χ = 256, the three instances gave 1.309e-6, 2.604e-7 and 1.210e-6. The mean is 9.265e-7, z = 40.19, ratio 2418. The per-instance ratios are 1712–8604.
   - Verdict: **EXCEED**.
5. **d\*(χ) from our own MPS:**
   - χ = 16: ≤ 8.
   - χ = 32, 64 and 128: 16.
   - χ = 256: 24. At d16–d20 the χ = 256 MPS matches the device or does better (5.02e-2 vs 3.04e-2).
6. **Routing sensitivity (post-hoc).**
   - Without swap-back, our own MPS at 61q, d36, χ = 256 averages 1.52e-7, which is 6.1× lower (up to 27× lower per instance). At 16q the same change gives up to ~28× higher.
   - BlueQubit's evolved value is 5.9× above ours on the same 2 instances.
7. **Runtime.**
   - BlueQubit time is dominated by sampling at ~19–29 ms per shot, so the 1e6-shot plan was infeasible (D5).
   - χ ≥ 512 was NOT RUN: the prediction was 26719 s at χ = 512.
   - F (the full logical d36 circuit) at χ = 256 with 1e3 shots ran in 1188 s (build 1157 s), job cl5CkkAovhM5dybr.
   - F at χ ≥ 512 was NOT RUN.
8. **d28 scan cell (exploratory).**
   - S256_i0_d28 returned the input 247/200000 = 1.235e-3, against hardware 7.954e-3: z = 26.14, ratio 6.44 on one instance. Our own MPS gives 1.947e-4 for the same cell.
   - The other two d28 instances were cut by the deadline.
   - Totals: 11 cells done, 55 NOT RUN.
9. **Scope.**
   - U·U† mirror survival is a proxy. It does not measure the fidelity of sampling the 36-cycle U.
   - We make no claim about the RCS advantage.
   - Our depth-d mirrors are derived from the released d36 instances, which are different draws from the paper's.

RCS WAVE6: VERDICT=EXCEED d36_ratio=2418
