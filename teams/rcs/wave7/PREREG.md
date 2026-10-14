# rcs wave 7 — PREREG: the device vs the strongest own-implementation MPS we can run at $0 (verifier issue O3)

Frozen before any wave-7 data, including controls and the calibration pilot. sha256[:16] in `PREREG.sha16`;
script sha256s in `results/scripts_at_freeze.sha256`. `runner.py` refuses to run on any mismatch.
Scripts: `common.py` (constants), `orderings.py` (candidate chain orderings), `own_mps.py` (byte-identical copy of
wave 6's own_mps.py, sha256 e9161519…), `variant_mps.py` (ordering + routing on top of own_mps), `cell.py` (one
cell per child process), `runner.py` (driver), `analyze.py` (§6–§8, frozen now), `supervise.sh`.
Circuit derivation is wave 6's `mirror_lib.py`, imported read-only and unchanged.

## 1. Question and scope
Wave 6 found the device's d36 mirror survival (2.2408e-3) above our own χ ≤ 256 MPS by 2418×. The verifier (O3)
noted that this is one implementation's number: a second free MPS (BlueQubit mps.cpu, which failed validation V2)
sat 6–8× closer, and a routing choice moved our own value by up to 27× per instance.
**Question:** what is the margin against the best of a pre-registered set of own-implementation MPS variants
(chain ordering × SWAP routing), and how does it change with χ ∈ {128, 256, 512} (and 1024 if allowed, §5)?
Scope, stated in advance and carried into every wording (§7):
- Mirror survival of U·U† is a proxy; it is not the fidelity of sampling the 36-cycle RCS circuit.
- The mirrors are derived from the released d36 instances; the shallower mirrors (d28, pilot d16/d20) are
  truncations of the same instances, not the paper's separate depth-d draws.
- No claim about the RCS advantage itself.
- "Best of N variants" is a best-of over the orderings/routings we chose and ran. It is not a bound over all MPS
  or all classical methods; a different algorithm (other truncation, other contraction) could do better.

## 2. Circuits and inputs (identical to wave 6)
- Derived depth-d mirror of instance i (i = 0, 1, 2) from `refs/rcs-nighthawk-data/data/circuits/mirror/
  d36_instance{i}.qasm` via wave 6 `mirror_lib.derived_ops(i, d)`. d = 36 is the released circuit (802 CZ).
- Input x = wave 6 `INPUTS[i][0]` (`numpy.random.default_rng(20260926)`, 61 bits per draw, inst 0..2, k 0..1).
  Control C0 asserts equality with the bits stored in wave 6's own-MPS cell files.
- Input prepared by rx(π) on each qubit with x_q = 1. Survival = exact |⟨x|ψ_trunc⟩|² (no sampling).

## 3. Instrument and candidate variants
- Engine: own numpy MPS (wave 6 own_mps.MPS): every 2-site update is an SVD truncated to χ with s ≤ 1e-10·s_max
  dropped, renormalised; mixed-canonical form. Unchanged from wave 6.
- Chain ordering (`orderings.py`; physical qubit p at (p // 10, p % 10); subgrid rows 1–8, cols 2–9):
  LOG (logical index = row raster, wave 6), RSN (row snake), CRA (column raster), CSN (column snake),
  RCM (reverse Cuthill–McKee of the 102-edge coupler graph, scipy), TWR (2-row grouped: row pairs (1,2),(3,4),
  (5,6),(7,8), column by column top-then-bottom, pairs alternating column direction).
- Routing: SB (swap-back: move the far qubit adjacent, CZ, move it back; = wave 6) and NSB (no swap-back; the
  logical→site permutation is tracked; = wave 6's post-hoc Perm routing).
- Candidates (frozen order): LOG_SB, LOG_NSB, RSN_SB, RSN_NSB, CRA_SB, CRA_NSB, CSN_SB, CSN_NSB, RCM_SB,
  RCM_NSB, TWR_SB, TWR_NSB.

## 4. Cells, order and selection (all run by `runner.py`, one child process at a time)
1. **Controls (run first; they gate everything):**
   - C0: inputs equal wave 6's (assert).
   - C3 (discriminating): for each of the 12 candidates, the 16-qubit forward-only U of instance 0 (first 36
     segments restricted to q < 16) with the ordering restricted to q < 16, χ = 256 (exact at 16 q). Pass:
     max |⟨y|U|x⟩_MPS − ⟨y|U|x⟩_statevector| < 1e-7 over 9 bitstrings y (8 from default_rng(7), plus x=INPUT16).
   - M (mutation arm; the control must be able to go red): the same check with deliberately corrupted
     bookkeeping — "g1raw" (1-qubit gates applied to site q instead of pos[q]) for every candidate except LOG_SB
     (where it is a no-op), and "book" (swap does not update the permutation) for every NSB candidate. Pass:
     every mutant gives error > 1e-3.
   - C1: LOG_SB, d36, χ = 128, inst 0–2, must reproduce wave 6 `L_chi128_i{i}_d36` survival within relative 1e-3.
   - C2: LOG_NSB, same cells, must reproduce wave 6 `posthoc_routing61.json` chi128_i{i} within relative 1e-3.
   - Failure rules (fixed now): C3 or M fails → write STOP_CONTROL, no pilot/headline cells run. C1/C2 fail at
     8 threads → rerun C1/C2 at 4 threads (wave 6's count); if they pass, every later cell runs at 4 threads and
     the 8-thread discrepancy is reported as numerical sensitivity; if they fail again → STOP_CONTROL.
2. **Calibration pilot (NOT used in any headline number):** all 12 candidates × inst 0–2 × d ∈ {16, 20} at
   χ = 64. Score = mean over the 6 cells of log10(survival).
3. **Selection (fixed now):** the variant set is LOG_SB (wave-6 baseline, always included) plus the 5 other
   candidates with the highest pilot score (ties → frozen candidate order). N = 6. Cells of candidates that are
   not selected are never run beyond the pilot.
4. **Headline ladder, frozen order:**
   a. d36, χ = 128: selected variants in selection order (LOG_SB, then pilot rank), inst 0, 1, 2 each.
   b. d36, χ = 256: same order.
   c. d36, χ = 512: variants ranked by their d36 χ = 256 three-instance mean survival, best first; all three
      instances of a variant before the next variant.
   d. d28, χ = 128 then χ = 256: selection order.
   e. d28, χ = 512: ranked by d28 χ = 256 mean, best first.
   f. χ = 1024 decision (§5), d36 only, the single best variant.

## 5. Compute, runtime, missing-point and retry rules
- Every script's first statement is the A10 guard (MemAvailable ≥ 20 GiB) exactly as in TEAMS.md. The runner
  also checks it before every cell and exits if it is not met; `supervise.sh` relaunches it every 120 s once
  MemAvailable ≥ 20 GiB. The floor is never lowered. Waits are logged in `results/runner.log`.
- One simulation process at a time (a lock file prevents two runners; cells run sequentially as child processes).
  nice 10. BLAS threads: OMP/OPENBLAS/MKL_NUM_THREADS = 8 (4 after a C1/C2 fallback, §4.1). No GPU, no quantum
  device, no BlueQubit job, $0.
- RSS: the child reads its VmRSS every 50 two-site updates; > 3072 MB → the cell is NOT RUN (rss). Peak RSS per
  cell is recorded (getrusage in the child). If MemAvailable drops below 12 GiB mid-cell, the child aborts; the
  cell restarts from scratch later and this is not an attempt.
- Deadline: 2026-10-01 20:00 EDT. A cell not started by then is NOT RUN (deadline); a running cell is killed at
  the deadline and is NOT RUN (deadline). Before each headline cell a runtime prediction is made: mean wall time
  of done cells at the same (χ, d); else 8× the mean at (χ/2, d); else the same-χ mean at the other depth scaled by
  the CZ-count ratio; else 8× the (χ/2, other depth) mean scaled likewise; else none. Prediction > time left →
  NOT RUN (predicted).
- χ = 1024 (§4.4f): best variant = highest d36 χ = 512 three-instance mean among variants complete at χ = 512.
  Predicted RSS = 4 × the maximum peak RSS over all χ = 512 cells; > 3072 MB → NOT RUN (rss prediction).
  Otherwise α = log2(mean T512 / mean T256) over the best variant's three d36 instances; predicted time for
  instance i = T512_i · 2^α; each instance runs only if its prediction fits the time left.
- Retries: a child crash (any exit other than done / RSS / memory) is retried once; a second crash → FAILED
  (missing point). Memory waits and guard trips are not attempts. A cell is never re-run to change its value.
- When every cell is terminal or the deadline has passed, `analyze.py` runs automatically and `RUN_COMPLETE`
  is written.

## 6. Measures (`analyze.py`)
Hardware per d ∈ {28, 36}: wave 3 `instance_survival` + `ivw` over the 3 instances (as wave 6):
F_hw, σ_hw, B_hw = max(1, √(χ²/2)). d36: F_hw = 2.2408e-3, σ 5.57e-5, B 1.0 (known from wave 6).
- S(v, χ, d, i) = exact survival of variant v at bond χ, depth d, instance i.
- **Best-of per instance:** B_i(X, d) = max over **every done headline cell** at depth d with χ ≤ X (all
  variants). Cumulative over χ because survival need not be monotone in χ. Including every done cell can only
  lower the margin.
- **Margin:** margin(X, d) = F_hw(d) / mean_i B_i(X, d). z(X, d) = (F_hw − F̄) / √((σ_hw·B_hw)² + σ_mps²),
  F̄ = mean_i B_i, σ_mps = sd_i(B_i)/√3.
- **χ_max(d):** the largest X ∈ {128, 256, 512} such that all N selected variants × 3 instances are done at every
  ladder χ ≤ X. The headline is margin(χ_max, 36) ("best_margin"). A partially complete χ above χ_max, and the
  single-variant χ = 1024 point, are reported separately with their own wording (§7), never as the headline.
- Also reported: every variant's value per cell; the single-best-variant margin F_hw / max_v mean_i S(v, χ_max, 36, i);
  per-instance margins; which (variant, χ) attains each B_i; the same ladder at d28 (not a verdict).

## 7. Verdict keys and frozen wording
- **MATCH:** z(X, 36) ≤ 3 for some evaluated X (ladder points, the partial set above χ_max, or χ = 1024).
  Wording: "an own-implementation MPS variant at χ ≤ <X> reaches the device survival within 3σ at 36 cycles".
- **EXCEED:** not MATCH. Wording: "the device exceeds the best of <N> own-implementation MPS variants (chain
  orderings × SWAP routings) at χ ≤ <χ_max> by factor <r> at 36 cycles", r = best_margin (4 significant figures).
  Partial / χ = 1024 addendum: "plus <M> of them at χ = <X>: factor <r_X>".
- **BlueQubit arm:** not re-run. Quoted only as "BlueQubit mps.cpu at χ = 256 (instrument validation failed (V2);
  post-hoc build-time filter; 2 of 3 instances) gives a ratio of 224.08 (Poisson 95% 88–822)" — the verifier's
  corrected pooled value. The wave-6 "> 448" χ = 128 bound and the 298.8 IVW value are not used.
- **Lead rule:** whenever our number and the BlueQubit number disagree, the less favourable (smaller) margin is
  written first. If best_margin > 224.08, the BlueQubit sentence (with its label) leads.
- Every use carries the three scope sentences of §1 (proxy; derived from the released d36 instances; no claim
  about the advantage). The word "free MPS" is not used without "own-implementation" or the BlueQubit label.

## 8. Exploratory (labelled EXPLORATORY, model-dependent; never a headline)
- Power-law fit of log10 mean_i B_i(X, d) against log10 X over the completed ladder points (fit range stated,
  number of points stated), and the extrapolated χ* at which it would reach F_hw(d).
- Margin shrink factor per χ doubling; per-variant rankings; pilot-vs-headline rank agreement; runtimes and RSS.

## 9. Prior knowledge (disclosed)
- Wave 6 values seen before this freeze: own LOG_SB d36 χ = 128/256 survivals and runtimes (≈150 s / ≈1100 s,
  RSS 87 / 288 MB at 4 threads); LOG_NSB χ = 128/256 d36 (post-hoc); χ = 64 d12/d16/d20 survivals
  (≈0.27–0.39 / 4e-4–1.4e-3 / 3e-4–9e-4); χ = 128/256 d28 survivals (≈5e-6–2.3e-5 / 4e-5–2.9e-4); the hardware table.
- Before the freeze we computed, for inst 0 d36, the number of 2-site updates per candidate (a routing count, no
  simulation): LOG_SB 5606, LOG_NSB 5806, RSN 5726/5897, CRA 6658/6242, CSN 6650/6336, RCM 7434/5852,
  TWR 5290/5930 (SB/NSB). No candidate's survival on any analysis circuit was computed before this freeze.
- Pre-freeze code tests used only non-analysis random circuits (10–12 q): identity-order SB and NSB reproduce
  wave 6's MPS and Perm bit-for-bit; random orderings are exact at full χ; both mutations produce O(1e-2) errors.
