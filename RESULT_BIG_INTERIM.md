# Interim — large-instance brackets (written 2026-09-24 BEFORE the chi=1024/2048 values exist)
51q x 30c (run 3, done): pp_1e-4 0.104 | mps_64 0.636 | mps_256 0.580 | mps_512 0.558. Cost $0.00.
Pre-registered edge (PATCH_PREREG_27CYC.md): [0.104-0.005, 0.636+0.005]. Contains QESEM 0.366, SPP 0.350/0.385,
M_th 0.410 and PEPS-BP 0.541. NOTE: 30 cycles exceeds the depth validated by the 27-cycle addendum, and the
addendum licenses "consistent with" wording only for 74qx27c, so for 51qx30c these are raw values / descriptive containment
only (verifier finding #4, 2026-09-24); not discriminating either way.
Stated in advance for the chi=1024/2048 follow-up (descriptive, NOT part of the tested pre-registration):
- mps_64 was strictly above exact in 45/45 27q/33q patch points with an exact value (results/floquet_patch{27,33}*.json), but it is a heuristic
  upper edge, not a bound. If mps_1024 or mps_2048 falls below 0.541 we will say "the MPS upper edge falls below PEPS-BP
  0.541", flag that this relies on the heuristic, and NOT claim PEPS-BP is wrong. If it stays above, we report no tension.
74q x 27c (run 2, done): pp_1e-4 0.086 | mps_64 0.610 | mps_256 0.563 | mps_512 0.544 -> contains QESEM 0.365: "consistent with".

## Addendum 2026-09-25 09:30 EDT — written while both chi=1024 jobs are RUNNING (7Mr3Ainb6iUa3qdo, SmXc2Q2CVg8YiwKt; no value exists)
Source: research/20260925-floquet-decision-path.md. MPS and PEPS-BP both truncate the state and are expected to err HIGH at
late cycles (originators' App. J–L: PEPS-BP reliable to ~12 cycles then drifts up). Therefore:
- An mps_1024 value near PEPS-BP 0.541 (e.g. 0.53–0.55) will be reported as "the MPS edge approaches the PEPS-BP value; both
  methods share the same truncation bias, so their agreement is NOT evidence of convergence". No convergence claim, no
  extrapolated value (a 3-point fit of chi 64/256/512 already "converges" to ~0.535 — an example of false convergence).
- The earlier rule stands: mps_1024 below 0.541 -> "the MPS upper edge falls below PEPS-BP", relying on the heuristic that
  MPS errs high; not a claim that PEPS-BP is wrong.
- Nothing here may be used to claim a decided value for 51qx30c or 74qx27c.
