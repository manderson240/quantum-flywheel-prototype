# Result — pre-registered 27-cycle bracket addendum (PATCH_PREREG_27CYC.md, hash 037116030b0d9dc4)
Scored 2026-09-24 with the frozen counting rule (pp_1e-4 - 0.005 <= exact <= mps_64 + 0.005); no parameters changed.
- n=27: 6/6 in bracket; two-sided 4/4. n=33: 6/6 in bracket; two-sided 2/2. Total 12/12 -> SUPPORTED at both n.
- No points missing; total BlueQubit cost $0.00 (free CPU tiers).
Caveats (descriptive, not tested): only 6/12 points are two-sided — the Pauli-path lower side collapses to ~0 for zzd2/zzd3
at 33q, so for those the test is one-sided. Bracket widths (mps_64 - pp_1e-4) at 20/27 cycles are 0.24-0.42 — feasibility bounds, not error bars.
Per the addendum, the 74qx27c bracket (run 2) may now be reported as "consistent with / inconsistent with" QESEM.
Per-point table: results/floquet_patch_27cyc_score.txt
