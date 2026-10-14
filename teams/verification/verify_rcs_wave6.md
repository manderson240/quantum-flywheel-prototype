# Independent verification: rcs wave 6 (2026-09-26)

**Verifier:** a fresh-context agent that assumed the work was broken.

**Method**
- `analyze.py` was not read or run. `own_mps.py` was not run, and no simulation was run.
- All numbers were recomputed from:
  - the raw cell JSONs in `results/cells`, `results/cells_collapsed` and `results/local`;
  - `results/state.json`;
  - `results/bq_jobs.jsonl` at the project root;
  - `refs/rcs-nighthawk-data/data/counts/mirror_survival.json`, using my own IVW implementation.
- No network was used and no BlueQubit job was submitted.

## Summary
- Every headline number reproduces, most of them to the last printed digit. I found no false number (WRONG = 0).
- The EXCEED verdict with the own MPS as the carrier follows from the PREREG as written. The §9 V2 route was fixed before any 61q analysis data existed.
- Four OVERSTATED issues are in how the BlueQubit corroboration and the margin are presented:
  1. an IVW point estimate that is inconsistent with the interval reported beside it;
  2. the mandated "instrument validation failed" label is missing;
  3. the application lead sentence generalises "free MPS" beyond the one implementation measured;
  4. D6 states an inference as a fact.

## 1. PREREG integrity
- **sha256 prefix.** `sha256(PREREG.md)` starts with `a27ffaeac26a1ce3a5fc…`. The first 16 characters equal `PREREG.sha16` (`a27ffaeac26a1ce3`). OK.
- **Freeze timing.** `prereg_frozen_at.txt` gives 2026-09-26T12:15:11-04:00. The first wave-6 data job, V3 `bX2WQF8flRjiQOFM`, was submitted at 12:15:19 local, 8 s later. The first own-MPS cell file is dated 12:15:39. OK.
  - One job preceded the freeze: the phase0 metadata probe `XdZCyyeA6K5dSYPQ` at 12:00:41, a 12q χ=4 brickwork circuit, cost 0. It is not an analysis circuit.
  - The pre-freeze `est_probe` (estimate only) and the own-MPS timing run are both disclosed in §10.
- **Script hashes against `scripts_at_freeze.sha256`.**
  - `local_runner.py` is unchanged.
  - `mirror_lib.py` (D1), `plan.py` (D5 shots), `controller.py` (D4/D5/D8) and `own_mps.py` (D3) changed.
  - **D3 verified byte-exact.** I reverted only the disclosed D3 edit in `own_mps.py`: the gesdd try/except with the gesvd fallback, and the `svd_fallbacks` key. The result hashes to the frozen `0defa144789a21b4…`, so D3 is the only change.
  - The headline χ=256 d36 cells (written 13:43–14:20) were computed after the D3 edit, with `svd_fallbacks` = 0. Only `L_chi128_i1_d12` and `L_chi256_i1_d12` used the fallback, once each.
  - D1, D4, D5 and D8 could not be byte-verified. D1 also changed a docstring, and there is no git history.
- **Tamper evidence.** The freeze is *consistent with* the mtimes and the sha16, but it is not tamper-evident: `teams/rcs/wave6/` is untracked in git (`git status: ??`).
- **Deviations D1–D10.** For each: when it was decided, and its effect on the verdict.
  - **D1 (key endianness).** Decided after V3, a validation cell, and before any 61q analysis cell. It changes the readout only. The own MPS is unaffected. No verdict effect.
    - Side note, not counted: the sibling `teams/rcs/wave6_qpu` (orchestrator-owned) had already found the q0-leftmost convention on `mps.cpu` at 12:08–12:12, before this freeze (`wave6_qpu/results/mps.cpu_d4_bitorder_bug.json`, wave6_qpu D1). So the knowledge was in the repo 3 minutes before §5 was frozen with the wrong assumption. There is no evidence it had reached the rcs team.
  - **D2 (launch mechanics).** No data effect.
  - **D3 (SVD fallback).** Decided at the failing cell, before that cell had a value. Verified as above. No verdict effect: the fallback fired only in d12 cells, and d12 is not in any exceed run at χ=256.
  - **D4 (runtime cap).** Implementation fix; no job reached the own cap. No effect.
  - **D5 (shots 1e6 to 2e5, force_run).** Decided at 15:44. That was blind to BlueQubit 61q values: P1 had been terminated with no result. It was not blind to own-MPS values, since the own d36 χ=256 values existed from 14:20. D5 claims blindness only about BlueQubit, which is accurate. No verdict effect, because the own MPS carries the verdict.
  - **D6 (BlueQubit arm void).** Post hoc, after the collapsed 200000/200000 results. Literally applied, the BlueQubit primary would score MATCH. But the verdict carrier had already been switched by §9 at V2 (≈12:31, see §3 below). So D6 does not change the verdict; it adds a second reason for the route.
  - **D7 (F with 1e3 shots, χ=512 exploratory).** F is a feasibility fact. The announced exploratory χ=512 run was never submitted, and STATUS does not mention that it was dropped (minor, not counted).
  - **D8 (collapse filter).** Fixed at about 17:40, before any re-run result. The controller relaunched at 17:44:48, and the first re-run result was at 18:49. It was fixed *after* the first-run hits had been seen (details in §4). It affects BlueQubit only. No verdict effect.
  - **D9 (bookkeeping).** Checked: `state.json` holds `superseded_jobs` and `collapsed_jobs` per cell. There are 11 done and 55 notrun, matching STATUS.
  - **D10 (analysis departures).** None touches the own-MPS headline. D10.3 intervals are labelled post-hoc. D10.4 is labelled as reasoning, not measurement.

## 2. Headline recomputation (my code, raw files)
- **Hardware per-depth values.** IVW over 3 instances, se = √(max(p(1−p), 1e-12)/n), B = max(1, √(χ²/2)).
  - d36: F_hw = **2.2408e-3**, σ = 5.572e-5, B = 1.000. Matches.
  - d16: F_hw = **3.0386e-2** (instances 0.029983 / 0.029583 / 0.031667), σ = 4.046e-4, B = 1.564. "3.04e-2" is correct.
  - d28: F_hw = 7.9545e-3, σ = 1.481e-4, B = 1.653.
- **Own MPS, χ=256, d36.**
  - Per instance: 1.30877e-6, 2.60446e-7, 1.21035e-6. Mean **9.2652e-7**. Matches.
  - Ratio 2.2408e-3 / 9.2652e-7 = **2418.45**. Per-instance ratios 1712.1 / 8603.5 / 1851.3.
  - z = **40.19**, with σ_mps = sd/√3 and B = 1.
  - Inputs in all 120 local cells equal `default_rng(20260926)` INPUTS[inst][0]. All 120 cells are present.
- **BlueQubit, d36, χ=256 (evolved cells only).**
  - Instance 0: 1/2e5. Instance 2: 3/2e5. Total 4 hits in 4e5 shots, confirmed.
  - IVW = **7.500e-6**, σ = 4.33e-6, B_mps = 1 (χ² = 1.0). z = **39.96**. Ratio **298.77**.
  - Garwood 95% on 4 counts: [1.0899, 10.2416], which gives a ratio of **87.52–822.40**. Reported as "88–822".
  - The pooled plain rate is 1.0e-5, which gives a ratio of **224.08** (see issue O1).
- **BlueQubit, χ=128.** Instances 0 and 2 each have hits = 1 with flag `upper_bound_min_count_truncated_list`. Upper-bound mode gives F = 5e-6, so the ratio is > 448.2. That is literal PREREG (see O1).
- **d\*(χ), recomputed with the PREREG definition.**

  | χ | d* | Exceed pattern, d8→d36 |
  |---|---|---|
  | 16 | ≤ 8 | XXXXXXXX |
  | 32 | 16 | ..XXXXXX |
  | 64 | 16 | ..XXXXXX |
  | 128 | 16 | ..XXXXXX |
  | 256 | 24 | ....XXXX |

  All five match STATUS.
- **d16 claim.** Own χ=256 d16 mean = **5.0168e-2** (instances 0.05005 / 0.02065 / 0.07980) against the device's 3.0386e-2, z = −1.16. At d20: 3.871e-2 against 2.090e-2, z = −1.43. "Matches the device or does better" is fair. The point estimate is higher, but not at 3σ.
- **Other STATUS numbers.** All check:
  - V2 ratios 42.91 / 4.523 / 25.32, and BlueQubit V2 is non-monotone in χ;
  - S256_i0_d28: 247/2e5 = 1.235e-3, z = 26.14, ratio 6.44; own value 1.947e-4;
  - routing: 61q χ=256 no-swap-back mean 1.517e-7, 6.11× lower, per-instance 3.4 / 9.2 / 26.9×; 16q up to 27.8× higher;
  - BlueQubit / own on instances 0 and 2: 5.95×, or 7.94× with the pooled rate;
  - the χ=512 NOT-RUN prediction of 26719 s (α floored at 2, T_ref = 6679.85 s, × 4);
  - F: 1188 s total, 1157 s build;
  - collapsed / evolved: 7 / 4 of 11 plain 61q d36 mirror runs; build times 1.81–6.53 s against 164.8–850.0 s.

## 3. Verdict rule
**Not a reinterpretation.**
- PREREG §9 says that if V1 or V2 fails, "the own-MPS results then carry the verdict as a labelled substitute".
- V2 failed both of its criteria:
  - the BlueQubit/own ratios fall outside [0.5, 2];
  - BlueQubit is non-monotone in χ.
- The V2 results landed at 12:24–12:31 local, before any 61q analysis value existed. The first one was the collapsed run at 16:48.
- So the own-MPS carrier was fixed by a pre-registered criterion before the relevant data.
- Applying §8 to the own MPS:
  - MATCH fails: max own F(36) = 9.27e-7, far below 2.24e-3.
  - best χ = 256, whether it is chosen from the own MPS or literally from BlueQubit (7.5e-6 at χ=256 against ≤ 5e-6 at χ=128).
  - The exceed rule gives z = 40.19 > 3, so the verdict is **EXCEED**.
  - χ_max = 256: the own MPS has all 3 instances at d36.
- One caveat is worth stating: V2 shows the two MPS implementations disagreeing by up to 43×. §9 presumes the BlueQubit side is at fault. The own MPS was validated only at full χ (a 10q statevector test, and V1 = 1). Its truncated-χ values are one implementation's values (see §5).

## 4. Collapse filter (D6/D8)
- **Defensible on these data.**
  - Build times are bimodal: 1.81–6.53 s against 164.8–850.0 s.
  - Every collapsed run also has survival exactly 1 and a single distinct string. A hit-based rule would give the same classification.
- **Caveats.**
  - The 10 s threshold was fixed after the first collapsed runs' hits (200000/200000) had been seen, which is what triggered D6. It was set before any re-run result, not before any hits.
  - The later 6.53 s collapse (`VG8WGnTSEaxwprBl`) sits only 1.5× below the threshold.
  - The rule would be invalid at low χ, since genuine 16q builds took 0.57–4.6 s. It is applied only to 61q cells at χ ∈ {128, 256}.
- **What it discards.**
  - Five 61q analysis runs across 3 cells: P1_i0_χ128 run 1, M_i1_χ256 runs 1 and 2, and M_i1_χ128 runs 1 and 2.
  - Two cells are lost entirely: instance 1 at both χ.
  - Diagnostics (a) and (b) are also collapsed, but they sit outside the analysis.
- **How the inference is stated.**
  - STATUS states it correctly as "an inference, not a direct observation".
  - DEVIATIONS D6 does not (issue O4).
  - The application text does not mention the mechanism.
- Side note, not counted: the sibling wave6_qpu `mps.cpu` χ=256 d12 mirror of instance 0 (12:11, pre-freeze) returned 1000/1000 with build time 0.44 s. The own χ=256 value for that cell (k=0) is 0.9716, which predicts about 28 misses. That is early, undisclosed evidence of the same behaviour, from outside the rcs team's files.

## 5. Implementation sensitivity
- **Routing moves the own-MPS number the other way from the caveat.**
  - The application text's caveat is "SWAP routing alone moved our survival by up to ~28×". 27.8× is the **16q** figure, where survival goes up.
  - At 61q d36 χ=256 the maximum is 26.9× per instance, and survival goes *down* (mean 6.1× lower). An alternative routing would *increase* the margin.
- **The real downside risk to 2418 is the other free MPS actually tested.** BlueQubit `mps.cpu` at the same χ=256 gives 5.95× (IVW) to 7.94× (pooled) higher survival on the same two instances. That puts the margin at 224–299 (Poisson 88–822).
- **The lead sentence generalises.** "The device exceeds a free χ ≤ 256 MPS … by factor ~2400" presents the margin as a property of free MPS at χ ≤ 256. It is a property of this own implementation, and a second free MPS is about 8× closer (issue O3).
- **Accurate wording** would be:

  > "The device exceeds our own-implementation χ ≤ 256 MPS by a factor of 2418 (per instance 1712–8604) at 36 cycles. A second free MPS, BlueQubit mps.cpu at χ = 256 (instrument failed V2 validation; post-hoc build-time filter; 2 of 3 instances, 4 input returns in 4×10^5 shots), gives 224–299 (Poisson 95% 88–822). The margin is implementation-dependent."

- **The χ qualifier.**
  - "χ ≤ 256" is attached to the lead sentence and to STATUS item 4.
  - The BlueQubit "~300" sentence in the application text omits χ = 256.

## 6. Scope sentences
- **STATUS item 9:** the proxy sentence, the no-claim sentence and the derived sentence are all present.
  - Minor, not counted: "derived from the released d36 instances, which are different draws from the paper's" has an ambiguous antecedent. The released d36 instances *are* the paper's d36 circuits; only the depth-d draws differ.
- **proposed_application_text.md:** all three sentences are present and correctly worded.

## 7. Spend
- The journal holds 29 `rcs wave6` jobs and 1 phase0 probe. All are on `mps.cpu`.
- 24 of them have `done` cost 0.0. Five cancelled jobs have no `done` record, so their cost is null: kUToY3H5K2Ya5eeX, G1bju9sxfaZ2Dhxh, 65spVJwN1kABGWSa, qtLl3lJPF9DxdG64 and 6i58BaXnYErprfx1. That passes the rule. DEVIATIONS' statement that they "reported cost 0.0" cannot be confirmed from the journal.
- No gpu or quantum device appears. OK.
- **Prominent note (outside the target).** The journal also holds `wave6_qpu` jobs, which match a grep for "wave6". One of them is a paid `quantum` job, `Z83WrUyTxMvrOqaQ`, costing **$0.72**, from `teams/rcs/wave6_qpu` (orchestrator-owned, user-approved up to $3 in its own PREREG).
  - It is not part of `teams/rcs/wave6`.
  - Wave 6's "Every job cost $0.00" is true of wave 6 but false of "rcs wave 6*" as a glob.

## 8. Rounding and presentation (A8)
- 2418 (2418.45) is exact.
- "~2400" rounds down, which does not flatter.
- "88" rounds 87.52 up, a trivial flattering direction; not counted.
- z values are exact.
- The flattering choice is the estimator, not the rounding (O1).

## Issues
- **O1 — OVERSTATED. The BlueQubit point estimate is inconsistent with its interval.**
  - STATUS and the application text report the ratio 298.8 (IVW, 7.500e-6) next to the Poisson range 88–822.
  - That range is centred on the pooled 4/4e5 = 1.0e-5, which gives a ratio of **224.08**. The team computed this (`intervals.json: ratio_plain_point`) but did not report it.
  - At 1 and 3 hits, IVW with binomial se down-weights the larger count. The headline therefore carries the more flattering of two computed values.
  - Same family: "χ = 128 ratio > 448" treats truncated-list count bounds (≤ 1 hit each) as the survival. That is literal PREREG, but a 95% bound on ≤ 2 pooled hits in 4e5 gives a ratio of only > ~142.
- **O2 — OVERSTATED. The mandatory §9 label is missing.** PREREG §9 requires every BlueQubit result to be labelled "instrument validation failed (V1/V2)". The phrase appears 0 times in STATUS.md and 0 times in proposed_application_text.md. The BlueQubit ~300 therefore reads as corroboration from a validated second instrument.
- **O3 — OVERSTATED. The application lead sentence.** "A free χ ≤ 256 MPS" borrows the BlueQubit (free-service) framing. It omits the §3-required label "own-implementation MPS" in the verdict sentence and generalises a single implementation's margin. The routing caveat that follows ("up to ~28×") quotes the 16q figure, whose direction does not threaten the margin. The one measured threat, a second MPS about 6–8× better, is not framed as a margin caveat. Suggested wording is in §5.
- **O4 — OVERSTATED. D6 states the mechanism as fact.** D6 says "BlueQubit mps.cpu simplifies U·U† (inverse-gate cancellation) before simulation" and "the plain mirror is never evolved as a circuit". Four evolved runs contradict the latter. D8 corrects only "void" to "intermittent", and keeps "cancellation" as the mechanism without calling it an inference. STATUS hedges correctly.
- **WRONG.** None. Every recomputed number matches.

RCS WAVE6: WRONG=0 OVERSTATED=4
