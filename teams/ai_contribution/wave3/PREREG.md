# PREREG: does a qualifier-focused procedure close the verifiers' dropped-qualifier blind spot? (team ai_contribution, wave 3)

Frozen before any wave-3 corpus copy exists. `PREREG.sha16` = the first 16 hex characters of the sha256 of this
file's bytes up to and including the line `## Addendum (written after freeze; excluded from PREREG.sha16)`.
Anything below that line was written after the freeze and is not covered by the hash.

## 0. Question, and why

In wave 2 (PREREG sha16 `04570ab6a4efeb79`), blind fresh-context verifiers caught 51 of 72 plant-runs overall but
**0 of 12 deleted qualifiers** (class `dropped_qualifier`). In `graph/lessons.json`, `dropped_qualifier` is among
the most frequent real defect classes (8 of 89 defects at the time of writing), including in fix rounds. So the
verifiers' largest measured blind spot sits where our real errors are.

**Question (pre-registered).** Does a verifier given a qualifier-focused procedure catch deleted qualifiers that
the generic wave-2 brief misses, without a large rise in false findings?

The procedure, for each claim sentence:
1. find the source result behind it;
2. list the restrictions the source imposes (scope, parameter regime, denominator, depth, conditions, status such as post hoc or extrapolated, tolerance);
3. check that each restriction appears in or next to the sentence.

**Scope, stated plainly.** This tests ONE procedure, on ONE document set (our application as of 2026-09-27),
with 9 distinct deleted-qualifier plants and 2 runs per copy per arm. It is not a general claim about AI
verification, about qualifier detection in other documents, or about other prompts.

## 1. Design summary

- Fresh held-out plants in the CURRENT live application (`report/report.html`, `FORM_ANSWERS.md`,
  `SUBMISSION_KIT.md`), with a new seed family (`SEED_BASE = 30260927`; wave 2 used 20260927 + k).
- No wave-2 plant sentence is reused. `build.py` holds the 25 wave-2 plant spans as a constant, asserts once that
  it equals wave 2's `POOL`, and rejects any candidate whose sentence shares at least min(20, span length)
  characters with any wave-2 span. A check against the live report showed this filter excludes 18 report
  sentences, so it is not vacuous.
- 15 plants: **9 qualifier deletions** (primary) and **6 other-class plants** (3 `wrong_number`, 3 reference
  swaps, class `citation_overreach`) as a sanity control, so the new brief is not tuned only to qualifiers.
- 3 copies with neutral labels A–C: 2 planted copies (disjoint plant sets) and 1 byte-identical placebo.
- 2 arms (G, Q) × 3 copies × 2 runs = **12 verifier runs**. Both arms see the same copies.
- A sealed key, and independent adjudication by two adjudicators, with κ.
- No arm B (checker), no network, no BlueQubit, no spend.

## 2. Plant pool (`SEALED/pool.json`, sha256 `daabff58df2ee94ebd2c8ab1d288a6ba2ba6c070052964191ed6ec44c666f795`)

`build.py` (sha256 `e0701a2ee0db5bb460312c0e47bbc6dc09d5b8e9164f87f352ed08955a960ec7`) holds the same pool in code, and `--build` refuses to run unless the two are
identical and every hash listed in this section appears in this file. `score.py` imports its text normalisation
from `build.py`, so the build hash also freezes the scorer's segmentation (unchanged from wave 2).

**Qualifier plants.** Each deletes a restriction that a named source in the corpus imposes, and each deletion was
chosen so that the planted sentence is **false or overstated**, not merely less informative (a validator in
`build.py` recomputes or quotes the source for each). Candidates whose deletion left a true sentence were
rejected before freezing. The rejected candidates were: the δ/χ setting of the 19-qubit 27/27 bracket (it holds at
every recorded setting); "in Qiskit's index order" (RCM at χ = 32 is also poor at 3π/8); "at three angles"; "on
one lattice and parameter set" (the sentence stays hedged); "under a two-budget agreement rule"; and the δ of the
4-of-12 zero-collapse (underspecified rather than false).

| id | restriction kind | document | mirrored in | restriction also stated elsewhere (`cross_doc_tell`) |
|---|---|---|---|---|
| Q02 | parameter regime | report | – | no |
| Q05 | depth | report | – | no |
| Q07 | post-hoc status | report | – | no |
| Q08 | conditions | report | – | yes |
| Q09 | conditions (error model) | form | kit (verbatim abstract duplicate) | yes |
| Q10 | scope | form | – | yes |
| Q11 | conditions (exception) | form | – | yes |
| Q15 | scope | report | – | yes |
| Q16 | scope | report | – | yes |

Denominator and tolerance restrictions are not represented: no deletion of that kind made its sentence false under
the rule above. Recall on those kinds is therefore not measured.

**Other plants (sanity control):** N01, N02, N03 (`wrong_number`; report, form, report) and C01, C02, C03
(`citation_overreach`: a wrong file, a wrong arXiv id, a wrong arXiv id; form, report, report).

**Builder rules** (asserted in `build.py`):
- The original span occurs exactly once in its document and in each mirror. A verbatim duplicate in another document must be listed as a mirror; otherwise the build fails.
- The planted span occurs exactly once after planting, and every plant has a non-empty planted span. A deletion is written as a replacement that keeps the surrounding words, with capitalisation repaired where a sentence-initial qualifier is removed.
- Line counts are unchanged, and only plant lines change.
- Every plant is in a distinct normalised sentence, across all 15 plants.
- Every proving source is inside the corpus.
- Supporting-file tells are recorded per plant, as in wave 2: any non-document corpus file containing the normalised original span.

**Selection** (`random.Random(SEED_BASE)`). Within each class (qualifier, wrong_number, citation), the ids are
sorted, shuffled and dealt round-robin to the 2 planted copies from a random start. The pre-freeze
`build.py --validate` run gave:
- planted copy 1: Q05, Q09, Q15, Q16, N03, C01, C02 (4 qualifier, 3 other);
- planted copy 2: Q02, Q07, Q08, Q10, Q11, N01, N02, C03 (5 qualifier, 3 other).

**Placebo assignment.** Labels A–C are shuffled with `random.Random(secret)`, where `secret = os.urandom(16)` is
drawn at build time. Planted copies 1–2 take the first two labels and the placebo takes the last. The mapping is
stored only in `SEALED/assignment.json`. Blindness is procedural, as in wave 2: the orchestrator stages copies
with `cp -a` only, does not open, grep or diff `corpus/` or `SEALED/` before all 12 runs are complete, and treats
every copy identically. There is no arm B this time, so no instrument output can unblind the orchestrator before
adjudication.

## 3. Corpus

Each `corpus/copy_<L>/` holds exactly the wave-2 package layout (`INCLUDE` in `build.py`, identical to wave 2):
- the three documents;
- `results/`, `figures/`, `pilot/`, `pilot2/`, `tracker/`, `teams/rcs/wave2/results/`, `teams/rcs/wave3/results/`;
- five `refs/` files;
- the pre-registration and result files, and `research/20260925-floquet-decision-path.md`.

`__pycache__` is excluded. Every non-plant byte is identical to the project originals, and all mtimes are set to
1790000000. `--build` also writes `SEALED/originals/`, a byte-identical snapshot of the unmodified package, so the
adjudicators judge PREEXISTING against the application as it was at build time, even if the live files are later
edited (the wave-2 D5 lesson).

## 4. Arms, runs and isolation

**Arm G (generic).** `VERIFIER_BRIEF.md`, byte-identical to wave 2's (sha256 `3608302a02c936efedbae79eca4b67aa38c65f699203b31db948193448b1acf6`,
asserted in `build.py`).

**Arm Q (qualifier procedure).** `QUALIFIER_BRIEF.md` (sha256 `4cc089e89b3bcd00f016c2879c4fc46ec7d54d84cf0b981442791ae3f8d240a5`) is G plus exactly one
inserted section, `## Required procedure: check each claim's restrictions`, placed before
`## What counts as a finding`. `build.py` asserts that removing that section gives G byte for byte.
- The section names restriction KINDS only (scope, parameter regime, denominator, depth, conditions, status, tolerance). It gives no example drawn from the plants.
- Neither brief says that defects were planted, and neither gives a count.

**Harness note (identical for both arms).** Each prompt is the arm's brief with `{PKG}` and `{OUT}` substituted,
followed by `HARNESS_NOTE.md` (sha256 `fcc6a6b8855e8d9e26091e7fca1e98eaa1ff1984d61d0900d356c12e69288e72`) with `{SCRATCH}` = `{PKG}/_scratch`. It tells the
verifier to write helper files only there, never under `/tmp`. This fixes the wave-2 D3 shared-`/tmp`
contamination. As a consequence, G's transmitted prompt is not byte-identical to wave 2's, so any comparison of
G here with wave 2's 0/12 is descriptive only.

**Runs.** 2 runs per copy per arm, 12 in all. `stage_runs.py` (sha256 `df7a145b1cbf71dade50eab423de814ae2d70cfce50514c281775a4e14abc134`):
- stages each run into its own `~/cohezion-labs/review_pkg_<random hex>/`, whose name carries no label or arm, with a private `_scratch/`;
- writes the exact prompt to `briefs_sent/<L>_<ARM>_run<r>.md`;
- writes a random, interleaved launch order.

Each run is a NEW fresh-context agent of the same kind as the project's verifiers (read, shell, Python tools; no
network), with the SAME model for both arms. The model id is recorded per run. The orchestrator tells the agent
nothing beyond the prompt file.

**Contamination audit.** A run is VOID, and is re-run once with a fresh agent and a freshly staged directory, if
its transcript shows:
- a read, listing or search of any path outside its own staged directory;
- a write outside its `_scratch/` and `{OUT}`;
- any web or network call.

**Missing-run rule (A4).** A run that crashes, times out, is VOID, or ends without a `FINDINGS=` line is re-run
once. If the re-run also fails, the orchestrator writes `runs/<L>_<ARM>_run<r>.MISSING`. A MISSING run is never
imputed and never counted as zero findings. MISSING counts are reported per arm. The verdict needs, **per arm**,
at least 3 of the 4 planted-copy runs and at least 1 of the 2 placebo runs; otherwise the benchmark is an
instrument failure (sec. 9). No run is repeated after its score has been seen.

## 5. Scoring (`score.py`, sha256 `7ee06583016dd87eadbd69121fa8ffede495f4553f17f3e1aae974da174266d2`)

**Location and credit are the wave-2 rules, unchanged.**
- A finding LOCATES plant p only if all three hold:
  1. its file names a document where p is planted or mirrored;
  2. p's planted sentence is a maximal longest-common-substring match for its quote among that document's sentences;
  3. the overlap is at least min(20, 0.8 × quote length) characters, and the quote has at least 8 characters.
- AUTO_HIT: the finding locates p unambiguously and its type, what-is-wrong, source or correct-value text matches one of p's auto patterns.
- NEEDS_ADJ otherwise.
- One finding credits at most one plant, and a plant is hit at most once per run. Duplicates are neither hits nor false positives.
- An adjudicated HIT can only credit a plant the finding locates. An AUTO_HIT that the adjudication marks MISS is overruled.

**Auto patterns** match only the deleted words or the true value (for qualifier plants: the deleted restriction's
content). Because a Q-arm finding on a plant sentence will often name SOME restriction, the patterns do not match
restriction vocabulary in general. A self-test case checks that a finding naming a different restriction on the
right sentence is NEEDS_ADJ, not an AUTO_HIT. A post-build control does the same on the real key.

### 5.1 Changes from wave-2 `score.py` (complete list)

1. It imports normalisation from wave-3 `build.py` (the code is identical to wave 2's).
2. Runs are named `<L>_<ARM>_run<r>.md`. The arm is parsed from the name, and every statistic is computed per arm.
3. `.MISSING` markers, and reports without a `FINDINGS=` line, are recorded as MISSING (sec. 4 rule).
4. Plants carry `group` (qualifier/other). Recall is computed per arm and per group.
5. A **paired** cluster bootstrap (2,000 resamples, seed 30260927) resamples DISTINCT qualifier plants with replacement and computes both arms' recall on the same resample. It gives percentile 95% CIs for G, for Q, and for the difference Q − G.
6. Per-arm placebo statistics: FP, UNRESOLVED, PREEXISTING, MISLOCATED and PENDING counts; mean (FP + UNRESOLVED) per placebo run (the frozen FP statistic); FP-only per run; FP per planted-copy run; finding rows per run.
7. Recall is stratified by `cross_doc_tell`, restriction kind, class and plant id, per arm.
8. The frozen verdict rule (sec. 7) is implemented in `verdict()`, with the wording in `VERDICT_TEXT`.
9. Removed: arm B, Chapman capture–recapture and post-stratification (not part of this question).
10. The self-test is extended (30 checks). It adds `--mutation-test`, which neutralises five mechanisms in turn: the location rule, arm separation, the FP condition, the bootstrap lower bound and the MISSING rule. It requires the self-test to fail for every mutant. Pre-freeze result: 30/30 PASS, and 5/5 mutants killed.

## 6. Adjudication

- The packet is built mechanically by `adjudication/make_packet.py` (sha256 `f9a25b4b5d14cfb0d5c5a548632b410bea94f0a1e992fa1efb95208a9433da87`). It has one row per finding from every valid run of both arms.
- Run id, **arm** and copy kind are stripped, ids are opaque, the order is shuffled, and the seed is sealed in `adjudication/SEALED/map.json`.
- `located_options` and `nearby_options` are as in wave 2.
- Two independent fresh-context adjudicators judge the full packet. Each gets `adjudication/ADJUDICATOR_BRIEF.md` (sha256 `676f4b60ac0d290e2e6f0fcd6b7af1968042f831f7ec32b20d1c1fddfaa9eabe`) and a private staged copy of `SEALED/originals/` with `_adjudication/` and `_scratch/` directories. They are not the orchestrator, not this team, and not any verifier.
- `adjudication/merge.py` (sha256 `582742cfa720820bc73330e2a2becb3d9eb77f8855fe844c6e7f13c4edf2c172`; wave-2 merge plus a located-only κ) reports Cohen's κ over all items and over located items only.
  - Disagreements go to a third adjudicator. Its verdict is final when it matches one of the first two; otherwise the item is UNRESOLVED, which is never a hit.
  - PREEXISTING needs a `source_quote`.
- The adjudication rule is frozen in the adjudicator brief:
  - the wave-2 rule;
  - the wave-2 D1 MISLOCATED verdict;
  - two additions made explicit: a finding that names a DIFFERENT missing restriction is not a HIT; and "missing restriction" findings on the original text are PREEXISTING only if the adjudicator can quote the source imposing the restriction and its omission makes the original overstate.
- Reference swaps may point to the wrong section, file or paper.

## 7. Metrics and the frozen decision rule

Let qQ and qG be the qualifier-plant recall of each arm: hits over plant-runs on the planted copies, after
adjudication, with pending items counted as misses. The denominator per arm is 9 plants × 2 runs = 18 plant-runs,
fewer if runs are MISSING. Let d = qQ − qG, with paired cluster-bootstrap 95% CI [lo, hi] over the 9 distinct
qualifier plants. Let fpQ and fpG be the mean (FP + UNRESOLVED) per placebo run of each arm.

**Primary:** qualifier recall, Q vs G.

**Secondary:**
- other-class recall per arm;
- FP-only per placebo run;
- FP per planted-copy run;
- rows per run;
- recall by `cross_doc_tell`;
- unique qualifier plants caught by at least one run, per arm.

**Rule (frozen):** Q **closes the blind spot** only if all of these hold:
- qQ ≥ 0.5;
- d ≥ 0.3;
- lo > 0;
- fpQ ≤ fpG + 5.

Outcomes, evaluated in this order:

| code | condition | verdict wording (verbatim) |
|---|---|---|
| CLOSES | all four conditions | "The qualifier procedure closes the blind spot on this benchmark: it raised deleted-qualifier recall by at least 0.3 (bootstrap lower bound above 0) to at least 0.5, without more than 5 extra false findings per placebo run." |
| RECALL_GAIN_AT_FP_COST | recall conditions met, fpQ > fpG + 5 | "The qualifier procedure raised deleted-qualifier recall enough to meet the recall criteria, but at a cost of more than 5 extra false findings per placebo run, so it does not close the blind spot as pre-registered." |
| PARTIAL_GAIN | d ≥ 0.3 and lo > 0, but qQ < 0.5 | "The qualifier procedure raised deleted-qualifier recall by at least 0.3 (bootstrap lower bound above 0), but its recall stayed below 0.5, so it narrows the blind spot without closing it." |
| GAIN_NOT_DEMONSTRATED | d ≥ 0.3 but lo ≤ 0 | "The qualifier procedure's recall exceeded the generic brief's by at least 0.3, but the bootstrap interval over distinct plants includes zero, so an improvement is not demonstrated." |
| NO_IMPROVEMENT | d < 0.3 (including d < 0) | "No improvement: the qualifier procedure did not raise deleted-qualifier recall by the pre-registered 0.3 over the generic brief. This does not support adding it to our verification protocol as a fix for dropped qualifiers." |
| UNDECIDED_PENDING_ADJUDICATION | the rule gives a different outcome with pending counted as hit, or any placebo finding is still pending | "Undecided: the verdict depends on items still pending adjudication (pending-as-miss and pending-as-hit give different outcomes)." |
| INSTRUMENT_FAILURE | sec. 9 | "The benchmark failed as an instrument (<reasons>), so no verifier result is reported." |

**Mandatory added sentences** (verbatim templates; the numbers are filled in):
- If qG ≥ 0.5: "The wave-2 blind spot did not reproduce on fresh plants: the generic brief caught <hG/nG> deleted qualifiers here (recall <qG>), so the wave-2 0-of-12 may not generalise beyond that corpus."
- If Q's other-class recall < G's − 0.25: "The qualifier procedure lost recall on the other defect classes (<oQ> vs <oG>)."
- Always: "On the unmodified placebo copy, verifiers reported <fpQ> (Q) vs <fpG> (G) false findings per run counting unresolved (FP only: <…> vs <…>)."
- Always: "This tests one procedure on one document set, with 9 distinct deleted-qualifier plants and 2 runs per copy per arm; it is not a general claim about AI verification."
- Always: the headline numbers stated exactly: hQ/nQ, hG/nG, d with [lo, hi], each arm's own bootstrap CI, other-class recall per arm, κ overall and located-only, MISSING counts per arm, and qualifier recall split by `cross_doc_tell` in both arms. If the effect comes mostly from `cross_doc_tell` plants, say so.

**No application text is changed by this team.** A proposed sentence for the application may be written to
`proposed_application_text.md` only after the verdict, and it must use the verdict wording above.

## 8. Validity threats (stated in advance)

- **Priming in the corpus itself.** The live report and form describe the wave-2 planted-defect benchmark, and the report states "every deleted qualifier was missed (0 of 12)". Both arms read this. It may raise G's attention to qualifiers and so bias the comparison toward "no improvement". It is not removed, because removing it would be a non-plant edit.
- **Author–key correlation.** The same team wrote the plants, the key, the auto patterns and the Q procedure. The procedure names restriction kinds only. The auto patterns are narrow. Adjudicators judge every hit from the written rule.
- **Adjudicator arm leakage.** Q-arm findings may be recognisable by wording ("missing restriction"), so adjudicators may partly infer the arm. The arm is stripped, but this cannot be fully hidden.
- **Cross-document tells.** 6 of 9 qualifier plants have their restriction stated elsewhere in the package, so G's cross-document check can catch them without any qualifier sensitivity. Recall is reported split by `cross_doc_tell`.
- **Small n.** 9 distinct qualifier plants, 18 plant-runs per arm, 2 placebo runs per arm. The runs on a copy share a model family and are correlated, so the verdict uses the bootstrap over distinct plants. A true effect of moderate size may be missed (low power), and a null here is weak evidence of no effect.
- **Restriction kinds.** Denominator and tolerance deletions are absent, and other kinds have 1–4 plants each. Nothing is concluded per kind.
- **Seeded-defect realism.** The plants are single-span, source-checkable edits. Recall here is recall on those, not on all dropped qualifiers.
- **Cost asymmetry.** The Q procedure is longer, so Q runs are more likely to time out. MISSING is reported per arm, and the verdict requires coverage per arm.
- **Same model for both arms.** The result is conditional on that model and this prompt wording.

## 9. Instrument-failure conditions

The benchmark itself fails if:
- `score.py --self-test` or `score.py --mutation-test` fails;
- `adjudication/merge.py --self-test` fails;
- either arm has fewer than 3 valid planted-copy runs or fewer than 1 valid placebo run (sec. 4);
- the post-build controls (Addendum) show a plant that cannot be located, or a wrong-restriction finding that AUTO_HITs.

Such an outcome is reported as a benchmark failure, not as a verifier result.

## 10. Freeze record and deviations

`prereg_frozen_at.txt` records the freeze time. It is written with `PREREG.sha16` and before `build.py --build`.
Any change after the freeze is written to `DEVIATIONS.md` with a timestamp and whether it was made before or after
any score was seen. No change to the key, the pool, the briefs, the scorer or the rules is made after the freeze
except through that log.

## Addendum (written after freeze; excluded from PREREG.sha16)

Written 2026-09-27, after the freeze and after `build.py --build`. No verifier has run.

- `PREREG.sha16` = `b20ba288605a1338`, frozen at 2026-09-27T23:47:01-04:00 (`prereg_frozen_at.txt`), before `--build`.
- Sealed file hashes (sha256):
  - `SEALED/key.json`: `c0ddb3a73124676cf0db80f28b891624f36225c1032344c64f6857a0dfabcf09`
  - `SEALED/assignment.json`: `60feb3370b9fc051a02579f7f5dcc83f5bedd248aa238cf11e9765b96e471043`
  - `SEALED/pool.json`: `daabff58df2ee94ebd2c8ab1d288a6ba2ba6c070052964191ed6ec44c666f795` (as in sec. 2)
- Build output: 3 copies (`corpus/copy_A`…`copy_C`), 169 files each; 2 planted copies (7 and 8 plants; 15 plant
  slots, 15 distinct plants, 9 of them qualifier deletions); 1 placebo; `SEALED/originals/` (169 files). All mtimes
  1790000000. The builder asserted the placebo documents are byte-identical to the originals and that only plant
  lines changed in the planted copies.
- Checks before the freeze: `build.py --validate` (all 15 sources, wave-2 exclusion, brief assertions);
  `score.py --self-test` 30/30; `score.py --mutation-test` 5/5 mutants killed; `merge.py --self-test` OK.
- **Post-build controls** on the real key (synthetic findings written to the scratchpad, never to `runs/`):
  - every one of the 15 plants is located by a quote of its own sentence;
  - positive control (right sentence + `adj_right_problem` text): 14 of 15 AUTO_HIT; N02 was NEEDS_ADJ (a conservative pattern miss: `\b76\b` does not match "76x"), which goes to the adjudicators;
  - negative control (right sentence, "wording unclear"): 0 of 15 AUTO_HIT;
  - wrong-restriction control (right sentence, a finding naming a missing DENOMINATOR, a restriction no plant deleted): 0 of 9 qualifier plants AUTO_HIT;
  - end-to-end dry run on 12 synthetic reports, one of them a `.MISSING` marker: `score.py` → `make_packet.py` (24 rows; no run id or arm in any row) → `merge.py` (κ overall and located-only computed) → `score.py --adjudication` produced a verdict and all mandatory sentences.
- Deviations: none (see `DEVIATIONS.md`).
