# V2 diagnostic: RESULT (2026-10-06)

The pre-registration is PREREG.md, frozen 21:38:51Z with sha16 bd0b051e5df63034 and registered in graph/gate.py. Deviations are in DEVIATIONS.md:
- D1 normalized XEB, recorded before any results were seen.
- D2 exploratory repeats, NOT RUN because the token file is missing.

All of this is post hoc relative to wave 6. **The original V2 stays INCONSISTENT. Neither the wave-6/7 verdicts nor the 2418 / 312.6 factors change.** Analysis: analyze.py → results/analysis.json.

## Cost and instrument
- **Cost:** 8 BlueQubit mps.cpu jobs, 16 qubits, 1e5 shots each, all billed $0.00 (read back from the job records). The allowance probe (tools/probe_allowance_20261006.py) confirms that `cpu` and `mps.cpu` remain $0 after the credit expired.
- **Control C0, raw linear XEB:** 1.715 on exact samples, because the circuits are not Porter–Thomas. The pre-registered stop fired as intended (D1).
- **Control C0, normalized:** 1.002, which passes.

## Results: normalized XEB against the exact 16-qubit statevector
| Cell | χ | BlueQubit (95% CI) | Own wave-6 MPS (swap-back) | Own no-swap-back (descriptive) |
|---|---|---|---|---|
| F (forward 18 cycles) | 4 | 0.079 [0.074, 0.084] | 0.043 | 0.276 |
| F | 8 | 0.107 [0.102, 0.113] | 0.038 | 0.568 |
| F | 16 | 0.305 [0.298, 0.313] | 0.090 | 0.822 |
| B (mirror + rx(π) blocker) | 4 | 0.058 [0.057, 0.059] | 0.026 | 0.287 |
| B | 8 | 0.137 [0.134, 0.139] | 0.028 | 0.842 |
| B | 16 | 0.201 [0.197, 0.205] | 0.184 | 0.853 |

- **H_trunc: SUPPORTED** on both F and B, by the pre-registered rule (more than 2× own, with the CI excluding own, at 2 of 3 χ). On circuits that cannot be cancelled, BlueQubit's mps.cpu truncates better than our **wave-6 swap-back** MPS. It is clearly worse than our **no-swap-back** routing, and wave 7's own arm already took the best over routings that include no-swap-back (CRA_NSB and others).
- **H_cancel: REFUTED** (pre-registered rule: H_trunc holds on both F and B).

## R: the original V2 cells resubmitted, identical circuit and settings
| χ | Original V2 (2026-09-26) | Resubmitted (2026-10-06) | Within the 99% interval of the original? |
|---|---|---|---|
| 4 | 0.199 (19,931 / 1e5) | 0.016 (1,625 / 1e5) | NO |
| 8 | 0.028 (2,820 / 1e5) | 0.378 (37,820 / 1e5) | NO |

**V2 does not reproduce.** The same mps.cpu job at small χ gave survivals differing by roughly 10× in both directions. This is far beyond shot noise.

Run-to-run nondeterminism and a backend change between Sept 26 and Oct 6 cannot be told apart yet. The same-day repeat (D2) that would separate them could not run: the token file is gone.

## Reading
- The wave-6 V2 "inconsistent" verdict now has two documented contributors:
  1. Our wave-6 baseline routing (swap-back) was a weak MPS at small χ.
  2. BlueQubit mps.cpu small-χ mirror survivals were not reproducible on resubmission.
- No evidence was found for compile-time cancellation at 16q.
- Nothing here bears on the 61q headline arms:
  - The own-arm factor is already the best over routings, including no-swap-back.
  - The BlueQubit arm's literal 61q mirror cells were already void under D6.

## Status for the application
- The pre-registered part is complete and Stage-1-ready.
- Possible field-4 clause, at most one clause and labelled post hoc: "(a later diagnostic found BlueQubit's small-χ survivals did not reproduce on resubmission, and that our wave-6 baseline routing was the weaker MPS)".
- This would need two-family verification before the freeze. It is Mike's call whether to add it, given the advisor's stop recommendation and the reviewer audience (BlueQubit).

## D2 same-day repeats (exploratory, run 2026-10-08, $0)

### Results
| Cell | Sept 26 | Oct 6 | Oct 8 rep 2 | Oct 8 rep 3 |
|---|---|---|---|---|
| R χ=4 (mirror survival) | 0.199 | 0.0163 | 0.0169 | 0.0168 |
| R χ=8 (mirror survival) | 0.028 | **0.378** | 0.0292 | 0.0293 |
| F χ=16 (forward, normalized XEB) | — | 0.305 | 0.299 | 0.305 |

### Reading
- **Forward circuits reproduce.** All three F χ=16 runs agree within the shot-noise CI (±0.008).
- **Mirror survivals usually reproduce, with occasional large outliers.** Each mirror cell has a stable value (≈0.017 at χ=4, ≈0.029 at χ=8), but in 2 of 8 runs (4 per cell) it was off by ~10×: Sept χ=4 gave 0.199, and Oct 6 χ=8 gave 0.378.
- **Build time does not identify the outliers.** At 16q, mps_build_time is 3–5 s for both normal and outlier runs. The one sub-second build (0.57 s) is V2's χ=16 run (survival 0.618). So the 61q D8 collapse signature (build under 10 s) does not transfer to 16q, and the cause stays unexplained.
- **Updated V2 picture.** The September V2 values at χ=8 reproduce, at χ=4 they were an outlier, and the χ=16 value may be a partial collapse.

### Consequence
- BlueQubit mps.cpu mirror survivals carry instrument variance beyond shot noise. Its forward-circuit sampling does not.
- This is relevant to the kit's BlueQubit arm (224.08), which is built from 61q mirror survivals. That arm is already labelled "instrument validation failed (V2); post-hoc build-time filter; 2 of 3 instances". See the replication below.
