# Wave 6 QPU: derived RCS mirror circuits on BlueQubit's `quantum` device (orchestrator-owned). Frozen 2026-09-26, before any QPU job.

Approval: user approved up to $3 of reported cost on 2026-09-26, inside the unchanged $10 cap (ledger spent $0.00 at freeze).

## Circuits
- Derived from the released refs/rcs-nighthawk-data/data/circuits/mirror/d36_instance0.qasm, which is verified U·U†: all 36 segment pairs inverse-match.
- A depth-d mirror = the input rx layer, then the first d/2 cycles of U (each cycle = 1q layer + CZ layer), then the exact inverse of those d/2 cycles, then the final 1q layer of the released file's inverse part, then measure_all. The builder asserts that the derived circuit's ideal output is the input: exact 61q statevector is infeasible, so this is checked at the segment level.
- Input bitstring: numpy default_rng(20260926).integers(0,2,61); θ_i = π·s_i. Survival = shots whose measured bitstring (converted from qiskit's little-endian key) equals s.
- Depths run in order: 4, then 8, then 12. 1,000 shots each (the SDK default for `quantum`).

## Stop rules
- Before each job: `ok_to_spend(estimate)` and a wave-local cumulative reported cost + estimate ≤ $3.00. Otherwise stop.
- After depth 4: continue only if at least 5 of 1,000 shots survive (measurable), and the job reports a backend or device name or completes normally.
- Any single job reporting cost > $1.50: stop.
- All job ids go to results/bq_jobs.jsonl via record_job the moment they exist.

## Comparison (descriptive only)
The paper's Nighthawk pooled survival (IVW over 3 instances, released counts, wave-3 estimator):
| d | pooled survival |
|---|---|
| 4 | 0.2136 ± 0.0014 |
| 8 | 0.1093 ± 0.0010 |
| 12 | 0.0623 ± 0.0007 |

We report survival p with a Wilson 95% CI and the ratio p / p_Nighthawk.

## Frozen wording
"On <backend as reported> via BlueQubit, a mirror derived from the paper's released 36-cycle instance 0 returns its input in
p [CI] of 1,000 shots at depth d, against <p_N> pooled on Nighthawk r2. Different device, layout, transpilation, instance
depth and inputs: this is a descriptive cross-hardware data point, not a replication and not evidence about the paper's
advantage claim."
If the backend is not reported, write "<BlueQubit 'quantum' device, backend not reported>".
