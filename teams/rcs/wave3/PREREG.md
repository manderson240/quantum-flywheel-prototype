# PREREG — rcs wave 3: mirror-fidelity reproduction and the d36 mirror-vs-patch gap

Source: arXiv:2609.28657v1 (read-only HTML, 2026-09-25); release repo pinned at commit b9dd86b0.
Inputs (local, read-only): refs/rcs-nighthawk-data/data/counts/mirror_survival.json (10,733 B, git-blob SHA-1 verified
by the orchestrator), refs/rcs-nighthawk-data/data/results/patch_xeb.json, refs/rcs-nighthawk-meta/data/results/
fidelity_vs_depth.json, refs/rcs-nighthawk-data/data/layout.json (num_qubits only), and the local patched d36 .qasm
files (CZ counting only). The authors' analysis/fidelity_vs_depth.py and rcs/estimators.py were READ, never executed.

## 0. What was already known or computed BEFORE this file was frozen (lesson D50: be exhaustive)
By this team in wave 1/2, or read by me before freezing:
- K0.1 All 14 released pooled mirror points (fidelity, se) and the released fit (prefactor 0.3257140452262145,
  per-cycle 0.871674814249307, error/qubit/cycle 0.002251456460061827, fitted F at 20..40; fit(36) = 2.3205899641814787e-3),
  and the released pooled 3-/4-patch points at all depths (read in wave 1 and again now).
- K0.2 Wave-1 derived numbers (teams/rcs/research/20260925-release-vs-paper-check.md, prereg_amendments.md): the
  unweighted log-linear fit reproduces the released fit; pairwise shot-noise gaps d20 mirror−4-patch −6.0σ,
  d32 mirror−4-patch +5.4σ, d36 mirror−3-patch +5.8σ; fit(36) is +1.4σ vs mirror, +11.8σ vs 3-patch, +10.0σ vs
  4-patch; an SE-weighted refit gives 0.350·0.8681^d, F(36) = 2.15e-3.
- K0.3 Wave-2 verifier: χ² of the 15 d36 records about their IVW mean K3 26.8/14 (Birge 1.38), K4 29.3/14 (Birge 1.45);
  5.8σ becomes ≈5.1σ if only the 3-patch se is Birge-inflated.
- K0.4 Wave-1 final_layer_control.py computed a 15-qubit full-d36 sub-circuit statevector and a collision ratio
  (0.9976); wave 2 reproduced all 30 d36 patch-XEB records (not re-used here beyond the released values).
- K0.5 Of mirror_survival.json I have seen ONLY its structure: a `description` string and `depths` with keys
  4,6,…,20,24,28,32,36,40, each holding `hits` and `shots` as 3 (instances) × 10 (inputs) lists. No hit/shot VALUE
  has been printed, summed or computed. I have not counted CZ gates in any patched qasm file in this wave (wave 2's
  precheck compared CZ multisets but I use none of its numbers).
- K0.6 Paper facts (quoted exactly in §1).
Consequence: the depth-slope hypothesis (§4 E2/E3) is INFORMED by K0.2 (sign change between d20 and d32/36). It is a
confirmatory quantification of a pattern already seen, not a blind test; its evidential weight is reduced accordingly.

## 1. Paper statements under test (exact quotes, arxiv.org/html/2609.28657)
- Abstract: "Two independent fidelity estimators—mirror benchmarking and three- and four-patch cross-entropy
  benchmarking (XEB)—agree with each other at every measured depth".
- Sec. II: "we mirror a pseudo-patched circuit constructed to match the K=3 patched family gate-for-gate within ∼2%".
- Sec. II: survival "is a direct fidelity estimate for the d-cycle sequence UU†"; forward U has "d/2 cycles".
- App. C: "Each mirror circuit is executed on 10 random input strings with an equal share of the shot budget, and the
  survival probability is averaged over inputs."
- App. D: shots grow with depth "from $3\times 10^{4}$ to $3.5\times 10^{5}$ per mirror instance" (LaTeX alttext);
  Fig. 2: "Error bars are ±5σ, accounting for shot noise."
- Sec. III: "F_XEB(36)≈2.3×10^-3 (global-fit value, Table 1; measured 1.8–2.2×10^-3)".
Mirror comparison partner is therefore K=3 (PRIMARY); 4-patch is SECONDARY.

## 2. Estimator (my own implementation, formula read from rcs/estimators.py)
- Per depth d, instance i: p_i = Σ_s hits[i][s] / Σ_s shots[i][s]; se_i = sqrt(max(p_i(1−p_i), 1e−12) / Σ_s shots[i][s]).
- Pooled: IVW mean over the 3 instances, se = sqrt(1/Σw), w = 1/se_i².
- Fit: unweighted OLS of log10 F on d over the 14 pooled mirror points (closed form, not np.polyfit);
  A = 10^intercept, f = 10^slope; error/qubit/cycle = −ln f / num_qubits (61 from layout.json); fitted F at 20..40.

## 3. Reproduction targets, tolerance, verdict
- Units R1–R14: pooled mirror (fidelity AND se) at each depth vs fidelity_vs_depth.json; unit tier = worse of the two.
- R15 prefactor, R16 per-cycle, R17 error/qubit/cycle, R18–R23 fitted F at 20,24,28,32,36,40. Total 23 units.
- ρ = |mine − released|/|released|. EXACT ρ ≤ 1e−9; NUMERICAL 1e−9 < ρ ≤ 1e−6; DISCREPANT ρ > 1e−6.
- REPRODUCED iff 23/23 EXACT; REPRODUCED-NUMERICAL iff all EXACT/NUMERICAL with ≥1 NUMERICAL; PARTIAL otherwise;
  NOT REPRODUCED iff ≥ 12/23 DISCREPANT. Missing units count against REPRODUCED.
- Scope honesty (A8): the arithmetic is the authors' documented rule; a match shows only that the released points
  follow from these released counts under that rule. It says nothing about hardware provenance or whether survival
  equals circuit fidelity.
- Data-consistency checks (reported, outside the verdict):
  C1 shots equal across the 10 inputs in every (depth, instance). If not, also compute the mean-over-inputs survival
     (the paper's "averaged over inputs") and report its difference from the summed estimator in pooled-se units.
  C2 per-instance shot totals lie in [3e4, 3.5e5] and are non-decreasing in depth (paper: "grow with depth").
  C3 integers, 0 ≤ hits ≤ shots.

## 4. Gap analysis at d36 (all σ variants fixed now; no variant chosen after results)
Gap G = F_mirror(36) − F_3patch(36) (primary); same for 4-patch (secondary); also fit(36) − each patch value.
Overdispersion (Birge) ratios, inflate only if > 1:
- B_m (mirror): sqrt(Σ_d χ²_d / 28), χ²_d = Σ_i (p_i − pooled_d)²/se_i² over all 14 depths (3 instances each).
- B_3, B_4 (d36): sqrt(χ²/14) of the 15 d36 records about their IVW mean (should reproduce K0.3).
σ variants: (a) shot-only sqrt(se_m²+se_K²); (b) patch-only inflated; (c) BOTH inflated = PRIMARY;
(d) sensitivity: DerSimonian–Laird random effects on each side (τ² from its own d36 records; mirror τ² from its 3
d36 instances), with the DL pooled means and ses.
Fit(36) uncertainty: OLS residual-based se of the fitted mean at d=36 in log10 space, s² = RSS/12,
se = s·sqrt(1/14 + (36−d̄)²/Sxx), converted to linear by F·ln10·se.
Verdict (primary, variant c): |z| < 3 → "gap CONSISTENT with observed overdispersion"; |z| ≥ 3 → "gap PERSISTS beyond
overdispersion". Two-sided normal p reported. The 4-patch, fit and DL rows are reported but do not set the verdict.

## 5. Candidate explanations and what supports / refutes each
E1 Statistical (overdispersion) — §4 verdict.
E2 Constant multiplicative offset (SPAM/readout/scale) vs E3 per-cycle rate difference (effective circuits differ:
   mirror echo residual, pseudo-patched gate set, U† half). Weighted LS of y_d = ln(F_m/F_3) on (d−36), d ∈
   {20,24,28,32,36,40}; var_d = (se_m·B_m/F_m)² + (se_3·B3pool/F_3)², B3pool = sqrt(Σχ²/Σdof) of the K3 records
   about their per-depth IVW means over all six depths. Slope se multiplied by max(1, sqrt(χ²_res/4)).
   |slope|/se ≥ 3 → E3 supported, E2-alone refuted; < 2 → E2 favoured; 2–3 → inconclusive. Same for K4 (secondary).
   Report exp(slope) (per-cycle fidelity ratio) and the intercept (ln-gap at d36). PRIOR-INFORMED (K0.2).
   Descriptive: separate unweighted log10 fits over 20–40 for mirror, 3-patch, 4-patch (per-cycle f, d=0 intercept).
E4 Gate-count mismatch (paper: within ∼2%). Count CZ in the 15 K3 and 15 K4 d36 patched qasm files. Per-CZ log
   cost c = [ln F_K4(36) − ln F_K3(36)] / (N̄_K3 − N̄_K4) (pooled values, mean counts); upper alternative c_max =
   −36·ln f_mirror / N̄_K3 (all decay attributed to CZ). Bound |Δln| ≤ 0.02·N̄_K3·c (and ·c_max). If the c-bound
   < ln-gap − 2σ_ln (variant c) → a ≤2% mismatch cannot alone explain the gap; else "could explain". EXPLORATORY
   (descriptive only): per-circuit ln F vs CZ count across the 15 K3 circuits (confounded by patch geometry).
   The mirror's own CZ count is NOT testable here (needs data/circuits/mirror/d36_instance{0,1,2} — not downloaded).
E5 Fit extrapolation vs direct measurement: report fit(36) − mirror(36) and fit(36) − 3-patch in σ; curvature test:
   add a quadratic term to the unweighted OLS over the 14 mirror points, t = coef/se (residual variance, 11 dof);
   |t| ≥ 3 → single exponential misspecified. Also report the IVW-weighted-in-log fit and the 20–40-only fit at 36.
E6 Mirror input-string heterogeneity (SPAM/readout by input): χ² of the 10 input survivals about their instance
   survival (binomial var from the instance p and per-input shots), pooled over all 42 (depth, instance) cells
   (378 dof). B_in > 1.2 with p < 1e−3 → input-dependent heterogeneity present (sign vs patch not identifiable).
E7 Partition dependence of the 3-patch d36 value: between-partition χ² of the 5 partition IVW means (4 dof); and
   leave-one-partition-out pooled K3 with z (variant c, B_3 recomputed on the 12 remaining). If any leave-one-out
   gives |z| < 3 → primary gap driven by one partition. Reported, does not change the §4 verdict.
Untestable here (named, not guessed): mirror CZ count/structure; survival vs process fidelity (errors invisible at
readout); readout confusion matrices; twirling efficacy; drift ordering (shot order not retained).
A gap left unexplained by E1–E7 is reported as unexplained. No tuning until it disappears.

## 6. Missing / retry / resource rules
- Check MemAvailable before every Python run (light ones included). If < 20 GiB: wait 60,120,240,480,600,600… s,
  cap 60 min; then the step is MISSING (never lower the floor). `nice -n 10`; RSS guard 0.9 GB (abort → missing).
- A run that raises may be retried once unchanged; a second failure → the affected units are missing.
- Any rerun with changed conventions after results are seen is labelled POST-HOC DIAGNOSTIC and cannot change a
  verdict. No BlueQubit jobs, no downloads, no posting; nothing unpickled (json/qasm text only).
