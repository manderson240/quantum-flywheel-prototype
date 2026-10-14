# Exploratory: run-to-run recurrence filter on wave-2 findings (2026-10-07)

**Status: EXPLORATORY.** This was not pre-registered, and it reuses the wave-2 data the benchmark was scored on. Script: recurrence_filter.py, output in recurrence_filter.json. It implements lead 1 of research/20261007-ai-verification-leads.md.

**Rule tested.** A finding is kept only if the other blind run on the same copy flagged the same file and line, within a tolerance.

**Sanity check.** The plant-hit total is 51, which matches the published 51 of 72. So the instrument reads the same data the benchmark score was computed from.

| Tolerance | Plant hits kept | False findings kept (all copies) | Placebo false findings kept (C, per run) |
|---|---|---|---|
| exact line | 48 / 51 (94%) | 25 / 53 (47%) | 7/10 and 6/12, i.e. 22 → 13 (−41%) |
| ±3 lines | 51 / 51 | 38 / 53 (72%) | 9/10 and 9/12, i.e. 22 → 18 (−18%) |

**Reading**
- At exact-line tolerance, the filter halves false findings across the planted copies and cuts placebo false findings by 41%, while losing 3 of 51 hits.
- Two caveats keep this short of the pre-registered ≥ 50% bar:
  1. **Plant hits recur partly by construction.** A plant sits at a fixed place, so any run that catches it flags the same line.
  2. **Many false findings recur.** About half the false findings in the planted copies, and 59% (13/22) on the placebo, reappear in the second run of the same model. Same-family errors are correlated, consistent with Kim et al.
- So recurrence across two runs of one model family is a weak filter. The confirmatory Stage-1 arm should require recurrence across two different model families. That is how this project's two-family rounds already work, and their kimi false positives (FP11–FP15) were caught by the other family.

**Application impact.** None before the freeze. This feeds the Stage-1 verification plan.
