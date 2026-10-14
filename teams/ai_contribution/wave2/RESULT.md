# Planted-defect benchmark: result (PREREG sha16 04570ab6a4efeb79; scored 2026-09-27 with the frozen score.py and two independent adjudicators)

## §9 frozen wording, filled with the computed numbers
- **Headline:** "On a planted-defect benchmark with a sealed answer key (3 copies of our application × 12 planted defects, 2 blind
  runs each), fresh-context AI verifiers caught 51 of 72 (0.708, 95% CI [0.524, 0.912]; 19 of 22 distinct defects caught at
  least once); our arithmetic checker caught 3 of 36; on an unmodified placebo copy the verifiers reported 11.0 false findings
  per run (14.0 counting unresolved)."
- **Recall band:** moderate.
- **Old figure:** hi = 0.912 ≥ 0.911, so the frozen wording is "Consistent with the earlier 41-of-45 figure." The margin is
  0.001, so it is not a strong confirmation.
- **Verifiers vs checker:** R_A − R_B = 0.625, and the bootstrap lower bound 0.524 > the Wilson upper bound 0.218, so
  "Verifiers outperformed the checker." Structural reason (frozen): the checker reads the application text only for the
  co-authorship string and the abstract word count.
- **False alarms:** F_up = 14.0 > 5, so "The verifiers produce substantial false alarms on unmodified text."
- **Remaining real defects:** calibration PASSED (N̂ = 9, 8, 10.25 vs true 12; all within 50%). "Capture–recapture on two blind
  runs of the unmodified application estimates 11.4 real defects (95% CI [11, 12.8]), of which about 0.4 remain unfound."
  Post-hoc caveat (labelled, not part of the frozen rule): calibration underestimated the true count by 15–33%, so treat this as a
  lower bound. The verifiers are also correlated (D3 shared /tmp; same model family).

## Per class (arm A)
- wrong_number 15/16; scope_overreach, favorable_reading, citation_overreach, cross_document_inconsistency: 6/6 each;
  overgeneralization 7/12; hidden_denominator 3/6; stale_count 2/2.
- **dropped_qualifier 0/12**: blind verifiers missed every deleted qualifier. This is the class our lessons graph shows
  recurs most in fixes (A2/A8), so it is the known blind spot.
- Plants whose number is a checker constant: 18/18; others: 33/54.

## Adjudication
- Two fresh-context adjudicators (same model, claude-opus-5-5) judged all 193 findings independently: κ = 1.0, 0 disagreements.
- No notes or source quotes were identical, so this is not copying. But same-model raters are correlated; report κ with that caveat.
- 1 auto-hit was overruled.

## Deviations affecting the reading
D2 (orchestrator unblinded by arm B after arm A launched), D3 (shared /tmp between concurrent verifiers), D4 (two adjudicators
+ κ), D5 (adjudicators judged the pre-edit application copy).
