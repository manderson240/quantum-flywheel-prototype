# Proposed amendments to DRAFT_PREREG_RCS.md (rcs team, wave 1, 2026-09-25)

The draft itself is not edited. Each amendment cites the evidence in `teams/rcs/`. The first two are **blocking**:
the draft cannot be frozen as written.

**Evidence files:**
- `results/structure_d36.json`: cut profiles, 7 orderings
- `results/c2_band_profile.json`
- `results/final_layer_control.json`
- `results/summary_checks_raw.json`
- `results/download_sets.json`
- `research/20260925-release-vs-paper-check.md`
- `research/20260925-classical-attacks-lit.md`

---

**A1 (blocking): align the memory budget with the charter, and state what it costs.**
- The draft (§A Budget, §F) allows < 4 GB RSS per process. TEAMS.md rule 3 caps local processes at about 1 GB.
- The draft's own estimates are about 0.7 GB of tensors at χ=1024 and about 2.6 GB plus SVD workspace at χ=2048.
- Replace the budget and ladder with:
  - "local ladder {64, 128, 256, 512}; χ=1024 is attempted once, under a whole-run RSS abort guard of 0.95 GB (checked every cycle, not by an early-cycle probe, since real bond growth lags the crossing bound); an abort is a missing point; χ=2048 is never run locally."
- Carry this change through the rest of the draft:
  - **(a)** S-T2 and S-T1 are judged at the highest rung completed within budget.
  - **(b)** Gate G(b) is evaluated at that same rung, 512 or 1024, not at 1024/2048.
  - **(c)** χ=2048 exists only in the vendor arm. That arm has no truncation diagnostic, so it can never satisfy a criterion.
  - **(d)** Restate the §F band at the rung that will actually run. With the draft's own model (lossy events from `structure_d36.json`, 896 CZ, row-major), the counts are 2,523 events at χ=512 and 2,353 at χ=1024. The resulting F̃(36):

    | ε | χ=512 | χ=1024 |
    |---|---|---|
    | 0.5% | 3.2e-6 | 7.5e-6 |
    | 1% | 9.7e-12 | 5.4e-11 |
    | 2% | 7.3e-23 | 2.3e-21 |

    This model holds ε fixed across χ, which is optimistic at lower χ. The T2 gap at χ=512 is therefore 2.85 decades (log10(2.3e-3/3.22e-6)) even at ε = 0.5%. [Corrected wave 2, D37: was "≥ 2.9".]
- **The structural bound barely separates the rungs above 512.** The first-bond saturation cycles are 5 (χ=512) and 7 (χ = 1024, 2048 and 4000). The mid-bond crossing count exceeds log2 χ at cycle 8 for χ = 1024, 2048 and 4000.
- Alternative: request a one-off user exception for one χ=2048 local run. That is a user decision and cannot be assumed.

**A2 (blocking): integrity check by git blob SHA-1, on .qasm files.**
- `manifest.json` `sha256` hashes the **.qpy** only. The d36 .qasm is `e2e72760…`, while the manifest has `2bb17672…`. The draft's run-time check would therefore reject every .qasm file, or silently check nothing.
- Replace it with: "each file is checked against its git blob SHA-1 in the GitHub tree at b9dd86b0 (`results/repo_tree_b9dd86b0.json`); mismatch aborts."
- Use `full/d40_logical.qasm`, not `.qpy`. It is parsed by our strict line grammar (`analysis/structure.py`, angles via `qasm_angle.angle`, no eval), so no qiskit deserialiser is in the trust path.

**A3: define the cycle-d snapshot BEFORE cycle d's CZ layer.**
- d36 ends with a 22-CZ layer followed only by Z measurement. That layer leaves the output distribution unchanged (exact statevector control: TVD 0.0; interior-layer negative control TVD 0.50).
- Truncations during that layer would lower F̃ spuriously.
- Define F̃(d) as the accumulated product after cycle d's single-qubit layer and before its CZ layer. F̃(36) then covers 896 CZ.
- Recompute the §F lossy-event counts on 896 CZ, row-major:
  - χ=1024: 2,353 (was 2,516, stated as "about 2,520")
  - χ=2048: 2,189 (was 2,345, stated as "about 2,350")
- At ε = 1% this moves the §F predictions up by about 0.7 decades. The prediction band must be restated before freezing.

**A4: pin the ordering decision to measured cut profiles.** Static crossing counts over 896 CZ:

| ordering | max crossings | total crossings |
|---|---|---|
| row-major | 80 | 3,806 |
| row-snake | 80 | 3,823 |
| col-major | 81 | 3,938 |
| col-snake | 81 | 3,965 |
| anti-diagonal | 114 | 4,563 |
| RCM (bandwidth-minimising) | 141 | 4,696 |
| random control | 536 | 19,517 |

- Row-major stays primary; column-major stays descriptive.
- Record that RCM was tested and is worse. Bandwidth is not the right criterion, because the lattice is already bandwidth 8.
- Keep the draft's "no other ordering" rule. The draft's "81/81, about 3,980" figures are the 918-CZ counts and are reproduced exactly (3,978).

**A5: add a per-bond exactness control to Stage 0 (instrument check, full 61 q).**
- Crossing-count bound: while a bond's cumulative crossings are ≤ log2 χ, its discarded weight is zero in exact arithmetic.
- In complex64 the SVD leaves a noise floor. Discarded singular values are about ε_mach·σ_max, with ε_mach ≈ 6e-8. Up to χ of them are discarded, so per event w ≲ χ·(6e-8)² ≈ 1e-12 at χ=256.
- Freeze the threshold as follows. Before the run, measure the maximum per-event w over cycles 1–2 at every rung; truncation is known to be zero there. Set the threshold to max(1e-9, 100 × that maximum).
- Any w above the threshold before a bond's listed cycle (`structure_d36.json → saturation_cycle_per_bond`; for χ=256, every bond through cycle 3) = implementation bug; abort.
- It is a bound, not a prediction: truncation may start later than listed, never earlier. The check is falsifiable at full size without any exact reference.

**A6: state that the ε̂ transfer from calibration to target is an extrapolation in entanglement deficit.**
- C2 bands (23 q, rows 1–3 and 6–8) have a qubit cap of 11 ebits, reached by cycle 7. C1 patches (15–21 q) have caps ≤ 10.
- At the target, row-major, the cap is 30. The deficit (cap − log2 χ) is 20 at χ=1024, while no calibration circuit can exceed a deficit of about 8–9 (C2 at χ=4–8).
- Add: "ε̂ is reported as a function of deficit on C1/C2; its value at deficit ≈ 20 is an extrapolation and is labelled so; S-T2/S-T1 use the target's own F̃ (Zhou product), not a transferred ε̂." This strengthens the draft's H-est caveat without changing the criteria.

**A7: add a threshold sensitivity row (descriptive only).**
- The measured d36 anchors disagree pairwise by up to 5.8σ in shot-noise units (mirror vs 3-patch). The fitted 2.32e-3 is 11.8σ above the 3-patch value.
- An SE-weighted refit of the mirror data gives F(36) = 2.15e-3.
- Keep the primary threshold at 2.3e-3. Report Δ also against 2.24e-3 (mirror), 2.15e-3 (weighted fit), 2.00e-3 (4-patch) and 1.84e-3 (3-patch). None of these can turn a miss into S-T2.

**A8: Stage-0 control — fix the aggregation rule before computing.**
- Reproducing `patch_xeb.json` (partition 0 of K3/d36/instance 0 = 1.6349e-3) needs the paper's Eq. 1 normalisation and the rule that combines 5 partitions × 3 instances into the 1.839e-3 3-patch point.
- Pre-register: "the aggregation rule is copied from `analysis/compute_patch_xeb.py` and `rcs/estimators.py` (read, not executed) into the frozen PREREG before our reproduction runs".
- Also reproduce the d36 3-patch and 4-patch points to 1e-6 relative.
- File needs: download set A-min, 42 files / 15.6 MB (DOWNLOAD_REQUEST.md).

**A9: keep the T1 wording conservative, and name post-selection.**
- A T1 (score) statement must say whether it assumes the √F relation (Ayral, 2207.05612) and/or top-k post-selection (the lever used in 2406.18889).
- Neither is validated at 61 q. A full-size score cannot be computed (about 1e22 operations per amplitude), so any T1 number stays "predicted".

**A10: add a sibling pre-registration (separate file, not this one) for the memory-realistic contraction-cost estimate.**
- The literature scan ranks batched/sliced TN as the class most likely to move the 110-year figure, in either direction.
- The authors' repo already contains `sparse_batched_cost` and `run_memory_sweep.py`, with no released results.
- A path-search-only estimate is $0 locally. Because it would have to run under the 1 GB cap, it needs its own budget decision; cotengra searches on width-64 networks may not fit.
- The direction is unknown, so pre-register both outcomes. That must happen before any search.

**A11: correct the facts in the draft's disclosure section (§D).**
- §D says `layout.json` and `patch_xeb.json` were "read", but no local copy exists under `refs/rcs-nighthawk-meta/` (15 files, 265 KB).
- Either record where they were read (GitHub API, in-memory) or re-read them after download approval.
- [Corrected wave 2, D36: the earlier claim of a size discrepancy is withdrawn.] The scoping note says "about 360 KB raw"; the apparent size of the local copy, measured in wave 2 (find -printf %s), is 356,177 B for the 14 data files (356,218 B including COMMIT_SHA.txt), which agrees. The 265 KB figure was compressed ZFS on-disk usage, a different measure. The file count (14 data files) also agrees, and all 14 match the pinned git blob SHA-1s. The first half of A11 (no local copy of `layout.json` / `patch_xeb.json` at the time) stands.
