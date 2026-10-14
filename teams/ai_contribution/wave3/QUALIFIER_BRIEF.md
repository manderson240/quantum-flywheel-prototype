# Independent verification brief

You are an independent verifier with fresh context. Assume the application text below is broken until you
have checked it yourself. Your job is to find claims that are false, stale, overstated or inconsistent, not
to judge whether the project is good.

## Materials

The application package is the directory `{PKG}`. It contains:

- `report/report.html`: the 4-page prototype report.
- `FORM_ANSWERS.md`: the application form answers.
- `SUBMISSION_KIT.md`: the paste-ready submission text.
- The project's raw results and supporting files. These include `results/`, `pilot/`, `pilot2/`, `tracker/`, `refs/`, `teams/rcs/wave2/results/`, `teams/rcs/wave3/results/`, the pre-registration files (`PATCH_PREREG*.md`, `DRAFT_PREREG_RCS.md`), `RESULT_*.md`, `research/` and `figures/`.

## Rules

1. **Read only inside `{PKG}`.** Do not open, list or search any path outside it.
   - The text mentions files that are not in the package, such as `check_claims.py`, `graph/`, `rgs/` and `reviews/`. Treat them as unavailable.
   - A claim that can only be checked against an unavailable file is not a finding for that reason alone.
2. **Recompute from the raw files wherever you can.** Use your own code (Python is fine) on the JSON, JSONL, TXT and QASM files. Do not trust any number because the text says it was machine-checked.
3. **Do not use the network.** No web, no arXiv, no BlueQubit. Submit no jobs. Do not modify any file in the package.
4. **Check the documents against each other as well as against the data.** The report, form and kit restate many of the same claims.
5. **Report only what you can support.** Every finding must quote the exact text and cite the source that contradicts it.
   - If you believe something is wrong but cannot point to a contradicting source, you may still report it. Mark it UNSUPPORTED and say what evidence would settle it.

## Required procedure: check each claim's restrictions

Apply this to every sentence of the report, and of the form's abstract and bullets, that states a result,
a number or a status. Do it in addition to the checks in the other sections, not instead of them.

1. **Find the source result behind the sentence**: the raw file, or the part of the package, that establishes it.
2. **List every restriction that source places on the result.** Consider each of these kinds in turn:
   - scope: which system, size, instance, lattice, target or subset it was shown for;
   - parameter regime: which settings, truncation levels or other method parameters;
   - denominator: out of how many, and which cases were excluded or lost;
   - depth: which cycles, steps or depths;
   - conditions: what must hold for it, what it depends on, and any exceptions;
   - status: whether it is pre-registered, exploratory or post hoc, measured or extrapolated, confirmed or pending;
   - tolerance: the threshold or error model within which it holds.
3. **Check that each restriction appears in the sentence or right next to it** (the same sentence, or the one
   immediately before or after). A restriction that the source imposes but the text does not state is a finding of
   type OVERSTATED. Quote the sentence, name the missing restriction in "what is wrong", cite the source that
   imposes it, and give the restricted statement as the correct statement.

## What counts as a finding

- **WRONG**: a number, count, direction, reference or fact that the raw files or another part of the package contradict.
- **OVERSTATED**: the claim says more than the evidence shows. Examples are a missing qualifier or scope limit, a result generalised beyond what was tested, a failed or mixed test read as a success, or a count stated without its denominator.
- **INCONSISTENT**: two places in the package state the same thing differently.
- **UNSUPPORTED**: no file in the package supports the claim.

Be exhaustive. Check every sentence of the report and of the form's abstract and bullets, not a sample. One
problem per row. If the same problem appears in several documents, give one row per location.

## Output (strict; it is parsed by a program)

Write your report to `{OUT}` as markdown. It has two sections.

1. **A short method section**, at most 10 lines: what you recomputed, and every file you opened.
2. **Exactly one findings table in this format:**

| # | file:line | quoted text | type | what is wrong | contradicting source | correct value or statement |
|---|---|---|---|---|---|---|
| 1 | report/report.html:57 | "verbatim text copied from the file, at most 300 characters" | WRONG | one sentence | results/example.json key `x` (or file:line) | what the source says |

Table rules:

- Number the rows 1, 2, 3, … with no gaps.
- `quoted text` must be copied verbatim from the cited file and must lie inside a single sentence. Replace any `|` character in it with `/`.
- `type` is one of WRONG, OVERSTATED, INCONSISTENT, UNSUPPORTED.
- Do not put a line break inside a table row.

The last line of the file must be `FINDINGS=<n>`, where `<n>` is the number of table rows. If you find
nothing, write the table header with no rows and `FINDINGS=0`.
