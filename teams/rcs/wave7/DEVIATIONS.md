# rcs wave 7 — deviations and observations (PREREG sha16 8205a246afeaa95a, frozen 2026-09-26 22:11:59 -04:00)

## W1 — two selected variants are the same computation (observation; no rule changed)
- The pilot selected LOG_SB, TWR_NSB, CSN_NSB, CRA_NSB, RCM_NSB and LOG_NSB (N = 6, PREREG §4.3).
- CRA_NSB and CSN_NSB give **identical** survivals to all printed digits in all 6 pilot cells and in all 3 d36
  χ = 128 headline cells (e.g. inst 0: 8.352806369e-08 in both).
- Post-hoc diagnostic (`posthoc_diag_nsb_convergence.py`, inst 0 derived d8, χ = 16; run at 01:3x on 09-27):
  the two initial orderings differ at 28 of 61 sites, but under no-swap-back routing both reach the same
  logical→site permutation. The identical survivals show this happens before any truncation that differs.
- Consequence: the pre-registered set has N = 6 labels but **5 distinct computations**. Every statement of "best
  of N variants" in this wave says "6 pre-registered variants (5 distinct)". The best-of maximum is unaffected.
  The duplicate cells are still run as pre-registered (no rule changed).

## W2 — power loss and reboot on 09-27 (interruption only; no rule changed)
- The machine lost power at about 12:27 on 09-27 and rebooted. The runner and supervisor died.
- At that moment 143 cells were done; all 143 JSON files parse (orchestrator check).
- One cell was in flight: H_LOG_SB_c512_d36_i0 (d36, χ = 512, the first χ = 512 cell). It started at 10:57:36
  with a predicted time of 8857 s and wrote no result. No value of it has been seen.
- `results/runner.lock` was left on disk, dated 10:35. The runner uses a kernel `flock`, not the file's
  existence, so a leftover file blocks nothing. A non-blocking flock probe at 12:32 acquired it, which means
  no process held it. The file was left in place.
- The interrupted cell stays `pending` with attempts = 0. It is recomputed from scratch. This is the same
  deterministic computation, so it is not a retry after seeing data (PREREG §5 treats an external kill like a
  memory wait: not an attempt).
- Frozen script hashes were re-verified. The supervisor was relaunched at about 12:33 with the same 20 GiB floor
  and the one-process rule.
- Wall time lost is about 1.5 h (10:57 → 12:33). The deadline (2026-10-01 20:00 EDT) is unchanged.

## W3: second power outage (2026-09-27 ~14:20). Interruption only; no rule changed.
The in-flight cell H_LOG_SB_c512_d36_i0 was lost again with no result written. It had restarted at 13:10:40 after a mid-cell
memory wait. 143 done cells are intact (0 corrupt) and all script hashes pass. The orchestrator relaunched supervise.sh; the cell recomputes from scratch.

## W4: runner stopped with the orchestrating session (2026-09-28 14:18); deadline passed unattended. No rule changed.
Written 2026-10-02 BEFORE analyze.py was run, so the analysis outcome was unknown when this was recorded.
- supervise.sh ran as a background task of the orchestrating Claude session. When that session ended, the supervisor and
  runner stopped. runner.log's last line is `09-28 14:18:16 START H_CRA_NSB_c512_d36_i0`; no cell ran after that, and the
  in-flight cell was lost with no result written. Nobody noticed until 2026-10-02.
- Under PREREG §5 every cell not started by 2026-10-01 20:00 EDT is NOT RUN (deadline). That is the outcome here, though the
  cause was the stopped runner, not compute running out. 149 cells are done: d36 χ = 128 and χ = 256 complete (18 + 18),
  d36 χ = 512 partial (6 of 18), d28 none. So χ_max(36) = 256, with χ = 512 a partial addendum (PREREG §7).
- §5 says analyze.py runs automatically when the deadline has passed; it did not, because the runner was dead. It is run
  by hand now, unmodified (hash-checked against PREREG.sha16 at start). The cells were not restarted after the deadline.
- Lesson: a multi-day pre-registered run must not be owned by a chat session. Run it under a supervisor that survives the
  session (systemd user unit or tmux outside the agent sandbox), and add a heartbeat check that alerts when runner.log
  goes quiet.

## W5: addendum runner mis-handled a memory interruption (2026-10-02 15:46); fixed. No addendum rule changed.
- Other work on the shared machine drove MemAvailable below 12 GiB mid-cell; cell.py's guard aborted H_CRA_NSB_c512_d36_i1
  with rc 3 (MEMLOW). The frozen runner.py treats rc 3 as a memory interruption, "not an attempt": wait, then re-run from
  scratch (runner.py lines 144–147). post_deadline.py v1 instead recorded it as a FAIL and would never re-run it, contrary to
  the addendum's own text ("calls the frozen cell.py ... as runner.py did"; interruptions are re-run from scratch).
- Fix: post_deadline.py now applies runner.py's return-code semantics (rc 3 → wait and re-run; rc 4 → NOT RUN, RSS cap;
  anything else → FAIL, not retried). The v1 script is kept as results_post/post_deadline.v1.py and the wrong marker as
  results_post/H_CRA_NSB_c512_d36_i1.memlow_interruption.txt. The cell re-runs from scratch; cells are deterministic, so no
  result depends on this.
