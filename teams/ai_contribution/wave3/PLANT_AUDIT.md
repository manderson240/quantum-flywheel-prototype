# Plant-strength audit (wave3)

Auditor: fresh-context agent, 2026-09-27. Read-only. Inputs used: plant records in SEALED/key.json,
SEALED/originals/ (for context only), and the cited project sources. The corpus/ directory and
SEALED/assignment.json were not opened. The report gives no copy mapping.

Question asked of each plant: with the qualifier deleted, is the planted text false or overstated as a
reader would take it? Values were recomputed from the raw sources wherever possible.

## Qualifier-deletion plants (9)

| id | class | verdict | reason (source) |
|---|---|---|---|
| Q05 | dropped_qualifier (depth) | STRONG | The bracket is tight only at 1 cycle. Recomputed from `results/tracker_floquet51_sweep.json`: the width (MPS minus PP δ=1e-4) is 0.0005/0.006/0.016 at cycle 1, 0.025-0.097 at cycle 2, and 0.35-0.45 at cycles 13 and 16. |
| Q15 | dropped_qualifier (scope) | STRONG | The 3.3e-15 match covers only 8 slices (k=8-16 qubits). No 70-qubit amplitudes were computed, because the 2^31 message exceeds the 2^24-entry cap (`research/20260924-rgs-stabilizer-method.md` lines 12-20; FORM_ANSWERS "validated on slices"). |
| Q07 | dropped_qualifier (post-hoc status) | STRONG | `pilot/PILOT_PREREG.md` lists the arms as grid, random, rule, agent and blind, plus hindsight references. It has no verifier-gate re-analysis, and `check_claims.py` labels the check "post-hoc gated agents". Unlabeled, the sentence sits inside the "Verdict (pre-registered)" paragraph and reads as a confirmatory result. |
| Q02 | dropped_qualifier (parameter regime) | STRONG | Recomputed from `results/otoc2_echo_4x4_seeds7-11-13.json`: the MPS max error is 0.847 at χ=4, 0.399 at χ=16 and 0.029 at χ=64. The matching Pauli-path "max error 1.000" covers all δ, so the unqualified 0.029 reads as the maximum over all χ, which is false. |
| Q08 | dropped_qualifier (conditions) | STRONG | FORM_ANSWERS lines 150-151 say Nighthawk availability is still to be confirmed with the program (Premium/Flex only), "so the QPU plan defaults to Heron". Without the condition, Nighthawk reads as committed. |
| Q11 | dropped_qualifier (conditions) | STRONG | `results/bq_jobs.jsonl` shows job Z83WrUyTxMvrOqaQ (device quantum, "wave6_qpu mirror d4") with cost 0.72. The report states "Prototype cost $0.72 (one QPU job)". The claim that every run cost $0.00 is false. |
| Q16 | dropped_qualifier (scope) | WEAK | `check_claims.py` does recompute values from `results/*.json`, but against hard-coded expectations. It reads the report text only for a few string checks, and the report itself says it "reads almost none of the text". The "recomputes each stated number" wording is the same in the original, so the plant's only change is removing the disclosure that text-to-number agreement rests on review. The overstatement is the implied machine check. |
| Q10 | dropped_qualifier (scope) | WEAK | `xcheck_local27.py` is a from-scratch numpy simulator, and it matches BlueQubit at 24/24 points (max 1.77e-5; `results/xcheck_local27.json`). It imports `build`, `observables` and `patch` from `floquet_patch_oracle`, so the definitions are shared. The planted text is literally true; it only hides a common-mode independence caveat. |
| Q09 | dropped_qualifier (conditions) | TRUE | `teams/rcs/wave3/results/gap_d36.json` gives z = 5.81 (shot-only), 5.06 (patch-inflated) and 4.32 (both inflated, the primary "c" verdict). The unqualified 4.3σ is the most conservative figure, so dropping the method label cannot overstate the gap. |

## Control plants (6), each expected to be clearly WRONG

| id | class | verdict | reason (source) |
|---|---|---|---|
| N01 | wrong_number | WRONG (confirmed) | 38 + 57 = 95, not 89. `check_claims.py` recomputes 89 disagreements = 38 right + 51 wrong from the pilot records. |
| N02 | wrong_number | WRONG (confirmed) | From `refs/tracker_issues_20260924.txt` (#249 66325 s, #245 870 s), 66325 / 870 = 76.2, not ~67. |
| N03 | wrong_number | WRONG (confirmed) | From `results/tracker_submissions_2026-09-23.json`, the OLE 49x1296 values are 0.619-0.943, so the span is 0.62-0.94, not 0.62-0.84. |
| C01 | citation_overreach | WRONG (confirmed) | `PATCH_PREREG.md` is the intermediate-size Floquet bracket pre-registration. The RCS draft is `DRAFT_PREREG_RCS.md`. |
| C02 | citation_overreach | WRONG (confirmed) | FORM_ANSWERS cites tensor-network Monte Carlo as Goto, Suwa & Todo, arXiv:2609.12466. arXiv:2609.05598 is matrix-product belief propagation. |
| C03 | citation_overreach | WRONG (confirmed) | FORM_ANSWERS gives the δ caution as Gharibyan et al., arXiv:2507.10771. arXiv:2510.25838 is the peaked-circuits paper. |

## Process deviation

The read-only inline `python3 -c` checks ran without the MemAvailable guard the brief prescribes. No files were written except PLANT_AUDIT.md, and _audit_scratch/ was not needed.

## Notes for the scorer

- Q09 cannot measure qualifier detection: the deletion makes the claim less informative, not stronger. A
  verifier that does not flag it is correct.
- Q16 and Q10 are omissions of caveats about method, not false statements. A miss there is a weaker failure
  than a miss on the six STRONG plants.
- Side observation, not a plant: `check_claims.py` asserts "every recorded job cost 0.0". That is true only
  for the result files it reads; `bq_jobs.jsonl` records a $0.72 QPU job. The report's own "$0.72" line
  handles this correctly.

PLANT AUDIT: STRONG=6 WEAK=2 TRUE=1 (qualifier plants only)
