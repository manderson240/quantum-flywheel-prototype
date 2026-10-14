# PREREG: planted-defect benchmark for the AI-verification claim (team ai_contribution, wave 2)

Frozen 2026-09-27, before any corpus copy exists. `PREREG.sha16` = the first 16 hex characters of the sha256 of this
file's bytes up to and including the line `## Addendum (written after freeze; excluded from PREREG.sha16)`.
Anything below that line was written after the freeze and is not covered by the hash.

## 0. Claim under test and why

The application says: "fresh-context AI verifiers caught 41 of 45 defects later confirmed in our own claims; our
arithmetic checker caught none". The denominator is defects we found ourselves, so recall has no external
ground truth. This benchmark supplies one. Known defects are planted into copies of the real application text,
and a sealed key is written before any verifier runs. Blind verifiers (arm A) and the checker (arm B) are then
scored against that key. An unmodified placebo copy (arm C) measures false alarms.

## 1. Methodological grounding (citations NOT verified by this team)

The orchestrator named these sources. This team has not checked them against primary text, and none may be cited
in the application until the orchestrator has verified them.

- Error seeding: known faults are seeded and the fraction found estimates detection effectiveness (Mills, 1972).
- Capture–recapture estimation for software inspections: Eick et al., ICSE 1992; later Briand, El Emam et al.

This design uses both:

- recall on seeded defects (sections 5–7);
- a two-sample Chapman (bias-corrected Lincoln–Petersen) estimate of real defects remaining in the unmodified application, from the overlap of two blind runs on the placebo (section 7.4). The estimator is itself calibrated on the planted copies, where the true N is known.

## 2. Defect catalogue

The catalogue is `SEALED/pool.json`, sha256 `b708e458e367b69d1030bc2ea5f261707f3a1f2b2217b2c0b10ea8bd3983c820`, written by `build.py --write-pool`. `build.py` (sha256
`37a3c16ffe46ae3e6149dec48434785a5b135300b456d2c38aae3b32b13054e7`) holds the same pool in code, and `--build` refuses to run unless the two are identical. `score.py`
imports its text normalisation from `build.py`, so this hash also freezes the scorer's segmentation. It holds 25
source-validated plants in 11 strata. Each plant records:

- `id`, `stratum`, `class`, the transformation `rule`, and the document;
- the exact original and planted strings;
- `mirror`: verbatim duplicates that receive the same edit;
- the source files that prove the planted text wrong;
- `checker_constant`: whether `check_claims.py` holds a hard-coded constant for that number;
- the auto-scoring patterns and the adjudication statement of the right problem;
- `cross_doc_tell`: whether another application document still states the original, so a document diff alone could reveal the plant;
- the arm-B checks credited.

The key adds `support_file_tell` per plant. It lists every non-document corpus file that contains the plant's
normalised original span verbatim, which would let a verifier diff instead of verify. In the pre-freeze
`--validate` run no plant had such a file. Recall is stratified by this flag as well.

Every `class` is a class in `graph/lessons.json`. Class counts in that file (snapshot D01–D71, 71 defects):

| class | count |
|---|---|
| fix_introduced_defect | 11 |
| wrong_number | 7 |
| scope_overreach | 6 |
| dropped_qualifier | 6 |
| overgeneralization | 6 |
| favorable_reading | 5 |
| citation_overreach | 4 |
| cross_document_inconsistency | 4 |
| stale_count | 3 |
| hidden_denominator | 2 |
| single_source_truth | 2 |
| unsourced_number | 2 |
| unstated_definition | 2 |
| unmeasured_mechanism | 2 |
| unit_conflation | 1 |
| process classes | 8 |

The process classes are rule_after_data, missing_required_output, silent_instrument_failure, primed_reviewer and
rule_deviation. They are not plantable in text. The benchmark plants the 9 text classes shown in section 8.

Strata, transformation rules and per-copy quotas (12 per planted copy):

| stratum | class(es) | rule | quota | candidates |
|---|---|---|---|---|
| S01 arm-B control | dropped_qualifier | delete the one string `check_claims.py` reads (co-authorship disclosure, report §7) | 1 | 1 |
| S02 number, checker has a constant | wrong_number, stale_count | change a number for which `check_claims.py` holds a constant | 1 | 4 |
| S03 number, no checker constant | wrong_number | change a number `check_claims.py` has no constant for | 1 | 3 |
| S04 qualifier deleted | dropped_qualifier | delete a scoping qualifier | 1 | 3 |
| S05 overgeneralisation | overgeneralization | generalise from 2 of 3 settings / beyond tested depth | 2 | 2 |
| S06 scope overreach | scope_overreach | extend a result to a target or scale it was not shown for | 1 | 2 |
| S07 favourable reading | favorable_reading | read a failed test, a CI excluding 0, or closeness as a win | 1 | 3 |
| S08 reference swap | citation_overreach | swap a section reference | 1 | 2 |
| S09 direction flip | wrong_number | flip a comparison direction | 1 | 2 |
| S10 cross-document | cross_document_inconsistency | make form and report disagree | 1 | 2 |
| S11 hidden denominator | hidden_denominator | drop the words that restrict a count's denominator | 1 | 1 |

**Builder rules (asserted in `build.py`):**

- the original span occurs exactly once in its document and in each mirror;
- the planted span occurs exactly once after planting;
- line counts are unchanged;
- at most one plant per normalised sentence;
- every proving source is inside the corpus;
- the builder re-derives the true value from the source and asserts that the original agrees with it and the planted text contradicts it. Qualitative plants instead assert that the contradicting text exists in the named file;
- mirroring: a plant in a verbatim duplicate passage (the form abstract, repeated in `SUBMISSION_KIT.md`) is applied to every duplicate, so a form/kit diff does not reveal it. S10 is the exception, because the disagreement is the defect.

**The arm-B finding that shaped the strata, from static reading of `check_claims.py`.**

- It reads the application text in exactly two places:
  - `"co-authored by BlueQubit" in _rep and ... in _frm`;
  - the form-abstract word count (330–360).
- Every other check compares the JSON results with constants hard-coded in the checker. It never reads a number from the report or form.
- So an S02 plant, a number "it recomputes", is predicted to be MISSED by arm B, like every other plant.
- The only plant arm B can catch is S01.

**Selection.**

- Planted copy k (k = 1, 2, 3) uses `random.Random(20260927 + k)`. Strata are processed in table order. The candidates are sorted by id and shuffled, and the first ones that do not share a sentence with an already chosen plant are taken.
- 22 distinct candidates are used across the 36 plant slots. S01 and S11 have a single candidate, and S05's quota equals its 2 candidates, so those 4 plants appear in all 3 copies.
- The quotas (S03 = 1, S05 = 2) were set to move the class mix toward the empirical distribution (section 8). A first draft had S03 = 2 and S05 = 1; that draft was replaced before this freeze.
- A pre-freeze `build.py --validate` run did this selection in memory and printed the plant ids per planted copy. It wrote nothing.

**Placebo assignment.**

- The labels A–D are shuffled with `random.Random(secret)`, where `secret = os.urandom(16)` is drawn at build time.
- Planted copies 1–3 take the first three labels; the placebo takes the last.
- The secret and the mapping are stored only in `SEALED/assignment.json`, whose sha256 is committed in the addendum.
- **Blindness is procedural, not cryptographic.** The placebo cannot be computed from the seeds, but anyone who opens the copies can find it: S01 and S11 are in every planted copy, so a grep for the co-authorship string finds it at once. The commitment is therefore that the orchestrator:
  - stages copies with `cp -a` only;
  - does not open, grep or diff corpus contents or `SEALED/` before all runs are complete;
  - gives every copy identical treatment.
- Each verifier sees one copy and cannot compare.

## 3. Corpus

Each `corpus/copy_<L>/` holds:

- the three application documents;
- `results/`, `figures/`, `pilot/`, `pilot2/` and `tracker/`, excluding `__pycache__`;
- `teams/rcs/wave2/results/` and `teams/rcs/wave3/results/`;
- five `refs/` files: `arXiv2607.24937_excerpts.txt`, `arXiv2608.13110_abstract.txt`, `tracker_issue151_excerpt.txt`, `tracker_issues_20260924.txt` and `arxiv2607.24937/p.txt`;
- `PATCH_PREREG.md`, `PATCH_PREREG_27CYC.md`, `RESULT_27CYC.md`, `RESULT_BIG_INTERIM.md`, `RESULT_CHI1024.md`, `DRAFT_PREREG_RCS.md` and `research/20260925-floquet-decision-path.md`.

Every non-plant byte is identical to the project originals, and the placebo is byte-identical throughout. There are
no comments and no diff artefacts. Every file and directory mtime is set to the epoch 1790000000.

Deliberately excluded, because they are prior defect lists or the author's checker (real verifiers were barred
from the checker):

- `check_claims.py` and `overclaim_scan.py`;
- `graph/`, `reviews/` and `teams/verification/`;
- `pilot_nli/`, `teams/ai_contribution/` and `drafts/`.

## 4. Arms

**Arm A: blind fresh-context verifier.**

- The brief is `VERIFIER_BRIEF.md`, sha256 `3608302a02c936efedbae79eca4b67aa38c65f699203b31db948193448b1acf6`, with `{PKG}` and `{OUT}` substituted and nothing else changed.
- Agent: a fresh-context Claude subagent of the same kind as the project's real verifiers, with read, shell and Python tools, no network, and told nothing else. Record the model id per run.
- Runs: exactly **2 independent runs per copy × 4 copies = 8 runs**. Every copy is treated identically, so the orchestrator stays blind to the placebo.
- Staging: each run gets its own fresh copy of `corpus/copy_<L>`, made with `cp -a` to a neutral directory OUTSIDE the project tree, e.g. `~/cohezion-labs/review_pkg_<random>/`. The directory name must not contain the label.
- Contamination audit: the orchestrator checks each transcript. The run is VOID, and is re-run once with a fresh agent, if it:
  - reads, lists or searches any path outside the staged package (above all the project originals and `SEALED/`);
  - makes any web or network tool call.
- Missing-run rule (A4): a run that crashes, times out or ends without a parseable table and `FINDINGS=` line is re-run once. If the re-run also fails, the run is recorded as MISSING and reported with n. It is not imputed and never counted as zero findings.
- A `FINDINGS=` count that disagrees with the parsed rows is flagged. The parsed rows are still scored.
- No run is repeated after its score has been seen.

**Arm B: `check_claims.py` against the planted text.**

- `run_armB.py` reads the checker source and replaces exactly the two text-read expressions, `(_HERE / "report" / "report.html")` and `(_HERE / "FORM_ANSWERS.md")`, with the copy's paths. It asserts one occurrence of each.
- It then `exec`s the source with `__file__` set to the original checker. All other inputs are the project's own, and the checker file on disk is never modified. The runner sha256 is `3f74a79d21c3471ae9d40834fb5bf08d6811183763fb682225b042cc4100ba18`.
- Baseline: the same runner on the originals (`--original`).
- A check that FAILs on a copy and PASSes on the baseline is a flip.
- Validity (A6): at least 100 PASS/FAIL lines and the checker's final summary line in both outputs. Otherwise arm B is recorded as an instrument failure for that copy.

**Arm C: placebo.** This is arm A on the placebo copy, which has zero plants. Arm B on the placebo must give zero flips; any flip is an instrument failure.

## 5. Scoring rule (implemented in `score.py`, sha256 `b52d9ce5dabb27439fe260d7a767f4a16f9fc3cf0d1fd95746ac9da8a63414a5`)

**Normalisation.** Text is normalised by stripping HTML tags (block tags become breaks), unescaping, applying
NFKC, mapping minus, dash and times signs to ASCII, removing markdown emphasis, and collapsing whitespace. It is
then split into sentences.

**Location.** A finding LOCATES plant p only if all three hold:

1. The finding's file (report, form or kit) names a document where p is planted or mirrored. A finding with an unrecognised file is searched against all three documents.
2. The sentence containing p's planted text (for a deletion, the post-deletion sentence) is a maximal longest-common-substring match for the finding's quoted text among all sentences of that document.
3. That overlap is at least min(20, 0.8 × quote length) characters.

A quote of fewer than 8 characters locates nothing. A quote from a different sentence cannot hit p, even if the
finding describes p's problem correctly. This is the mutation test.

**Problem.**

- AUTO_HIT: the finding locates p, its location is unambiguous (a unique best sentence), and its type, what-is-wrong, source or correct-value text matches one of p's pre-written auto patterns. The patterns are the true value, or the deleted or flipped words.
- NEEDS_ADJ: the finding locates p but no pattern matches, or the location is ambiguous.
- Auto hits are provisional until the independent adjudicator has reviewed them (below).

**Who adjudicates.** Not the application's author and not this team (A1).

- The adjudicator is a separate fresh-context agent. It gets:
  - the rules in this section and in section 6;
  - read access to the project sources;
  - finding rows stripped of run id and copy kind, in shuffled order;
  - for a located plant, the plant's `adj_right_problem`.
- It judges every NEEDS_ADJ item, EVERY AUTO_HIT, and every non-plant finding.
- An AUTO_HIT it marks MISS is overruled. The headline uses the adjudicator's verdicts. The auto-only count and the number overruled are reported beside it.

**Adjudication rule, fixed now.**

- The adjudicator sees the finding row and p's `adj_right_problem` statement. The verdict is HIT only if the finding, read alone, identifies the error the plant introduced: a reader could restore or correct the planted change from it.
- Numeric plants: saying that this specific number is wrong or inconsistent with a named source counts, even without the correct value.
- Qualifier deletions and overgeneralisations: the finding must say the claim lacks the specific restriction the deleted text supplied, or overstates scope in that direction.
- Direction flips: the finding must say the direction is wrong.
- Reference swaps: the finding must say the reference points to the wrong section.
- Anything else is a MISS: generic "unclear" or "unverifiable" complaints, a different problem in the same sentence, or a correct problem at a different location.
- An adjudicated HIT can only credit a plant the finding LOCATES.

**Credit.**

- One finding credits at most one plant: the lowest id among eligible plants not yet hit.
- A plant is hit once per run. Further findings on an already-hit plant are DUPLICATES. They are neither hits nor false positives.
- No final recall is reported while NEEDS_ADJ items are pending. If any remain, recall is reported as a bound: pending as miss (the headline) and pending as hit.

**Arm B credit.** Arm B is scored by the same "right problem" rule (A3).

- A plant is a hit if a flipped check is one of the plant's credited checks, and a check is credited only when its own name states that problem. The only such check is `report + form disclose BlueQubit co-authorship of the Floquet candidate`, credited to S01.
- A flip of `abstract ~350 words` is INCIDENTAL and not a hit.
- Any other flip is UNEXPECTED and reported.

## 6. False positives and pre-existing defects

Every arm-A finding that credits no plant is classified by the adjudicator. Each class is checked against the cited
source, and verifier findings are treated as claims too (M2):

- **PREEXISTING**: the text as it stands in the ORIGINAL application is false, overstated or inconsistent, confirmed against a quoted source. The adjudicator gives it a `defect_id`. The same id is used for the same problem at the same original sentence across runs.
- **FP**: the source supports the text.
- **UNRESOLVED**: cannot be settled from the corpus.

PREEXISTING findings are reported separately. They are never false positives, and they are listed as new
candidate defects for the lessons graph after the M2 check.

The false-positive rate is reported:

- per placebo run: FP only (lower bound) and FP + UNRESOLVED (upper bound);
- per planted-copy run, as a secondary figure.

## 7. Metrics

1. **Arm A recall.** Hits / plant-runs, pooled over the 6 planted-copy runs (72 plant-runs). It is reported with two intervals: a Wilson 95% CI, and a cluster-bootstrap 95% CI that resamples the 22 unique plants (2,000 resamples, seed 20260927).
   - The plant-runs are not independent (section 8), so the cluster-bootstrap interval is the one used in the verdict. The Wilson interval is secondary.
   - Co-headline: the number of unique plants caught by at least one run.
   - Also reported: recall by stratum, by class, by `checker_constant`, by `cross_doc_tell` and by `support_file_tell`.
2. **Post-stratified arm A recall (mitigation for class mix).** Per-class recall weighted by the section 2 empirical counts of the planted classes: wrong_number 7, scope 6, dropped_qualifier 6, overgeneralization 6, favorable 5, citation 4, cross-document 4, stale_count 3, hidden_denominator 2.
3. **Arm B recall.** Hits over the 36 plant slots, with a Wilson CI. Also reported: arm B incidental and unexpected flips, and baseline FAILs.
4. **Capture–recapture.**
   - **(a) Real application (placebo).** Take n1 and n2, the distinct PREEXISTING `defect_id`s found by placebo runs 1 and 2, and m, the number found by both. Report the Chapman N̂ = (n1+1)(n2+1)/(m+1) − 1, the Seber variance, a normal 95% CI floored at the observed distinct count, and N̂ − (n1+n2−m), the estimated unfound defects. If m = 0 the estimate is flagged unstable.
   - **(b) Calibration on planted copies (true N = 12).** Apply the same estimator to the two runs' plant hits on each planted copy. If N̂ misses 12 by more than 50% on any planted copy, or m = 0, the estimator FAILED calibration. The real-defect estimate is then reported with that label, and it leads (WAVE-6 note).
5. **Placebo.** Findings per run by class (PREEXISTING, FP, UNRESOLVED), plus the arm-B zero-flip sanity check.

**Frozen predictions for arm B** (from the static reading in section 2):

- exactly the S01 plant is hit in each planted copy, so 3/36 = 8.3%;
- no `checker_constant` plant is hit;
- no incidental word-count flip (each planted form abstract has 353 words by the checker's formula);
- zero flips on the placebo.

Any deviation is reported as a refuted prediction.

## 8. Validity threats (stated in advance)

- **Seeded defects may be easier or harder than natural ones.**
  - Every plant was chosen to be provable from a file in the corpus. Natural defects often are not.
  - Every plant is a single-span edit.
  - So recall here is best read as recall on source-checkable, single-sentence defects. It is not recall on all defects.
- **The class mix does not match the empirical distribution.** Planted class counts over the 36 slots (from the pre-freeze `--validate` run) against the empirical share among the same 9 classes:

  | class | planted slots | planted share | empirical share |
  |---|---|---|---|
  | wrong_number | 8 | 22% | 7/43 = 16% |
  | dropped_qualifier | 6 | 17% | 14% |
  | stale_count | 1 | 3% | 7% |
  | overgeneralization | 6 | 17% | 14% |
  | scope_overreach | 3 | 8% | 14% |
  | favorable_reading | 3 | 8% | 12% |
  | citation_overreach | 3 | 8% | 9% |
  | cross_document_inconsistency | 3 | 8% | 9% |
  | hidden_denominator | 3 | 8% | 5% |

  - The orchestrator asked for the mix to MATCH the empirical distribution. That was done only partly: the quotas were rebalanced (S03 2 to 1, S05 1 to 2), which cut wrong_number from 31% to 22%.
  - Numbers are still over-represented, because the brief required both a checker-constant and a non-constant number plant, plus a direction flip. stale_count and hidden_denominator are off by a single plant each way.
  - Mitigation for the remaining gap: per-class recall plus the post-stratified recall in 7.2. Classes absent from the benchmark (unsourced_number, unstated_definition, single_source_truth, unmeasured_mechanism, unit_conflation, and all process classes) are not measured.
- **Author–key correlation.** The same team wrote the plants, the key and the auto patterns. Auto patterns can only credit findings that locate the planted sentence, and ambiguous cases go to an adjudicator working from the written rule above.
- **Tells.**
  - S10 plants and plants with `cross_doc_tell = true` can be found by diffing documents. Recall is reported stratified by that flag.
  - The same S01, S11 and some S03 plants recur across copies. They are counted per copy-run, and unique-plant recall is reported too.
- **Capture–recapture assumptions.** Equal catchability and independent runs. Two runs of the same model family are positively correlated and defects differ in difficulty, which biases N̂ LOW. That is why the estimator is calibrated in 7.4(b).
- **Dependence.** The 72 plant-runs come from 22 unique plants. 4 of them recur in every copy, and the two runs on a copy use the same model family. So a Wilson interval on 72 is too narrow. The verdict uses the cluster-bootstrap interval over unique plants.
- **Small n.** 72 plant-runs and 2 placebo runs. No claim is generalised beyond this corpus, these 3 copies, this verifier configuration and 2 runs per copy.

## 9. Verdict wording (fixed; filled with the computed numbers, whatever they are)

Let R_A be the pooled arm-A recall, after independent adjudication and taking pending as miss if any remain, with cluster-bootstrap 95% CI [lo, hi]. Let R_B be the
arm-B recall.

- **Headline sentence (mandatory, verbatim template):** "On a planted-defect benchmark with a sealed answer key (3 copies of our application × 12 planted defects, 2 blind runs each), fresh-context AI verifiers caught H of 72 (R_A, 95% CI [lo, hi]; U of 22 distinct defects caught at least once); our arithmetic checker caught K of 36; on an unmodified placebo copy the verifiers reported F false findings per run (F_up counting unresolved)."
- **Recall band:**
  - R_A ≥ 0.80 "high";
  - 0.50 ≤ R_A < 0.80 "moderate";
  - 0.25 ≤ R_A < 0.50 "low";
  - R_A < 0.25 "very low".
  - The band word is used as-is. For "low" or "very low", this sentence is mandatory: "This does not support describing AI verification as a strong defect detector for our claims."
- **Comparison with the old figure:** if hi < 0.911 (= 41/45), then: "The earlier 41-of-45 figure, whose denominator was defects we found ourselves, is not reproduced against an external key; the planted-defect recall is the figure to cite." If hi ≥ 0.911: "Consistent with the earlier 41-of-45 figure."
- **Verifier against checker:** if R_A − R_B ≥ 0.25 and R_A's cluster-bootstrap lower bound exceeds R_B's Wilson upper bound: "Verifiers outperformed the checker." Otherwise: "No demonstrated advantage of verifiers over the checker on this benchmark."
  - Either way, state the frozen structural reason: the checker reads the application text only for the co-authorship string and the abstract word count.
- **False alarms:** if F_up > 5 per placebo run: "The verifiers produce substantial false alarms on unmodified text."
- **Remaining real defects:**
  - If calibration passed: "Capture–recapture on two blind runs of the unmodified application estimates N̂ real defects (95% CI [a, b]), of which about U remain unfound."
  - If calibration failed: "The capture–recapture estimator failed calibration on planted defects (N̂ = x against a true 12), so its estimate of remaining real defects (N̂ = y) is not reliable."
- **Weak recall must not be dropped from the application.** If recall is weak, the application's AI-contribution sentence must be replaced by the headline sentence above.

## 10. Instrument-failure conditions (the benchmark itself fails)

The benchmark itself fails if any of the following holds:

- `score.py --self-test` fails;
- `run_armB.py --dry` fails;
- arm B on the placebo shows any flip;
- the arm-B baseline output is invalid;
- more than 2 of the 8 arm-A runs end VOID or MISSING.

Each such outcome is reported as a benchmark failure, not as a verifier result.

## 11. Freeze record and deviations

`prereg_frozen_at.txt` records the freeze time. It is written together with `PREREG.sha16` and before
`build.py --build`. `SEALED/keys.json`, containing `{}`, existed in `SEALED/` before this work began. It is not part
of this benchmark and was left untouched.

### Deviations

No change to the key, the pool, the brief, the scorer or the rules after this freeze. Any deviation is written to
`DEVIATIONS.md` with a timestamp and whether it was made before or after any score was seen.

## Addendum (written after freeze; excluded from PREREG.sha16)

Written 2026-09-27, after the freeze and after `build.py --build`. No verifier or arm-B run had happened at this point.

- `PREREG.sha16` = `04570ab6a4efeb79`. Freeze time is in `prereg_frozen_at.txt` (2026-09-27T13:14:24-04:00).
- Sealed file hashes (sha256):
  - `SEALED/key.json`: `58be79440168ad1d5db54a8f6bbe2760b22980694d67076c020c18f387e184e7`
  - `SEALED/assignment.json`: `d4183be89fb7ec571907cd51d81c6144d8d02844c87efc1faa92e3fb2609d2bb`
  - `SEALED/pool.json`: `b708e458e367b69d1030bc2ea5f261707f3a1f2b2217b2c0b10ea8bd3983c820`, the same as in section 2.
- Build output: 4 copies (`corpus/copy_A`…`copy_D`), 167 files each. There are 3 planted copies with 12 plants each, 36 plant slots over 22 distinct plants, and 1 placebo. All mtimes are 1790000000.
  - Apparent sizes differ by a few bytes between copies, because the edits change string lengths. A verifier sees only one copy, so it cannot compare.
- Checks run before the freeze, with no corpus written:
  - `build.py --validate`: all 25 pool entries passed their source checks, and the 3 planted copies were built in memory;
  - `score.py --self-test`: 22 of 22 checks passed;
  - a mutation of the scorer (dropping the maximal-match location requirement) turned 7 of those checks red, including the wrong-sentence mutation check and the adjudication-cannot-rescue check, so the self-test discriminates;
  - `run_armB.py --dry`: OK;
  - neither the arm-B baseline nor any arm-B copy run was executed.
- `SEALED/keys.json` (`{}`, dated 2026-09-26) existed before this work and is not part of the benchmark.
- **Post-build checks, run before any verifier.** Synthetic reports were written to the scratchpad, never to `runs/`.
  - **Located:** every one of the 36 real plants is located by a quote of its own sentence, so no plant is unfindable.
  - **Positive control** (right sentence plus the `adj_right_problem` text): 35 of 36 AUTO_HIT. The remaining one was NEEDS_ADJ, a conservative pattern miss that goes to the adjudicator.
  - **Negative control** (right sentence, "wording unclear"): 0 of 36 AUTO_HIT.
  - **Placebo:** 0 hits.
  - **Arm-B baseline probe:** `python3 run_armB.py --original` ran `check_claims.py` on the unmodified documents, with 135 PASS/FAIL lines, ALL CLAIMS VERIFIED and exit 0. The interpreter is the system `python3`, with qiskit 2.5.2. No arm-B copy run was executed.
- Deviations: see `DEVIATIONS.md` (one entry, before any verifier run).
