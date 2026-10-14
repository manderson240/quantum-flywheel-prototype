# STATUS: ai_contribution wave 2, planted-defect benchmark. Built and frozen; NO verifier has run.
1. Built: 4 neutral copies (3 planted + 1 sealed placebo), 167 files each: 12 plants per planted copy, 36 slots, 22 distinct plants in 9 lessons.json classes. Scripts: `build.py`, `score.py`, `run_armB.py`, `VERIFIER_BRIEF.md`, `RUNBOOK.md`.
2. Freeze: `PREREG.sha16` = `04570ab6a4efeb79`, frozen 2026-09-27T13:14:24-04:00 before the corpus existed. `key.json` sha256 `58be7944…`, `assignment.json` `d4183be8…`, `pool.json` `b708e458…` (full hashes in the PREREG Addendum).
3. Arm-B finding, from reading the source: `check_claims.py` reads the application text only for the co-authorship string and the abstract word count, never for a number. Frozen prediction: 3 of 36 caught.
4. Checks: scorer self-test 22/22 pass, and a scorer mutation turns 7 red. On the real key, all 36 plants were locatable; the positive control gave 35/36 AUTO_HIT (1 goes to the adjudicator) and the negative control 0/36.
5. Arm-B baseline probe on the originals: 135 checks, ALL CLAIMS VERIFIED. No arm-B copy run and no verifier run has been done.
6. The orchestrator's additions are in the PREREG before the freeze: capture–recapture (Chapman on the 2 placebo runs, calibrated on the planted copies where N = 12) and the seeding validity threat.
7. Not done fully: the class mix only partly matches lessons.json (wrong_number is 22% of plants against 16%); post-stratified recall covers the gap. The Mills, Eick and Briand–El Emam citations are unverified.
8. Blindness is procedural: the placebo is findable by grep, so do not open `corpus/` or `SEALED/` until all 8 runs are done. Deviation D1 (a MISLOCATED verdict) was logged before any run.
9. Orchestrator commands: `RUNBOOK.md` (integrity checks, 8 arm-A runs, arm B, independent adjudication, then `score.py`).
AI WAVE2 BUILD: copies=4 planted_total=36 prereg=04570ab6a4efeb79
