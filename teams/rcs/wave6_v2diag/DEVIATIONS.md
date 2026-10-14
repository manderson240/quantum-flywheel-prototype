# V2 diagnostic: deviations from PREREG.md (frozen bd0b051e5df63034)

## D1: normalized XEB instead of raw linear XEB (recorded 2026-10-06T21:40:31Z, before ANY BlueQubit cell result was collected; results/cells/ held 0 files)

Control C0 failed as pre-registered. On 1e5 samples drawn from the exact F distribution, the raw linear XEB was outside [0.9, 1.1].

**Cause.** The 16-qubit restricted circuits are not Porter–Thomas, so a perfect sampler does not score 1 on 2^N·Σp² − 1:
| Circuit | 2^N·Σp² − 1 | Participation |
|---|---|---|
| F | 1.711 | ~24,172 |
| B | 86.87 | ~746 |

C0 therefore did what it was written to do: it detected that the instrument assumed the wrong distribution. Nothing in the simulators failed.

**Change.** Every XEB is divided by its ideal value, giving the normalized linear XEB F̂ = (2^N·mean_i p(x_i) − 1)/(2^N·Σp² − 1). This applies to F̂_BQ and its bootstrap CI, and to own F_own = (2^N·Σq p − 1)/(2^N·Σp² − 1). Perfect sampling scores 1 by construction, for any distribution.

**C0 is re-run** with the same [0.9, 1.1] band on the normalized estimator. The decision rules (the 2× factor and the CI condition) are unchanged, because both sides of every comparison share the same denominator. The raw values are also reported.

## D2: exploratory same-day repeats of R (recorded 2026-10-06T21:50:30Z, AFTER seeing the R results; not pre-registered)

R_chi4 = 0.01625 and R_chi8 = 0.3782 lie far outside the 99% interval of the original V2 values (0.199 and 0.028).
- **Question.** Is this run-to-run nondeterminism in mps.cpu, or a change between the September and October runs?
- **Method.** Two more identical resubmissions each at χ = 4 and χ = 8 (R2_*, R3_*), plus two identical F_chi16 repeats as a control. F_chi16 is the forward cell, so its XEB tests whether nondeterminism also appears on a circuit that cannot be cancelled.
- **Status.** Labelled exploratory; it does not change the H_trunc/H_cancel verdicts.
- **D2 status, superseded below (2026-10-06T21:51:41Z): NOT RUN.** Both submission attempts failed at token load, before any job was created. The BlueQubit token file (/home/mike-anderson/dev/cohezion/.env) no longer exists on the host. It was present at 21:40Z, when the pre-registered cells ran. Waiting on Mike. results/repeat_summary.json holds only the pre-registered R/F values.
- **D2 RUN 2026-10-08 after the token file was restored.** 6 jobs, all $0. Results are in results/repeat_summary.json and results/buildtimes.json.
