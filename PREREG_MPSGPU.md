# Pre-registration: GPU MPS upper edge on the tracker candidates (frozen before the first mps.gpu job, 2026-09-28)

Binding once its sha256 prefix is in graph/gate.py PREREGS. No mps.gpu job has run when this is frozen.

## Question
Our MPS upper edge on the two live tracker candidates is still falling with bond dimension on BlueQubit mps.cpu
(results/floquet_big_*.json): 51qx30c magnetization 0.636, 0.580, 0.558, 0.538 at χ = 64, 256, 512, 1024; 74qx27c 0.610,
0.563, 0.544, 0.526. The free CPU tier terminated χ = 2048 on both (server status TERMINATED after 7.7 h). How far does the
edge fall at χ = 2048 on BlueQubit mps.gpu, and what does a GPU MPS job actually cost and take?

## Budget (Mike, 2026-09-28)
Only the account's existing credits: $24.28, expiring 2026-10-05. cost_ledger.py CAP = $25.00 ($0.72 spent before + $24.28).
estimate() takes no options and so cannot see χ; its list prices ($6.08 per 51q job, $9.37 per 74q job, about $4 per
GPU-hour) are not used for decisions. Decisions use measured cost only.

## Steps (in order; stop at the first failure)
1. **Instrument validation and cost measurement (V-GPU).** 51qx30c magnetization, mps.gpu, χ = 512. Pass if
   |mps.gpu − mps.cpu| ≤ 1e-3 (mps.cpu = 0.5583479). Record billed cost C₁ and wall time T₁. Fail, error, or not
   COMPLETED → stop; report "mps.gpu not validated" and run nothing else.
2. **74qx27c, χ = 2048** (first, because it has no classical entry other than QESEM). Predicted cost and time:
   C = C₁ · (2048/512)^3 · (74/51), T = T₁ · (2048/512)^3 · (74/51). Run only if spent + C ≤ CAP and T ≤ 7 h (the observed
   server termination point, taken as the ceiling because no limit is documented). Otherwise NOT RUN (budget/time).
3. **51qx30c, χ = 2048**, same rule with C = C₁ · 64, T = T₁ · 64, using the ledger after step 2.
The exponent 3 is fixed here (MPS contraction cost ∝ χ³; mps.cpu measured 512 → 1024 at 6.9×, i.e. about 2.8). χ = 4096 is
not run: by the same rule it costs 8× a χ = 2048 job, beyond the budget.
Backstop: a running job is cancelled if (elapsed hours × rate) would take the ledger past CAP, or at 7.5 h; the rate is
C₁/T₁ for steps 2–3 and the list rate of $4 per GPU-hour for step 1, which has no measured rate yet. A
cancelled job is reported as NOT RUN (cancelled) with its billed cost.
Server-terminated jobs: no retry (budget).

## Reporting (frozen wording)
- Cost line (always, whatever the physics): "On BlueQubit mps.gpu, χ = <χ> on the <n>-qubit candidate took <T> and cost
  $<C>; the free CPU tier ran χ = 1024 in 13.4 h (51q) / 20.4 h (74q) and was terminated at χ = 2048 after 7.7 h."
- Physics line (only if step 1 passed and the job COMPLETED): "On BlueQubit mps.gpu (validated against mps.cpu at χ = 512
  to <d>), the MPS magnetization for <candidate> is <v> at χ = 2048, continuing <χ = 64–1024 values>." It is the upper edge
  of our bracket only where PATCH_PREREG_27CYC.md was supported; it is a heuristic truncated-MPS value, not a bound, and not
  converged. Every use states the QESEM value (0.365 / 0.366) it is compared with and makes no claim that either is correct.
