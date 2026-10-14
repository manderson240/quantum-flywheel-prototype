# Result — 51q×30c MPS χ=1024 (BlueQubit mps.cpu job 7Mr3Ainb6iUa3qdo, 48,227 s, $0.00), scored 2026-09-25 10:08 EDT
Reading rules frozen BEFORE this value existed: RESULT_BIG_INTERIM.md (sha16 e8a5f47c22b52bb3, verified unchanged at scoring).
MPS upper edge by χ: 64 0.6355 · 256 0.5796 · 512 0.5583 · 1024 0.5384. Steps per doubling: 0.0559, 0.0212, 0.0200.
- Frozen rule "below 0.541": the MPS upper edge is 0.0026 below PEPS-BP 0.541. This relies on the heuristic that MPS errs high
  (45/45 at 27–33 q); it is NOT a claim that PEPS-BP is wrong. The gap (0.0026) is smaller than the 0.005 tolerance
  the pre-registrations use (χ=1024 edge + 0.005 = 0.5434 ≥ 0.541), so it is not a discrepancy. (The pre-registered bracket
  itself uses the χ=64 edge, 0.6355; the χ=1024 edge is our descriptive extension of it.)
- Frozen rule "near 0.541 (0.53–0.55)": MPS and PEPS-BP may share a high-side truncation bias; their closeness is NOT evidence
  of convergence. The step did not shrink (0.021 → 0.020), so the ladder shows no geometric convergence either.
- Scope: 30 cycles exceeds the depth validated by the 27-cycle addendum -> descriptive only. No decided value for 51q×30c.
- 74q×27c χ=1024 (SmXc2Q2CVg8YiwKt) still running at scoring time.

## Correction 2026-09-25 (council 6, methodology lens) — what is and is not pre-registered here
- The comparison of the 0.0026 gap with the 0.005 tolerance is NOT pre-registered: that tolerance belongs to the χ=64 bracket.
  Applying it to the χ=1024 edge is a forking path, so it is withdrawn as an argument; the gap is simply left uninterpreted.
- "The step did not shrink (0.021 → 0.020)" is a POST-HOC description, not a pre-specified convergence test.
- What WAS pre-specified (RESULT_BIG_INTERIM.md addendum): below 0.541 relies on the MPS-errs-high heuristic, and closeness to
  PEPS-BP is not evidence of convergence. The report sentence now states only those plus the raw numbers.

## Follow-up run completed 2026-09-25 (job log results/floquet_big_51q_hichi.log)
- χ=1024 rerun: 0.5383666430889399, identical to the value already reported (0.5384). $0.00.
- χ=2048 (job wwu3QYpFjIEXyh36): TERMINATED by BlueQubit ("Something went wrong with the request, we are investigating it").
  There is no value, and it is not a result. Not retried; the application does not depend on it.

## 74q×27c χ=1024, completed 2026-09-25. Scored only by RESULT_BIG_INTERIM.md (rules frozen while the job was running)
- mps_1024 = 0.5256639733175006 (log: results/floquet_big_74q_hichi.log). $0.00.
- χ ladder: 64 0.610 · 256 0.563 · 512 0.544 · 1024 0.526 (steps 0.047, 0.019, 0.018), the same slow tightening as 51q.
- Frozen rule (27-cycle addendum): the edge [0.086−0.005, 0.526+0.005] = [0.081, 0.531] still contains QESEM-ZNE 0.365, so the
  wording stays "consistent with". Not discriminating, and no decided value (per the 09:30 addendum).
- The value sits near the 0.53–0.55 band that the addendum names for PEPS-BP 0.541 (a 51q reference). Per the frozen rule,
  MPS and PEPS-BP share a truncation bias, so nearness is NOT evidence of convergence. research/20260925-floquet-decision-path.md's
  fit predicted v(1024)=0.531; the 0.005 match is descriptive only (a fit that "converges" is the false-convergence example).
- χ=2048: the local 24 h timeout killed the poller during the χ=2048 job ("Terminated"). No value, and no job id in the log. Not retried.
- Application impact: none. The report does not use the 74q χ=1024 value; the FORM bullet saying 74qx27c has "no classical entry" is unaffected.

## χ=2048 async retries (2026-09-26), jobs et92IhnigBLGNytE (51q) and 2U0iqV5pT3N0D5zZ (74q), free mps.cpu
Both TERMINATED by BlueQubit, $0.00, no value. With the 2026-09-25 51q attempt, χ=2048 has failed 3 of 3 times on this plan.
Treated as a service limit; not retried. The χ ladder ends at 1024 for both instances. No change to any reading.
