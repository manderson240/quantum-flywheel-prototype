# Wave 7 post-deadline addendum: result (ADDENDUM_POSTDEADLINE.md, sha16 9cfffd32ce2bcd1d)

Run: 2026-10-05. POST_DEADLINE_FINISHED logged 2026-10-04 22:32:02, all 9 addendum cells done (results_post/cells/).
Merge: wave7 scripts + results copied to ../wave7_merged_scratch (same directory depth, so common.ROOT resolves),
addendum cells added as done, unmodified analyze.py run there (rc 0). Output: results_post/merged_analysis.json,
stdout results_post/merged_analyze_stdout.txt.

CHECK FIRST (pre-registered): χ = 128 and χ = 256 ladders for d28 and d36 are byte-identical (JSON equality) to the
confirmatory results/analysis.json; verdict and d36 headline identical (EXCEED, χ_max 256, margin 2418.45, z 40.19).
Disclosed: the EXPLORATORY power-law fit (d36/exploratory_powerlaw) differs in the 15th significant digit
(chi_star 2020.1797354223859 -> ...838; slope ...2057 -> ...20575), i.e. floating-point summation order. It is not a
χ = 128/256 output and does not enter any reported number. Only other differences: the new χ = 512 cells and their
ladder entries, and the auto wording "plus 2 of them" -> "plus 5 of them".

Completeness: all 5 distinct variants × 3 instances done at χ = 512 (LOG_SB, TWR_NSB, CRA_NSB, RCM_NSB, LOG_NSB).
Pre-registered report sentence: "completed after the pre-registered deadline (deviation W4): at χ ≤ 512 the factor is
312.6" (z = 40.0). The three added variants did not beat the existing best at χ = 512 (per-variant mean survival at
χ = 512: CRA_NSB 1.06e-6, LOG_NSB 1.36e-6, RCM_NSB 1.68e-6), so the factor is unchanged from the partial value.
It never replaces the χ ≤ 256 headline. In the application since 2026-10-05 (FORM_ANSWERS wave-7 bullet), verified by two-family
rounds (reviews/verifier_batchd{1,2}_20261005.md, reviews/batch_d_20261005/); round 2 clean from both families.

Council 2026-10-05 control (reviews/council_qpu_20261005/ADJUDICATION.md R1): the ORIGINAL confirmatory analysis re-run
on 2026-10-05 without the addendum cells (../wave7_control_scratch) reproduces the merged power-law values exactly
(slope 3.7714292584120575, χ* 2020.1797354223838); every other field equals the confirmatory analysis.json. The
15th-digit change comes from the run environment (Oct 2 vs Oct 5), not from the merge. The merged run is identical to its
same-day control on every χ ≤ 256 output.
