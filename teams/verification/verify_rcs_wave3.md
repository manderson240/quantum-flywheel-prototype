# Independent verification — rcs wave 3 (2026-09-25)

Verifier: fresh context, own code (`$TMPDIR/v/rec.py`, stdlib + numpy, json only, nice -n 10, MemAvailable 33.6 GiB,
RSS < 100 MB). The team's `mirror_analysis.py` was read only for the E4/χ² conventions after my own numbers were done.
Inputs are untracked files under refs/ (not git checkouts), so the b9dd86b0 pin could not be re-checked here; I relied on
the orchestrator's verification. The paper was read once from arxiv.org/html/2609.28657 (read-only; a transient scratchpad copy was used for text search and then deleted).

## 1. Pre-registration
- sha256(PREREG.md) = 238724009fef6ccc ec18… → prefix matches PREREG.sha16. CONFIRMED.
- mtimes: mirror_survival.json 13:38:34; PREREG.md 13:45:44; .sha16 13:45:45 (both r--r--r--). Every file in
  teams/rcs/wave3/results/ and the script are ≥ 13:50:25. No file in teams/ or refs/ was written between 13:38 and
  13:45 other than PREREG. The counts file did not exist locally before 13:38, so no earlier wave could have
  computed a mirror value from it. Consistent with K0.5. CONFIRMED (a 13:47 run cannot be timestamped
  independently, since its outputs were overwritten. Only its E4 file survives, copied to run1_first/ at 13:50:30).
- D50 disclosure (§0 K0.1–K0.6) lists the wave-1/2 derived numbers, including the d20/d32 sign pattern, and correctly
  downgrades E2/E3 to prior-informed. I grepped teams/rcs/{research,results,analysis,wave2,*.md} for partition /
  slope / Birge / leave. The only prior patch-side computations found are the wave-2 per-circuit reproduction of all
  30 d36 records (disclosed in K0.4) and the wave-1 ±5σ agreement note (K0.2). No undisclosed per-partition means,
  depth-slope fits or leave-one-out results were found. Adequate.
- E4 σ change: PREREG §5 E4 says only "if the c-bound < ln-gap − 2σ_ln (variant c)". **No formula for σ_ln is
  written.** The delta-method form sqrt((se_m B_m/F_m)²+(se_3 B_3/F_3)²) is a reasonable reading, and it matches the
  E2/E3 var_d, although E2/E3 use B3pool rather than the d36 B_3. But the code comment "that PREREG §5 E4 specifies"
  and the STATUS phrase "corrected … to PREREG's delta-method form" overstate what the text says. PREREG §6 says a
  convention change after results are seen is a POST-HOC DIAGNOSTIC and "cannot change a verdict". The change
  flipped the c_max row from "could explain" (run 1, σ_ln 0.0506: threshold 0.0964 < bound 0.0989) to "cannot
  alone explain" (σ_ln 0.0451: threshold 0.1074 > 0.0989). The change is disclosed. The c-point call ("cannot",
  bound 0.0173) and the primary §4 verdict are unchanged either way. → OVERSTATED: the honest statement is that
  the c_max row is borderline and flips with the σ_ln convention.

## 2. Independent recomputation (all reproduced)
- The 14 pooled mirror points and ses match the released values exactly (max relative deviation 0). Shots are equal over
  the 10 inputs everywhere, so sum = mean over inputs.
- The authors' fit is UNWEIGHTED OLS on log10 F (docstring of analysis/fidelity_vs_depth.py lines 9–10, read only).
  My OLS gives A 0.325714045226214, f 0.871674814249307, 2.25146e-3 per qubit per cycle, and fitted F 20–40 equal
  to the release at about 1e-15. An SE-weighted fit gives 0.34996·0.86815^d, F36 2.155e-3 (the team's value).
- d36: mirror 2.2408e-3 ± 5.572e-5, 3-patch 1.8391e-3 ± 4.085e-5 (IVW of 15 = released). Gap 4.017e-4,
  ln 0.1976. z: shot 5.814; 3-patch Birge (sqrt(26.82/14)=1.384) 5.060; both inflated 4.317, where mirror
  B_m = sqrt(Σχ²/28) = sqrt(49.23/28) = 1.326 is the 3-instance scatter over all 14 depths, as PREREG §4 defines it.
  DerSimonian–Laird 4.893. 4-patch (1.9994e-3, B 1.446): 3.75 / 3.33 / 2.76. Fit(36) residual se 1.143e-4:
  +3.97σ vs 3-patch, +0.63σ vs mirror. All match STATUS.
- E2/E3: slope 0.00765 ± 0.00811 (t 0.94, χ²_res 28.98/4); K4 t 1.46 (χ² 27.45/4). Curvature t 0.95. The team's
  "χ² 948/12" uses a log-space delta convention. The linear-space value is 938.5. Same conclusion, convention only.

## 3. Shots
- File: d40 = [360000, 360000, 360000] per instance; d4 = 30000; non-decreasing. Paper App. D: "from 3×10^4 to
  3.5×10^5 per mirror instance". The claim is CONFIRMED as a text/data mismatch (3.6e5 does not round to 3.5e5). It
  is minor and correctly scoped "on text".

## 4. Explanation tests
- CZ counts recounted independently (awk on the first field == "cz", 30 local d36 qasm files): K3 810×3, 801×6,
  792×6 (mean 799.2); K4 747×3, 720×6, 711×6 (mean 721.8). Match. E4 arithmetic checked: c 1.080e-3,
  c_max 6.186e-3, bounds 0.0173 and 0.0989. Caveat in §1 above.
- E6 recomputed: χ² 362.15/378, B_in 0.979. The input effect is not established. Supported.
- E7 leave-one-partition-out recomputed (B_3 on the 12 remaining records): z 4.09 / 3.48 / 4.39 / 4.56 / 4.10, so the
  minimum is 3.48 (drop p1). "No single partition drives the gap" is supported. The between-partition χ² 20.1/4 was
  taken from team output and not recomputed.
- E2/E3: "constant offset favoured" per the rule, but flagged unresolved because χ²_res is about 7× its dof. Honest.
- The ~14% no-d20 offset is labelled POST-HOC in STATUS item 7 and is not used for any verdict.
  My own random-effects recomputation uses DerSimonian–Laird on ln(F_m/F_3), with Birge-inflated variances B_m and
  B3pool 1.400. Without d20: Q 7.06, ratio 1.143, z 4.84, d36 3.25σ, which matches. With all six depths: Q 35.43 and
  ratio 1.086 match, but I get τ 0.118, z 1.58 and d36 1.56σ, against the team's τ 0.134, z 1.41 and d36 1.40σ. The
  τ estimator is unstated; this is a minor, post-hoc-only difference, and in both versions the offset is not
  significant when d20 is included.

## 5. Application text / STATUS
- Numbers are exact (2.24e-3, 1.84e-3, 4.3σ both inflated, 5.8σ shot only). No claim that the paper is wrong.
  "1.8–2.3e-3 range" is consistent with the paper's own "measured 1.8–2.2×10^-3 … global-fit 2.3×10^-3".
- OVERSTATED (framing): the application sentence gives only the post-hoc favourable subset ("from 24 to 40 cycles
  the mirror sits about 14% above 3-patch"). It omits that with all six depths the K3 offset is 1.09 at 1.4σ
  (random effects), and that K4 disagrees (ratio 1.04, scattered, several negative ln ratios). It is labelled
  "Exploratory", but a single selected-subset number in outward-facing text should carry the all-depth figure.

## 6. Rule compliance
- ERRATA.md is a new file inside teams/rcs/wave2/, within the team's own folder. Wave-2 PREREG and .sha16 are
  untouched. No existing results files were edited. Acceptable under TEAMS.md rule 2. ERRATA content is accurate
  (5.81/5.06/4.32 reproduced).
- Resources: run_log peak RSS 29 MB, MemAvailable ≥ 33.7 GiB. No jobs, posts or unpickling observed. The CZ counts
  come from local qasm text.

RCS WAVE3: WRONG=0 OVERSTATED=2
