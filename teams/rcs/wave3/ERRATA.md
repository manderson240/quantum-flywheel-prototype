# ERRATA — rcs wave 3 (appended 2026-09-25, wave 4; wave-3 PREREG.md / .sha16 and results/ untouched)

Source of findings: teams/verification/verify_rcs_wave3.md (RCS WAVE3: WRONG=0 OVERSTATED=2).

## D53 — E4 σ_ln convention was changed after the first run; PREREG gave no formula
- PREREG §5 E4 says only "if the c-bound < ln-gap − 2σ_ln (variant c)". It states NO formula for σ_ln.
- Run 1 (13:47, results/run1_first/) used σ_ln = σ_c/F₃ = 0.0506. Run 2 (13:50) used the delta-method form
  sqrt((se_m·B_m/F_m)² + (se_3·B_3/F_3)²) = 0.0451. The change was made AFTER run 1's results were seen.
- STATUS item 5 and the code comment ("that PREREG §5 E4 specifies", "corrected … to PREREG's delta-method form")
  overstate the PREREG text. Correct statement: the σ_ln form is a POST-HOC choice (PREREG §6: post-hoc
  conventions cannot change a verdict).
- Consequence for the E4 rows:
  - c-point row (bound 0.0173): "cannot alone explain" under BOTH conventions (thresholds 0.0964 and 0.1074).
    Unchanged.
  - c_max row (bound 0.0989): BORDERLINE, POST-HOC. Run 1 → threshold 0.0964 < 0.0989 → "could explain";
    run 2 → threshold 0.1074 > 0.0989 → "cannot alone explain". The row flips with the σ_ln convention and
    carries no verdict. Replace STATUS item 5's "cannot alone explain (c_max row marginal)" with
    "c-point row: cannot alone explain; c_max row: borderline, flips with the post-hoc σ_ln convention".
- The primary §4 verdict (gap persists, 4.32σ variant c) does not depend on E4 and is unchanged.

## D54 — the "~14% above 3-patch" line used the favourable d24–40 subset
- STATUS item 7 and proposed_application_text.md quoted "from 24 to 40 cycles the mirror sits about 14% above
  3-patch". This is a post-hoc subset (d20 excluded after seeing it was the only negative K3 ratio).
- With all six depths (d20–40), random effects on ln(F_m/F_3): K3 ratio 1.086, d36 offset 1.40σ (team, τ 0.134)
  or 1.56σ (verifier, τ 0.118; the τ estimator was not stated in wave 3). i.e. 1.4–1.6σ, not significant.
  4-patch disagrees: ratio 1.04, scattered (χ² 19.2/4 even without d20), several negative ln ratios.
- Correction: the 14% figure is EXPLORATORY and POST-HOC; it must not appear without the all-depth figure.
  proposed_application_text.md's "Exploratory" sentence is WITHDRAWN. Replacement, if any text is used:
  "Across 20–40 cycles the mirror/3-patch ratio averages 1.09 (1.4–1.6σ, not significant; 4-patch 1.04)."
- STATUS item 7's reading "mirror sits ~14% above 3-patch at d24–40" is to be read as post-hoc and
  subset-dependent; with d20 it is 1.4–1.6σ.

## Correction to this ERRATA (appended same day, before wave-4 counting)
- The replacement sentence above quoted "4-patch 1.04". That is the NO-d20 K4 value. With all six depths
  (posthoc_depth_scatter.json K4.all, random effects): K4 ratio 0.997 (z_re −0.04; d36 0.80σ). Corrected
  replacement sentence: "Across 20–40 cycles the mirror/3-patch ratio averages 1.09 (1.4–1.6σ, not significant);
  the mirror/4-patch ratio averages 1.00."
