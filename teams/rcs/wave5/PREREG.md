# PREREG — rcs wave 5: is it justified to transfer the proxy fidelity to the 918-CZ advantage circuit?

Source: arXiv:2609.28657 (arxiv.org/html/2609.28657). I read it three times on 2026-09-25 between 16:10 and 16:17 by piping
curl to stdout and filtering it through a regex sentence splitter. An excerpt file from the first read sat in $TMPDIR
and was deleted at 16:19. The harness also kept a copy of one grep output in its tool-results store, which I do not
control. Math is quoted as rendered from the HTML `alttext`.
Release data: refs/rcs-nighthawk-data and refs/rcs-nighthawk-meta (commit b9dd86b0). I read the authors' code and never
executed it.

## 0. Everything I saw or computed BEFORE freezing this file (lesson D50, exhaustive)
- K0.1 All of waves 3 and 4, including wave-4 PREREG K0.1–K0.7. In particular:
  - own counts at d36: mirror 802/802/802 CZ; K3 810×3, 801×6, 792×6 (mean 799.2); K4 747×3, 720×6, 711×6
    (mean 721.8); full d36_logical 918; full d40 1020.
  - Haar RX: 2196 in every family. CZ layers: 36. The mirror has a barrier-protected duplicate middle CZ layer of
    20 CZ; the junction-cancelled mirror has 782 CZ.
  - wave-3 d36 levels, with shot se and instance Birge B: F_m 2.2407541873352317e-3 (se 5.572416141157374e-5,
    B 1.3260228091349258); F_3 1.8390523976486782e-3 (4.0850529700543075e-5, 1.3842077369180354);
    F_4 1.999385896123157e-3 (3.216069760032846e-5, 1.4460426427130502).
  - c = 1.07997e-3 per CZ (se 4.98114e-4), c_max 6.18643e-3.
  - wave-4 STATUS item 6 "ln(F_mirror/F_full) ≈ 0.125 (c) … up to 0.718 (c_max)".
  - wave-3 depth scatter: K3 residual χ² 29.0/4, mirror χ² 948/12 about its own fit.
- K0.2 I printed refs/rcs-nighthawk-meta/data/results/fidelity_vs_depth.json from the start through the K4
  collision ratio at d28. That covers every pooled point of all three families and the fit: prefactor 0.32571,
  f 0.871675 per cycle, fitted F(36) 2.3206e-3.
- K0.3 INFORMAL LOOK AT THE DATA (so this test is NOT blind). From the d20 and d40 pooled values, (ln F20 − ln F40)/20
  gives roughly mirror 0.138, K3 0.152, K4 0.150 per cycle. K4 (fewer CZ per cycle) does not visibly decay slower than
  K3, so I expect β̂ from the slope regression (M2) to be near zero or negative. I also estimated some predictions in
  my head:
  - bound model M1 from the mirror: about 1.1e-3.
  - M3 (c): about 1.98e-3 from the mirror and about 1.62e-3 from K3 and K4.
  The informative content of this test is therefore the interval widths and the decision against the frozen
  thresholds, not the direction.
- K0.4 manifest.json: the kind counter (patched 180, mirror 42, full 10, full_executed 1) and its first and last 3
  entries: mirror d04 cz 94; full d36_logical cz 918; full d36_executed cz 918 on 120 qubits; full d40 cz 1020.
  I have not viewed any other manifest per-depth counts. Locally there are 5 instance-0 patched files per depth for
  K3 and K4 at d20–40, and all 15 at d36.
- K0.5 Circuit tails. full d36_logical and K3 d36 partition0_instance0 end in a CZ layer, then a barrier, then measure.
  The mirror d36_instance0 ends in a 1q (rz·rx·rz) layer. teams/rcs/results/final_layer_control.json (wave 1): dropping
  the final CZ layer leaves the ideal output unchanged (tvd 0).
- K0.6 qpu_usage.json read. There is no device calibration data (CZ, SX or readout error per element) in the release.
- K0.7 Paper sentences read (§1). The brief states 896 of the 918 CZ affect the output; I have not verified this.
- K0.8 Wave-4 ERRATA arithmetic: the K3 min/max sensitivity.

## 1. Paper statements (exact)
- The transfer, one sentence: "Direct verification of this set is out of reach—each ideal amplitude costs
  $\sim 10^{22}$ operations, i.e. about two days of the full reference machine, for $10^{6}$ amplitudes (Sec. III)—so
  the fidelity of the advantage configuration is taken from the two proxy estimators measured at the same depth, with
  no depth extrapolation."
- "At 36 cycles, where the proxy estimators give $F\approx 2.3\times 10^{-3}$ , we collect $M=10^{6}$ samples of the
  full, unpatched circuit."
- "the fitted $F_{\mathrm{XEB}}(36)=2.3\times 10^{-3}$ (measured $1.8$ – $2.2\times 10^{-3}$ )". Fig. 2: "The star marks
  the 36-cycle full circuit (918 CZ gates) … at the fitted $F_{\mathrm{XEB}}\approx 2.3\times 10^{-3}$ ." The star value
  is the MIRROR FIT at d = 36. The measured range [1.8, 2.2]e-3 corresponds to [K3, mirror].
- App. C, the paper's own statement that per-cycle gate count matters: "A mirror of the full circuit would contain
  more two-qubit gates per cycle than the patched circuits it is compared against (the patched variants lack the
  boundary gates), so the two benchmarks would not be exactly comparable at fixed depth—their per-cycle error budgets
  would differ." This is why the mirror was count-matched to K3.
- "Patched XEB certifies the constituent patches but is, by construction, blind to errors on the removed boundary
  couplers".
- The per-qubit error model: "with $\epsilon_{q}\simeq 2.3\times 10^{-3}$ the per-qubit per-cycle error", and "a factor
  $0.872$ per cycle [the fit of Fig. 2 ]".
- Eq. (3): $W=8\,\kappa\,N_{s}\,F\,C_{\mathrm{amp}}$; "the bounded-fidelity trick makes the work linear in $F$".
- No statement found that corrects the 918-CZ circuit for its extra gates. I read the transfer as "same n, same d ⇒
  same F". That is exact under a per-qubit-per-cycle error model.

## 2. Counting (own line parser; angles via qasm_angle.angle(), never eval; nothing unpickled)
- Statements: `OPENQASM`, `include`, `bit[..]`, `qubit[..]`, and `input float[64]` are skipped. The parser recognises
  `rz`, `rx`, `sx`, `x`, `cz`, `barrier`, and `<ident>[i] = measure q[j]`. A `_theta_` parameter is counted by name
  and never evaluated. Anything else, or a ValueError, makes that circuit MISSING.
- Per d36 circuit it records:
  - N_cz;
  - the final CZ layer: the maximal run of consecutive `cz` statements after which only barriers and measures follow.
    Its size is 0 if a gate follows.
- Circuits: full d36_logical (meta path); mirror d36 ×3; K3 d36 ×15; K4 d36 ×15. N_P = mean over each family.
- Per-cycle CZ rate z_P is the OLS slope of the family-mean CZ count on d over d ∈ {20, 24, 28, 32, 36, 40}.
  - Source: the manifest `cz` field. The kinds are mirror, patched K3/K4 (the path contains K3 or K4), and full.
  - Spot-check: my own count of the 5 local instance-0 files per depth for K3 and K4 must equal the manifest. If they
    differ, I report it and use my count for those files.
  - z_full is reported the same way.

## 3. Model: ln F_P(d) = a_P − λ_P·d, with λ_P = α + β·z_P
α is the per-cycle decay not tied to the CZ count (1q gates, idling of all 61 qubits during each layer). β is the excess
decay per CZ. The gate-count bias of transferring proxy P to the full circuit at d = 36 is
  B_P = ln F_P(36) − ln F_full(36) = β·(N_full − N_P).
This assumes a_full = a_P. SPAM and estimator normalisation are OUT OF SCOPE; the offset between the mirror and K3 in
wave 3 shows intercepts can differ.
Prediction: F̂_full,P = F_P(36)·exp(−B_P).

- M0 — the paper's per-qubit-per-cycle model (NULL): β = 0 ⇒ B = 0. It is reported, not tested; it is the transfer's
  own assumption.
- M1 — BOUND, all per-cycle decay on CZ: β_P = λ_P/z_P, using each proxy's own λ_P. It is never the headline.
- M2 — PRIMARY, slope-calibrated (cancels intercepts):
  - λ_P comes from a WLS fit of ln F_P(d) on d over the window W. Each point's se_ln = se/F; se is the authors' pooled
    shot se from fidelity_vs_depth.json.
  - se_λ,P = WLS slope se × s_P, where s_P = max(1, sqrt(χ²_P/(n_P − 2))) (Birge, per family).
  - Then a WLS regression of λ_P on z_P over P ∈ {mirror, K3, K4}, with weights 1/se_λ,P², gives β̂. se_β comes from
    the WLS covariance × max(1, sqrt(χ²_reg/1)).
- M3 — secondary, level-calibrated (wave-3 c): β = c = ln(F_4/F_3)/(N̄_K3 − N̄_K4).
  - se_c = sqrt((se_4·B_4/F_4)² + (se_3·B_3/F_3)²)/(N̄_K3 − N̄_K4), using this wave's own counts.
  - CAVEAT: M3 assumes K3 and K4 share an intercept (a_K3 = a_K4).
- Share of per-cycle decay carried by the CZ count: φ = β·z_m/λ_m, using mirror values. It is reported for M2 and M3.

Primary window W = d20–40 for all three families: a common window with no data-dependent exclusion.

Sources P for the prediction:
- mirror measured, F_m;
- K3 measured, F_3;
- K4 measured, F_4. For these three, se = shot se × the wave-3 instance Birge B, as in K0.1.
- STAR = the authors' fit value at 36, 2.3206e-3, with N_P = the mirror count. Its se is the OLS prediction se of the
  mean line at d = 36: an unweighted OLS of ln F on d over the authors' mirror points d4–40,
  s·sqrt(1/n + (36 − d̄)²/Sxx).

Uncertainty of the prediction: σ_ln,P² = (se_P/F_P)² + ((N_full − N_P)·se_β)².
The 95% interval is exp(ln F̂ ± 1.96·σ_ln,P).
For M1, se_β,P = se_λ,P/z_P; z is treated as exact.

## 4. Pre-registered tests and decision rule
- T1 (gate-count dependence detected?): M2 is DETECTED if β̂ − 1.96·se_β > 0. It is reported with a sign; a
  significantly negative β̂ is reported as "opposite sign".
- T2 (all-on-CZ bound excluded?): β̂ + 1.96·se_β < β_M1,mirror = λ_m/z_m ⇒ M1 is EXCLUDED by the proxies' own data.
- Minimum detectable β at 80% power, two-sided 5%: MDE = 2.80·se_β. It is also expressed as a bias at the mirror,
  MDE·(N_full − N_m).
- Per-model class. It is applied to M2 (primary) and M3 (secondary). M1 is reported as a bound only.
  - WITHIN QUOTED RANGE: F̂_full,P ≥ 1.8e-3 for all four sources.
  - BIASED BEYOND QUOTED RANGE: the 95% upper end is < 1.8e-3 for all four sources.
  - Otherwise: BELOW RANGE FOR SOME SOURCES, NOT RESOLVED (list them).
  - X_M = max_P B_P, and X_M,95 = max_P (β̂ + 1.96·se_β)·(N_full − N_P), i.e. "biased by at most X_M,95" in ln F.
- HEADLINE (frozen):
  - If T1 is DETECTED (β > 0): "transfer biased by the gate count in the proxies' own data", with the M2 class and F̂.
  - Else, if T2 EXCLUDES M1: "no gate-count dependence detected; the data bound the bias at X_M2,95", plus the M2 class
    evaluated at the 95% upper bias, i.e. whether F_P·exp(−X_M2,95) ≥ 1.8e-3 for each source.
  - Else: "UNDETERMINED — the proxies cannot discriminate. The bias lies in [0, M1 bound] and depends on the unmeasured
    split between CZ and non-CZ error."
  - In every case the conclusion is MODEL-DEPENDENT and is stated as such. It is never framed as an error in the paper.
    The report states what would have to be true for each reading (M0: error independent of CZ count; M2/M3: per-CZ
    excess error equal to the calibrated β).
- Variants (reported, no verdict weight):
  - V1, output-affecting counts: subtract the final pre-measurement CZ layer from full and from each patched circuit;
    the mirror is unchanged.
  - V2, junction-cancelled mirror (N_m − duplicated layer).
  - V3, windows: all families d24–40; and mirror d4–40 with patched d20–40.
  - V4, no Birge (shot se only).
  - M3 is also computed with the extremes of K3 and K4 (min, max) counts.
- Derived, model-dependent, no verdict weight: by Eq. (3), W ∝ F, so the classical-cost estimate would scale by
  F̂_full/2.3e-3.

## 5. Primary counting convention
All executed CZ (N_full 918), because noise on a diagonal final layer is still partly visible (X/Y Pauli components flip
measured bits; about 12/15 of the non-identity 2q Paulis). V1 gives the output-affecting count.

## 6. Missing / retry / resource rules
- The memory guard (TEAMS.md rule 3) is the FIRST statement of every script. The address space is limited to 1 GiB via
  resource.setrlimit. Scripts run under `nice -n 10`.
- If the guard exits, wait 60, 120, 240, 480, 600, 600… s, up to 60 min; after that the step is MISSING. The floor is
  never lowered.
- A run that raises may be retried once unchanged; a second failure makes the affected item MISSING.
- A verdict requires the full circuit, ≥ 2 of 3 mirror files, ≥ 12 of 15 K3 and K4 files, and all 6 window points per
  family. Otherwise the verdict is MISSING.
- Every run writes to its own results/run_<YYYYmmdd_HHMMSS>/ directory. Nothing is overwritten (lesson D57).
- Any convention change after results are seen is labelled POST-HOC and cannot change the verdict.
- No BlueQubit jobs, downloads, posting, or email; json and qasm are read as text only.
