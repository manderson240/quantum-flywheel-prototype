# Deviations from PREREG (sha16 04570ab6a4efeb79)

**D1, 2026-09-27, after the freeze, before any verifier or arm-B copy run, and before any score was seen.**

This entry clarifies the adjudication vocabulary; the code is unchanged. A finding can identify a planted defect
correctly but fail the §5 location rule, for example because its quote is under 8 characters or because a
multi-sentence quote overlaps most with a neighbouring sentence. Such a finding is neither PREEXISTING (the
original text is fine) nor FP (the source does contradict the planted text).

- The adjudicator records these findings with verdict `MISLOCATED`.
- `score.py` counts false positives only for the literal verdict `FP`, so MISLOCATED findings are excluded from the false-positive figures without any code change.
- The orchestrator reports their count from `score.json` (`non_plant` entries).
- Headline recall is unaffected: under the frozen rule, these findings do not credit a plant.

## D2 (orchestrator, 2026-09-27, before any arm-A result existed)
Arm B's output (runs/armB/*.txt) unblinded the orchestrator to which copy is the placebo: one copy passed all checks,
the other three failed the co-authorship check. All 8 arm-A verifiers had already been launched with identical,
path-only briefs, so arm-A blinding is intact. The orchestrator is now UNBLINDED for adjudication. Adjudication therefore
goes to an independent fresh-context adjudicator (PREREG §5–6), as planned; the orchestrator does not adjudicate.
Arm B result: the same frozen prediction held (co-authorship plant caught in 3 of 3 planted copies = 3 of 36; placebo passes).

## D3 (orchestrator, 2026-09-27): shared-/tmp contamination risk between concurrent verifiers
Verifier A_run2 reported that a helper script it had written at /tmp/claude-1000/mk.py was overwritten by another concurrent
verifier's script under the same name (it cited report.html:82). Each run wrote VERIFICATION.md only into its own package
(A_run2's file ends FINDINGS=26 and matches its hand-back), so the reports are not mixed up. But the verifiers were not fully
isolated: a run could have seen another run's helper code. This is a threat to independence for the capture–recapture
estimate, and must be stated with it. Future runs: give each verifier a private scratch directory.

## D4 (ai_contribution team at the orchestrator's instruction, 2026-09-27, after the runs, BEFORE any adjudication)

This follows an external review. It sets two adjudication rules and how the adjudication input is built, before
any adjudicator has seen anything.

- (i) Two independent fresh-context adjudicators each judge the full packet. Agreement between them is reported as Cohen's kappa (`adjudication/merge.py`). Disagreements go to a third adjudicator. The third adjudicator's verdict is final when it matches one of the first two; otherwise the item is UNRESOLVED, which is never a hit.
- (ii) Every PREEXISTING verdict must quote the source value that contradicts the text, recomputed where possible. `merge.py` rejects a PREEXISTING verdict without one.
- The packet is built mechanically by `adjudication/make_packet.py`:
  - one row per arm-A finding (193 rows), with run id and copy kind stripped;
  - opaque random item ids;
  - order shuffled with a random seed, recorded in `adjudication/SEALED/map.json`.
- `located_options` uses score.py's frozen location rule.
- `nearby_options` is a mechanical addition. It covers plants sharing at least 20 characters with the quote, in any of the three documents, and only for findings that locate nothing. It exists so that the D1 MISLOCATED verdict can be applied at all. It gives no credit toward recall.
- The PREEXISTING `defect_id` namespace is taken from adjudicator 1, then 2, then 3, each prefixed. Ids from different adjudicators can split one real defect into two. That would bias the capture–recapture overlap m low and N̂ high, and it is to be reported with the estimate.

## D5 (orchestrator, 2026-09-27, before any adjudication)
The live application was edited after the benchmark build (D72 checker-scope fix, and confirmed fixes from external review 3).
Adjudicators must judge PREEXISTING against the application as it was at build time, so each adjudicator gets a private staged
copy of corpus/copy_C (byte-identical to the pre-edit originals, verified with cmp; the orchestrator already knew this was
the placebo, per D2). The packet and brief go in `_adjudication/`, with a private `_scratch/` directory, per the D3 lesson.
The brief's path prefix was rewritten to the staged directory; no other text was changed.


## D187 (found 2026-10-06): the freeze hash covered only the header
See FREEZE_ATTESTATION.md. The transcripts show no post-freeze edit to the protocol body; the post-hoc body hash is recorded there.
