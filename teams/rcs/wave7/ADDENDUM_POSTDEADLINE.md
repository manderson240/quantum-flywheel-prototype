# Addendum A1 to PREREG.md: completing the d36 χ = 512 cells after the deadline (frozen 2026-10-02)

Frozen BEFORE anyone has read results/analysis.json (the confirmatory χ ≤ 256 verdict, produced 2026-10-02 by the
unmodified analyze.py after deviation W4). Its sha256 prefix is written to ADDENDUM_POSTDEADLINE.sha16 and added to
graph/gate.py before the first addendum cell starts.

## Why
The runner stopped with the orchestrating session on 2026-09-28 (W4), so 12 of the 18 pre-registered d36 χ = 512 cells
never started before the 2026-10-01 20:00 EDT deadline; under PREREG §5 they are NOT RUN, and the confirmatory headline is
χ_max = 256. Nothing here changes that headline or any confirmatory output.

## Cells (fixed now; no other cells, depths or χ)
9 cells, d = 36, χ = 512, in this order (χ = 256 ranking by mean survival, best first; instances 0, 1, 2 within each):
CRA_NSB i0–i2, RCM_NSB i0–i2, LOG_NSB i0–i2. CSN_NSB is not run: it is the same computation as CRA_NSB (W1), confirmed
again on 2026-10-02 at all six χ = 128/256 cells (agreement to ~10 significant figures), so the best-of is unchanged. d = 28
stays NOT RUN.

## How
post_deadline.py calls the frozen cell.py with the same spec ({"kind": "mirror", "variant", "inst", "d": 36, "chi": 512}),
the same threads (state.json "threads"), nice 10, writing to results_post/cells/. Before each cell it checks every frozen
script against results/scripts_at_freeze.sha256 and refuses on mismatch. It waits while MemAvailable < 20 GiB. It never
runs runner.py or analyze.py and never writes to results/.
Hard stop: 2026-10-06 12:00 EDT. A cell not started by then is NOT RUN (addendum stop); a running cell is killed at the stop.
No retries beyond re-running a cell lost to an interruption (power loss, reboot), from scratch.

## Analysis and reporting (fixed now)
- post_analyze: copy wave7's scripts and results into a scratch directory, add the addendum cells as done, run the
  unmodified analyze.py there. CHECK FIRST: its χ = 128 and χ = 256 outputs must equal the confirmatory analysis.json exactly;
  any difference means the merge is wrong and nothing is reported.
- The χ = 512 best-of margin is reported only if all 5 distinct variants × 3 instances are done at χ = 512, as:
  "completed after the pre-registered deadline (deviation W4): at χ ≤ 512 the factor is <r512>". Otherwise as a partial set
  with the cell count. It never replaces the χ ≤ 256 headline. PREREG §7's lead rule (smaller margin first) and scope
  sentences apply.
