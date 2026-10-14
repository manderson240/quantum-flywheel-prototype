# Verification — rcs wave 5 (transfer bias of proxy fidelity to the 918-CZ circuit)

Verifier: independent adversarial pass, 2026-09-25. File reads plus small numpy arithmetic on
`fidelity_vs_depth.json`, `manifest.json` and the team's `transfer_bias.json`. No circuits were re-parsed and no team
script was re-run. Memory guard (4 GiB floor) was the first statement of the verifier script; MemAvailable was about
14 GiB. No existing file was modified. No jobs, downloads, posts or email were made. Nothing was unpickled.
Paper: arXiv:2609.28657, read-only via arxiv.org/html (curl to stdout, regex search).
Pinned data commit: `refs/rcs-nighthawk-meta/COMMIT_SHA.txt` = b9dd86b016743465… (matches).

## 1. PREREG integrity — CONFIRMED (with one caveat)
- `sha256(PREREG.md)[:16]` = beed370d62a9d547, matching `PREREG.sha16` and the run JSON `prereg_sha16`.
- File times (mtime): PREREG.md 16:19:56, PREREG.sha16 16:20:02, transfer_bias.py 16:21:10, run_start 16:21:29.974,
  results written 16:21:38.
- Caveat: `teams/rcs/` is untracked in git. The freeze is attested only by mtime, r--r--r-- permissions and the sha
  file, not by a commit. This is consistent, but it is not independently provable.
- Prior exposure is disclosed exhaustively (§0 K0.1–K0.8). That includes the informal slope look (K0.3), which
  explicitly makes the test non-blind and predicts β̂ ≤ 0. My naive d20–40 slopes reproduce it (0.1380, 0.1520, 0.1498).
- Formulas are stated in advance and applied as written. Checked against the code:
  - M0–M3;
  - Birge per family, max(1, √(χ²/(n−2)));
  - regression se × max(1, √χ²_reg);
  - σ_ln;
  - T1/T2;
  - MDE = 2.80·se;
  - the class rule;
  - the headline branch;
  - variants V1–V4 and the M3 count extremes.
- The headline took the frozen second branch (T1 NOT DETECTED, T2 EXCLUDED). The frozen M2 class ("WITHIN QUOTED
  RANGE") is reported as frozen, not reworded.
- V1 note: the code also subtracts the mirror's final layer, which is 0 because the mirror ends in a 1q layer. This is
  equivalent to "mirror unchanged".

## 2. Paper quotes — CONFIRMED verbatim
- "…so the fidelity of the advantage configuration is taken from the two proxy estimators measured at the same depth,
  with no depth extrapolation." The quote is exact, including the preceding clause (10^22 operations, about two days,
  10^6 amplitudes).
- App. C ("Mirror construction details", "Pseudo-patched forward circuit" paragraph): "…their per-cycle error budgets
  would differ." Exact.
- The other quoted lines are exact:
  - "blind to errors on the removed boundary couplers";
  - ε_q ≃ 2.3×10⁻³ per-qubit per-cycle;
  - 0.872 per cycle;
  - "fitted F_XEB(36)=2.3×10⁻³ (measured 1.8–2.2×10⁻³)";
  - Fig. 2 star "(918 CZ gates)".
- A search for "per-CZ", "gate count" and "boundary gates" finds no statement that corrects the 918-CZ transfer for its
  extra gates. The only gate-count remark is the cycle-picture versus gate-count-picture coincidence for the
  count-matched mirror. The team's reading of this is fair.

## 3. Numerical recomputation — ALL REPRODUCED
My independent numpy WLS used the authors' pooled points and se, with the manifest CZ means:

| quantity | team | verifier |
|---|---|---|
| λ mirror (d20–40, Birge 4.10) | 0.1396±0.0050 | 0.1396±0.0050 |
| λ K3 (Birge 3.78) | 0.1497±0.0064 | 0.1497±0.0064 |
| λ K4 (Birge 6.74) | 0.1508±0.0089 | 0.1508±0.0089 |
| z mirror / K3 / K4 / full (CZ per cycle) | 22.36/22.20/20.05/25.50 | 22.357/22.200/20.050/25.500 |
| β (M2) | −0.0037±0.0051 | −0.00371±0.00507 (χ²_reg 1.39) |
| 95% CI | [−0.0137, +0.00624] | [−0.01365, +0.006238] |
| M1 bound λ_m/z_m | 0.006246 | 0.006246 |
| T2 margin | 7e-6 (0.1%) | 7.28e-6 (0.12%) |
| MDE | 0.0142/CZ = 1.65 ln | 0.0142 = 1.648 ln (bound 0.724) |
| c (M3) | 1.08e-3±0.50e-3 | 1.07997e-3±4.98114e-4 |
| star F(36), f | 2.3206e-3, 0.871675 | 2.32059e-3, 0.871675 |
| V3a (d24–40) | M1 NOT EXCLUDED | hi 0.01026 > bound 0.00663: not excluded |

The authors' `fit` block (prefactor 0.32571, f 0.871675, F(36) 2.32059e-3) agrees with my unweighted OLS.

F_full(36) predictions (units e-3):

| source | M0 | M3 | M1 bound | M2 point | at M2 95% bias |
|---|---|---|---|---|---|
| mirror | 2.24 | 1.98 | 1.09 | 3.45 | 1.09 |
| K3 | 1.84 | 1.62 | 0.83 | 2.86 | 0.88 |
| K4 | 2.00 | 1.62 | 0.46 | 4.14 | 0.59 |
| star | 2.32 | 2.05 | 1.12 | 3.57 | 1.13 |

X_M2,95 = 1.224 ln (K4). This matches STATUS items 5 and 6 exactly.

The M3 claim that the 3- and 4-patch values are one number by construction is CORRECT. With c = ln(F4/F3)/(N3−N4),
we have ln F4 − c·N4 = ln F3 − c·N3 identically, so F3·e^{−c(918−N3)} ≡ F4·e^{−c(918−N4)}. Both give 1.618e-3, and
these are one datum, not two confirmations.

Other checks:
- "12–19% lower": e^{−0.125} = 0.882 and e^{−0.212} = 0.809. OK.
- "14.5% more CZ": 918/802 = 1.1446. OK.
- ERRATA arithmetic: G_c 0.00864 = c·8 and G_cmax 0.04949 = c_max·8. OK.
- Counts (JSON): full 918 with final layer 22 (896 output-affecting); K3 range [792, 810]; K4 range [711, 747];
  spot-check 80/80 agree.

## 4. Honesty
- **Verdict framing is honest.** It is labelled MODEL-DEPENDENT throughout, with no claim of error in the paper, and it
  states what must be true under each model.
- **The knife-edge exclusion is reported honestly.** It is not presented as a positive exclusion: the margin is 7e-6
  (0.1%), exclusion fails under V3a, and power is nil (MDE > bound). The "honest reading" is kept separate from the
  frozen headline.
- **The M2 "WITHIN QUOTED RANGE" class** is correctly flagged as resting on a negative, non-significant β.
- **OVERSTATED (1), proposed_application_text.md.** "could lie anywhere from 2.3e-3 down to about half that" is the
  mirror/star-anchored all-on-CZ bound (ln 0.72), but the text does not say it is source-specific.
  - The same bound from K3 gives 0.83e-3.
  - From K4 it gives 0.46e-3.
  - The team's own frozen X_M2,95 is 1.224 ln (0.59e-3 from K4).
  - The header does label the text "EXPLORATORY, model-dependent", and STATUS item 7 labels "(ln 0.72 mirror)". The
    application text alone, however, gives a narrower range than the team's analysis supports.
  - Fix: add "(mirror-anchored all-on-CZ bound; patch-anchored sources give lower values)".
- **"Only per-element error data at run time can settle this."** This phrase appears nowhere in the wave-5 or ERRATA
  files, so it is not counted.
  - The premise holds as far as the team reports: K0.6 says the release has no per-element calibration. I did not
    re-read qpu_usage.json.
  - The proxies also demonstrably cannot discriminate (MDE 1.65 ln > bound 0.72).
  - "Only" is too strong. A gate-count-varied benchmark at fixed depth, such as a mirror of the full circuit, would also
    settle it. Say "per-element error data or a gate-count-varied benchmark at fixed depth".

## 5. Rule compliance
- **A10 guard.** In transfer_bias.py the guard is the first executed code (import sys; MemAvailable; exit if < 20 GiB),
  split into 3 statements by the formatter, as the team disclosed. The run JSON records 20.62 GiB at start and peak
  RSS 15 MB. RLIMIT_AS is 1 GiB. In posthoc_c_by_depth.py the guard is the first statement.
- **Post-hoc recorded as NOT RUN.** This is recorded in `results/POSTHOC_NOT_RUN.json` and STATUS item 8. It truthfully
  notes the guard exited at 16:23 (13.6 GiB < 20) and that the wait loop was stopped on instruction. No posthoc output
  directory exists.
- **One run, own directory.** There is a single run in `run_20260925_162129/`, and nothing was overwritten. Wave-4
  PREREG, STATUS and results mtimes all predate 16:06; only ERRATA.md (16:18) is new, as claimed.
- **Leftover processes: UNKNOWN.** `ps -e` shows only 5 processes, so it is pid-namespace blind in this sandbox. A grep
  for transfer_bias/posthoc found nothing, but that is not evidence of absence.

## Findings summary
- WRONG: none. All numbers, quotes, formulas and the by-construction M3 claim check out.
- OVERSTATED: the application text's unlabelled "down to about half" range (§4).
- Notes (not counted):
  - the PREREG freeze is attested by mtime and sha only (untracked in git);
  - "only per-element data" is absent from the files and would be too strong if used;
  - process check UNKNOWN.

RCS WAVE5: WRONG=0 OVERSTATED=1
