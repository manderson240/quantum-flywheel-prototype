# Independent verification: ai_contribution wave 1 (headroom probe for Exp A)

Verifier: independent adversarial pass, 2026-09-25. I modified no team files. I ran no BlueQubit jobs.
MemAvailable was about 37 GiB, so I ran a small quimb re-simulation (linuxbrew Python 3.14.3, `nice -n 10`,
`OMP_NUM_THREADS=1`, `PYTHONDONTWRITEBYTECODE=1`, peak RSS 381 MB). My scripts live in the session scratchpad
(`recompute.py`, `ho.py`, `resim.py`). They re-derive every number from `runs_*.jsonl`. They do not import `analyze.py`.

## Claims table

| # | Claim | Team value | Mine | Status |
|---|---|---|---|---|
| 1 | sha256(PREREG.md)[:16] | bd2ee90798aa480a | bd2ee90798aa480a | CONFIRMED |
| 2 | Frozen before any truncated-run data | freeze 11:31:02 | PREREG.md born 11:30:57, .sha16 at 11:31:02, run.log born 11:31:08, runs_grid.jsonl born 11:31:10. instrument_check.py stores only exact diffs and cost/timing. | CONFIRMED (from mtime/birth times; deleted earlier runs cannot be ruled out) |
| 3 | Frozen code and data unchanged after data | 6 code + 5 data sha16 | All 11 sha16 values match PREREG. runner/analyze .pyc files were compiled at 11:30:09, before the freeze. | CONFIRMED (no rule change) |
| 4 | Runs / failures | 2,352 runs, 0 failed | 561+1640+145+6 = 2352, 0 failed | CONFIRMED |
| 5 | Frozen verdict | INCONCLUSIVE (instrument) | Bond detector fired (1,499 runs) and cutoff detector fired (dev χ64 ε=1e-4, 3e-4 end at 64). Frozen rule gives INCONCLUSIVE. | CONFIRMED (correct application) |
| 6 | Every violation follows a χ drop | 1,499/1,499 | Tighter test than the team's own: all **7,785** excess layers are the *first layer of a cycle whose χ dropped*, and each is ≤ the previous cycle's χ. The grid had 0 violations. | CONFIRMED |
| 7 | Mechanism: truncation acts only on bonds a gate touches | explanation | Correct. `apply_gate_raw(..., max_bond=…)` truncates only the bond(s) split by that 2-q gate and by its swap path. 1-q gates and untouched bonds keep their old dimension until a later gate crosses them. Cost is summed after every layer, so the excess is paid for; there is no hidden budget leak. | CONFIRMED |
| 8 | Cutoff detector mis-specified (χ cap binds) | profile differs, cost lower at every ε | Recomputed from the grid records. In all 3 regimes, at every ε in {1e-4…1e-2}, the χ64 bond profile differs from ε=0 and the cost is lower. Final bond stays at 64 for dev ε ≤ 3e-4 and HO ε ≤ 3e-3, so the detector fired and the cap was binding. | CONFIRMED |
| 9 | Dev Δ, median seed, L8/16/32 | +0.028/+0.026/+0.033 | +0.0278/+0.0264/+0.0333 | CONFIRMED |
| 10 | Dev Δ, best seed | +0.039/+0.061/+0.036 | +0.0387/+0.0606/+0.0360 | CONFIRMED |
| 11 | Held-out primary Δ | −0.067/+0.002, −0.051/−0.051, +0.027/−0.322 (4/6 negative, worst −0.32) | identical | CONFIRMED numerically; the direction is robust, the magnitude is OVERSTATED (P1) |
| 12 | Dev log10 MAE, schedule vs constant | worse at L16 (−0.061) and L32 (−0.034) | −0.0608, −0.0336; L8 is **+0.013** (the schedule is better) | CONFIRMED in STATUS; application text OVERSTATED (P2) |
| 13 | Cycle-16 error rises | 0.21→0.30 (L16), 0.17→0.22 (L32) | I re-simulated L16 and L32 B*/S* myself. Per-cycle mean \|err\| is identical to percycle_posthoc.json: 0.2101→0.2982 and 0.1707→0.2198. Med, MAE and cost are bit-exact. | CONFIRMED |
| 14 | Hill-climb | +0.007 at L8, "matched B* exactly" at L16 and L32 | +0.0066, +0.0002, 0.0000. It used only **44/57/44** evals of 187, *fewer* than Q_k = 69/115/155. | CONFIRMED (to rounding). PREREG's "more search than B" did not happen; STATUS item 7 acknowledges this. |
| 15 | Library default within 0.002 of best constant | ≤0.002 | 0.0021/0.0001/0.0023 | CONFIRMED (to rounding) |
| 16 | Engine reproduces 81 exact values to ≤1.9e-14 | 1.86e-14 | Re-ran dev exact myself: 27/27 values, max diff 1.86e-14 (cost 1.29e10, 96 s). I did not re-run the other 54. | CONFIRMED (partial, 27/81) |
| 17 | Random Q_k per seed | 69/115/155 | 69/115/155, all seeds reached Q_k | CONFIRMED |
| 18 | "median error 6–17%" (application text) | 6–17% | Absolute \|err\| 0.057–0.170 on expectation values in [−1,1]. It is not a relative %. | OVERSTATED (wording, P4) |
| 19 | Metric gaming (median rewards starving late cycles) | general claim | Holds at L16/L32. Does **not** hold at L8: S* is better at cycles 6–16 and `late_worse=false`. S* also starves *early* cycles (L16 cycle 4: 0.042→0.072). | OVERSTATED (P3) |

## Ranked problems

**P1 (most important): the size of the held-out loss, and the HO2 cells behind it, are metric artefacts. The direction is not.**
On HO2 (`ho_2.4_0.9`), the median log10 error is non-monotone in cost:
- library χ8 scores −1.678, χ16 scores −1.539, χ32 scores −1.660, χ64 scores −1.786;
- χ20/ε=1e-2 scores **−1.829 at cost 0.94M**, which beats library χ64 at 89M.

The HO2 frontier is therefore a cheap, heavily truncated setting at L16 and at L32. The "worst −0.322" at L32 is that artefact.

Re-scoring against a frontier chosen by MAE gives the same *direction*: 4 of 6 cells are still negative.
- HO1 is uniformly negative: −0.058, −0.084, −0.038.
- HO2 is +0.060, +0.078, −0.062.

So "does not transfer" is robust. The −0.32 magnitude and the specific HO2 cells are not. HO2's non-monotone metric is a second defect, separate from late-cycle starvation, and the team did not report it. It should be fixed in any re-registration, for example by requiring the metric to be monotone in cost on the held-out regimes before using them.

**P2.** The application text says the gains "reversed ... under mean error". That is true at L16 and L32 only. At L8 the dev MAE favours the schedule (+0.013).

**P3.** The metric-gaming claim is generalised from 2 of 3 levels. The mechanism is best stated as "the median ignores the tails (early and late cycles)", not "late cycles" only. The direction of the recommendation is still right: use a per-cycle max, MAE, or monotone χ.

**P4.** The application text puts the exploratory (detector-free) result first. It never labels that result exploratory or post-hoc, and "formally inconclusive" comes only afterwards. It also calls absolute error "%". STATUS.md, by contrast, separates the frozen verdict (item 3) from the post-hoc/exploratory readings (items 4–8) cleanly.

**P5 (design, acknowledged).** PREREG claims the 187-eval hill-climb makes a NO-HEADROOM verdict strong. In practice it converged in 44–57 evals from B*, a local optimum. The descriptive negative therefore rests on 3 seeds of random search. STATUS says so. The application text does not overclaim this point.

## Verdict checks
- The pre-registration held. The hash matches, the code hashes match, the freeze came before the first grid run, and no scoring rule was changed after data.
- INCONCLUSIVE is the correct application of the frozen rule.
- The post-hoc diagnosis of both detectors is correct. The bond detector fired on a real but harmless per-gate truncation latency: exactly one layer, and it was costed. The cutoff detector assumed ε would lower the final bond below the χ=64 cap, which is false when the cap binds.
- The descriptive "no headroom" reading is kept separate from the frozen verdict in STATUS.md. It is less clearly separated in proposed_application_text.md.
- Dev-side conclusion (no schedule reaches Δ ≥ 0.10 at any level): CONFIRMED.

## Processes
`ps` in this shell shows only 6 processes, so pid-namespace blindness applies and the team's worker state is **UNKNOWN**. run.log shows `PHASE_DONE heldout` and a verdict at 11:46:49, and the post-hoc files were written by 11:49:43. Every phase appears finished. I killed nothing.

The OVERSTATED count is P1–P4 (rows 11, 12, 18, 19).

AI WAVE1: WRONG=0 OVERSTATED=4
