# Result: BlueQubit mps.gpu validation and measured cost scaling (PREREG_MPSGPU.md + ADDENDUM1; 2026-09-28)

Status: COMPLETE. Not yet in the application; not yet independently verified. Source of every number: results/mpsgpu.json
and results/bq_jobs.jsonl (job ids PR9HTY4fBzWLUKKt, 9MmjGkhUPfwM0ZFE, Temr3BqLJuJyqQKn).

| job | mps.gpu value | mps.cpu value | abs diff | wall time | billed |
|---|---|---|---|---|---|
| 51qx30c magnetization, χ = 512 | 0.5583479436 | 0.5583479437 | 3.8e-11 | 0.551 h | $1.89 |
| 74qx27c magnetization, χ = 512 | 0.5435972772 | 0.5435972772 | 1.4e-12 | 0.751 h | $2.82 |
| 51qx30c magnetization, χ = 1024 | 0.5383666435 | 0.5383666431 | 3.8e-10 | 1.752 h | $6.95 |

- V-GPU PASSED (all three within 1e-3; in fact within 4e-10).
- Main pre-registration steps 2–3 (χ = 2048): NOT RUN by the frozen rule. The rule assumed cost ∝ χ³ and predicted $121
  (51q) and $176 (74q).
- Measured scaling (ADDENDUM1): cost grows by 2^1.88 = 3.68× per χ doubling (512 → 1024, 51q); wall time by 2^1.67 = 3.18×.
  74q vs 51q at χ = 512: cost ×1.49, time ×1.36. Rate $3.43–3.97 per billed hour.
- Re-costed from measured scaling (EXTRAPOLATIONS from one χ doubling; GPU cost may steepen at larger χ, as mps.cpu's
  512 → 1024 was 6.9×): χ = 2048 ≈ $26 / 5.6 h (51q), $38 / 7.6 h (74q); χ = 4096 (the largest bond dimension in Leviatan et al., arXiv:2607.24937, Qedma-led with IBM, RIKEN and BlueQubit co-authors; they report M_{z=2}, not the tracker's total M, so values are not directly comparable) ≈ $94 / 18 h (51q),
  $140 / 24 h (74q).
- BlueQubit's estimate() overstated the billed cost by 8.0–10.1× on all three jobs ($16.53, $28.52, $55.31 estimated).
- No new physics: every value reproduces an existing mps.cpu value. The MPS upper edge at χ > 1024 remains unmeasured.

Frozen cost line (PREREG_MPSGPU.md): "On BlueQubit mps.gpu, χ = 1024 on the 51-qubit candidate took 1.75 h and cost $6.95;
the free CPU tier ran χ = 1024 in 13.4 h (51q) / 20.4 h (74q) and was terminated at χ = 2048 after 7.7 h."

Lesson for the graph: the pre-registered χ³ assumption over-predicted χ = 2048 cost about 4.7× ($121 vs ≈ $26), so the
conservative rule blocked a job the credit would nearly have covered. Measure the scaling exponent before assuming it.
Spend: $11.66 of the $24.28 credit ($12.38 total ledger); $12.62 credit remains, expiring 2026-10-05.
