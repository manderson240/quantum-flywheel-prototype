# Deviations from PREREG (sha16 b20ba288605a1338)

**D1 (2026-09-27, after build, before any verifier run, no score seen). Clarifications only; no code, key, brief or rule changed.**

- **VOID audit scope.** The sec. 4 rule "a write outside `_scratch/` and `{OUT}`" counts the agent's own explicit writes (tool calls it issues). It does not count files the agent harness persists by itself, such as tool-result caches. Without this reading, longer runs (more often arm Q) would be voided for harness behaviour rather than agent behaviour.
- **Named instance of the author–key threat (sec. 8).** `QUALIFIER_BRIEF.md` was written after the plants were chosen. It uses category words only, but some sit close to particular plants: "error model" (Q09), "exceptions" (Q11), "instance"/"subset" (Q15). This is stated here so the reader can weigh it.
- **Thin wrong-restriction control.** The post-build wrong-restriction control tested one alternative restriction (denominator) per qualifier plant. It is weak evidence that the auto-patterns resist Q-style wording. Adjudicators review every AUTO_HIT regardless.
- **N02 auto-pattern gap.** `\b76\b` cannot match "76x" after normalisation, so N02 hits come only from adjudication.
- **Recommended before launch (A1):** one fresh agent (not a verifier, not this team) confirms, against each cited source, that each of the 9 qualifier deletions leaves its sentence false or overstated. If a plant is judged still true, record a pre-run deviation and drop it from the primary metric before any run. The only evidence so far is this team's own validators.

## D2 (orchestrator, before any verifier run): independent plant-strength audit (PLANT_AUDIT.md)
The qualifier plants were audited: STRONG 6, WEAK 2 (Q10, Q16), TRUE 1 (Q09: 4.3σ is already the most conservative of the three
gap_d36 z-values, so deleting the label cannot overstate it).
- Q09 is dropped from the primary metric; primary qualifier recall is over 8 plants.
- A sensitivity figure over the 6 STRONG plants only is reported beside it.
- All 6 controls were confirmed clearly wrong.
- Q09 is still scored and reported descriptively.
- The frozen thresholds (≥0.5, Δ ≥ 0.3, CI lower bound > 0, FP ≤ G+5) are unchanged.

## D3 (orchestrator, before any verifier run): prompt delivery
Each run's brief (briefs_sent/<R>.md, unchanged) is copied into its staged directory as `_TASK.md`. The agent's prompt is one
fixed line, identical for every run and both arms: "Your complete task instructions are in <d>/_TASK.md. Read that file first
and follow it exactly; it is your entire brief." The brief text the agent works from is byte-identical to the frozen prompt.
The rule "read only inside d" is unaffected, because _TASK.md is inside d.

## D4 (orchestrator): the D3 copy step failed silently
staging.tsv has 3 columns, so `read R d` put "dir<TAB>first" into d and no _TASK.md was written. All 12 agents were launched
before the copy was fixed. Agents that started first found no brief, did no review, read no plant, and reported this. The
briefs were then copied (12/12 verified). Each affected agent is re-dispatched with the same one-line prompt. Nothing was scored
or seen, so these runs are not re-runs after data.


## D187 (found 2026-10-06): the freeze hash covered only the header
See FREEZE_ATTESTATION.md. The transcripts show no post-freeze edit to the protocol body; the post-hoc body hash is recorded there.
