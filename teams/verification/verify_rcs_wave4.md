# Verification — rcs wave 4 (gate-count bias test), 2026-09-25

Verifier: independent adversarial pass. Nothing in teams/rcs/ modified. No jobs, downloads to disk, posts, .env, or
unpickling. Own counter written first (scratchpad `vcount.py`, own regex parser, own angle parser, no eval),
`nice -n 10`, `ulimit -v 1 GB`, MemAvailable 37–39 GiB at every run. Inputs: release commit
b9dd86b016743465ebc97fb9f6677f4a251a3baa (refs/rcs-nighthawk-meta/COMMIT_SHA.txt). Paper read-only via curl piped
to stdout (never written to disk).

## 1. PREREG — CONFIRMED
- `sha256(PREREG.md)` = 9f4b9c16548a8339bc60… → sha16 9f4b9c16548a8339 matches PREREG.sha16. Both files are mode r--r--r--.
- mtimes: PREREG.md 16:01:06, PREREG.sha16 16:01:10; first run output (results/run1_missing/) 16:02:20; code fix
  16:02:50; final results 16:03:56; post-hoc 16:05:25. No result file predates the freeze. (That no mirror gate line
  was READ before 16:01 cannot be proven from mtimes; mirror files were fetched 15:53 — plausible, unverifiable.)
- Prior exposure K0.1–K0.7 disclosed, including manifest shallow mirror counts and the analytic 918 derivation, and
  the prereg itself states the SIGN is prior-informed. Good practice.
- σ_ln formula stated in advance (§3): sqrt((se_m·B_m/F_m)²+(se_3·B_3/F_3)²); I recompute 0.0450868, thr 0.107389;
  BORDERLINE rule with σ' 0.0506 (thr' 0.096362) stated in §4.5. All confirmed.

## 2. Independent counts — ALL CONFIRMED
| circuit | CZ | Haar RX | prep RX | RZ | CZ layers |
|---|---|---|---|---|---|
| mirror d36 inst 0/1/2 | 802/802/802 | 2196 | 61 (`_theta_k_`) | 4392 | 36 |
| K3 d36 ×15 | 810×3, 801×6, 792×6; mean 799.2 | 2196 | 0 | – | 36 |
| K4 d36 ×15 | 747×3, 720×6, 711×6; mean 721.8 | 2196 | 0 | – | 36 |
| full d36_logical | 918 | 2196 | 0 | 4392 | 36 (29/22 alternating) |
- full d40 = 1020 (grep). manifest.json `cz` agrees for all 33 d36 mirror/patched entries and full d36.
- Every CZ run is a matching (disjoint qubits) in all circuits.
- "Exact gate-by-gate inverse": after removing the 61 prep RX, barriers and measures, the 7390-op body is a
  palindrome under inversion — op k and op n−1−k same gate/qubits, rz/rx angles negated (|Δ| ≤ 1e-9 mod 2π):
  0 mismatches in all 3 instances. CONFIRMED.
- Junction: forward layer 18 (20 CZ) and inverse layer 1 are the same edge set, separated ONLY by 2 barriers (no
  1q layer between). So the logical circuit contains a back-to-back CZ·CZ = I pair protected by barriers. CONFIRMED.
- Mirror layer sizes forward 29,18,28,20,21,16,24,18,25,22,26,19,23,19,26,19,28,20 then exact reverse.

## 3. Bias model and verdict — CONFIRMED
Recomputed from the frozen constants: g 0.197562; c 1.07997e-3; se_c 4.98114e-4; c_max 6.18643e-3; D 6.29850.
ΔN (K3 − mirror) = cz −2.8, rx 0, layers 0 → G_c −0.00302, G_cmax −0.01732, G_all 0.
- |G_cmax| = 0.0173 vs thr 0.1074 (σ 0.0451) and thr' 0.0964 (σ' 0.0506): correct. (Note: 0.0506 is the σ, the
  alternative threshold is 0.0964 — the STATUS gets this right.)
- Rule step 1 (ΔN_k ≤ 0 for every k) fires at both thresholds → "CANNOT EXPLAIN (wrong way)", no flip → no
  BORDERLINE. Correct application of the frozen rule; count-corrected gap 0.2006 / 0.2149 recomputed.
- Pre-registered sensitivity vs K3 min/max (§3) is NOT reported in results/STATUS (omission). My computation: vs
  810 → ΔN +8, G_c 0.0086, G_cmax 0.0495, G_all 0.0622 → step 3 CANNOT EXPLAIN at both thresholds; vs 792 → wrong
  sign. Verdict unchanged, but the sensitivity should be added.
- Post-hoc junction variant (782 CZ): ΔN 17.2, G_c 0.01858 (9.4% of g), G_cmax 0.1064, G_all 0.1356 → G_c < thr,
  G_all ≥ thr (and ≥ thr') → PARTLY at both. Recomputed exactly. The variant was pre-registered as a reported
  variant, but applying the rule to it is post-hoc; it is labelled "POST-HOC … No verdict weight" in the script,
  JSON and STATUS. Correctly labelled. Note G_cmax 0.1064 sits just under thr 0.1074 and above thr' — i.e. under the
  all-decay-on-CZ bound, a compiler-cancelled junction would be a near-borderline explanation; this is the
  main residual risk to the headline and depends on native compilation (untested).

## 4. 802 vs 918 — correctly described; held back appropriately
- 918 − 802 = 116 (14.5%) confirmed. STATUS item 6 labels it secondary, model-dependent, no verdict weight; it is
  absent from proposed_application_text.md. Holding it for a separate pre-registration is right — not overclaimed.
- Paper, exact: mirror = "a state-preparation layer, a forward random circuit U of d/2 cycles, its exact inverse U†,
  and a readout" and "we mirror a pseudo-patched circuit constructed to match the K=3 patched family gate-for-gate
  within ∼2% while remaining connected". App. C: "A mirror of the full circuit would contain more two-qubit gates
  per cycle than the patched circuits it is compared against". The paper ALSO states how the 918-CZ star is
  treated: "the fidelity of the advantage configuration is taken from the two proxy estimators measured at the
  same depth, with no depth extrapolation", and Fig. 2: "The star marks the 36-cycle full circuit (918 CZ gates) …
  at the fitted F_XEB ≈ 2.3×10^-3". So STATUS's "its treatment … not found (UNKNOWN)" is imprecise: the treatment
  IS stated (proxy value applied directly, no gate-count correction discussed). Recommend replacing UNKNOWN with
  that quote. Not counted as WRONG (no explicit correction exists, which is presumably what was meant).

## 5. Deviations
- DV1: run1_missing/gate_counts.json contains 32 circuits (15 K3, 15 K4, 2 full) and ZERO mirror entries; errors
  "unsupported gate 'meas'" for all 3 mirrors. count_gates.py mtime 16:02:50 = after run 1 (16:02:20), before any
  mirror count existed. Current MEAS regex accepts any register name; no other rule visibly affected. CONFIRMED
  (the prior code version is not preserved, so "no other rule changed" is taken on trust; my independent parser
  reproduces every count, so it is immaterial).
- DV2: the non-compliant 16:02:50 output was overwritten by the 16:03:51 rerun; no copy was kept, so identity
  CANNOT be verified from artifacts. DEVIATIONS says "identical apart from rss_mb"; STATUS item 8 says
  "byte-identical results" — self-contradictory (rss_mb is inside bias_test.json) and unverifiable. Immaterial to the
  science (deterministic code, counts independently reproduced), but OVERSTATED as written.
- Nothing else undisclosed found: RSS 17 MB, no jobs/downloads in wave-4 files.

## 6. proposed_application_text.md
- Numbers exact (802; 792–810; same Haar and layer counts; 61-gate prep; 4.3σ matches wave-3 z 4.317).
- It is a pre-registered primary result, so no "exploratory" label is needed; the 918 observation and the junction
  variant are correctly kept out.
- OVERSTATED: "A gate-count mismatch therefore cannot explain the … gap" is stated unconditionally. The team's own
  post-hoc variant shows the conclusion rests on the executed circuit keeping the barrier-protected duplicate CZ
  layer (if cancelled → PARTLY, G_cmax 0.106 ≈ thr) and on the assumed logical-to-native equivalence. Suggested
  fix: "…cannot explain the gap in the released logical circuits (assuming the duplicated junction CZ layer is
  executed, as the barriers indicate; native compilation not checked)." "Slightly more gates" is a mean statement
  (the mirror has fewer CZ than the 810-CZ K3 members).

## 7. Provenance of frozen constants, STATUS item 7, wave-3 ERRATA — CONFIRMED
- F_m/se_m/B_m, F_3/se_3/B_3, F_4/se_4/B_4 in PREREG K0.1 / count_gates.py equal wave3/results/gap_d36.json to all
  printed digits; f = 0.871674814249307 = reproduction.json "mine" = "released". z (both inflated) 4.3173 ✓.
- Manifest: I checked the 3 mirror + 30 patched + full d36 rows (34) against my counts; the team's 35th (d40 row) was
  not inspected in the manifest (d40 = 1020 confirmed by grep of the qasm only).
- STATUS item 7 recomputed with my parser: per-qubit exposure mirror − K3 mean min −1.4, max +3.2, mean +0.0918;
  102 couplers in the union; max |usage diff| 1.4. CONFIRMED.
- ERRATA D53: wave-3 PREREG sha16 238724009fef6ccc still matches its file. E4 text: "< ln-gap − 2σ_ln (variant c)"
  with NO σ_ln formula (variant c is defined only for the linear gap) — premise correct. run1_first/
  gate_count_bound.json has σ 0.050594 and c_max call "could explain"; final has 0.045087 and "cannot alone
  explain"; c_max bound 0.098884 lies between thr 0.0964 and 0.1074 → flip confirmed. c-point bound 0.01726 ✓.
- ERRATA D54 / correction: posthoc_depth_scatter.json K3.all re_ratio 1.0855, z_re 1.41, d36_z_with_tau 1.40,
  τ 0.134; K4.all re_ratio 0.9975, z_re −0.043, d36 0.80σ. All ERRATA numbers confirmed. (The verifier's 1.56σ/τ 0.118
  comes from the wave-3 verification report, not re-derived here.)

## Findings summary
Counting rule for OVERSTATED: a claim stronger than the artifacts support, including an unverifiable claim that the
team's own files contradict.
- WRONG: none. All counts, structural claims, arithmetic, and the verdict reproduce independently.
- OVERSTATED (2): (a) STATUS "byte-identical" rerun — unverifiable and contradicted by DEVIATIONS; (b) application
  text drops the logical-vs-executed/junction caveat.
- Minor/omissions (not counted): pre-registered K3 min/max sensitivity not reported (verdict unchanged); paper's
  treatment of the 918-CZ star mislabelled "not found".

RCS WAVE4: WRONG=0 OVERSTATED=2
