# rcs wave 6 — deviations from PREREG.md (sha16 a27ffaeac26a1ce3, frozen 2026-09-26 12:15:11 -04:00)

## D1 — bit-string key convention was wrong in PREREG §5. The pre-registered V3 control caught it.
**What happened**
- PREREG §5 assumed that BlueQubit count keys are little-endian (qubit 0 = rightmost character).
- V3 (job `bX2WQF8flRjiQOFM`: 61q, d = 2, χ = 64, only qubit 0 flipped, 1e4 shots) returned the single string
  `1000…0` in 10000/10000 shots.
- So BlueQubit `mps.cpu` puts **qubit 0 at the leftmost character**.
- Under the PREREG key, V3 scored hits = 0 and reversed-key hits = 10000. As pre-registered, this blocked the
  61q scan. At that moment no 61q analysis cell had been submitted.

**Fix**
- `mirror_lib.bitstring_key` now returns qubit 0 leftmost.
- `controller.py` tags every newly processed cell with `key_convention: "q0_leftmost"`.
- Cells processed before the fix are re-scored in `analyze.py` from their stored `reversed_key_hits`, which was
  computed from the same returned counts. The raw cell files are unchanged. Only V3 was processed before the fix;
  V1/V2 were still in flight.
- `results/state.json`: the V3 entry was edited to hits = 10000 so that the V3 gate reads the re-scored value.
  The old value is kept as `hits_raw_old_key` = 0.
- Under the corrected key, V3 survival = 10000/10000 = 1.0 and reversed-key hits = 0. It passes the PREREG §9
  criterion as re-scored.

**Side effects**
- V3's stored Hamming histogram is relative to the wrong key: "2": 10000 means qubit 0 and qubit 60 differ. It is
  not used.
- The controller process was stopped and restarted to load the fix. The three in-flight jobs (V1, V2 χ = 4, V2 χ = 8)
  kept their job ids, with no resubmission.

**Scope of the change**
- The fix changes only the readout key, not the circuits, cells, order or statistics.
- The own-MPS path is unaffected: it evaluates ⟨x|ψ⟩ by qubit index directly.

## D2 — launch mechanics (no effect on data)
- The first launch used `nohup … &` inside a tool call. Both processes were killed when that call returned.
- A relaunch was refused by the memory guard: MemAvailable was 18.6 GiB against the 20 GiB floor.
- Both processes now run under `supervise.sh`, which relaunches a guarded script only when MemAvailable ≥ 20 GiB.
  The guard stays the first statement of every script.
- Jobs already submitted kept running server-side, and the resumable state file held their ids.

## D3 — own-MPS SVD non-convergence (numerical robustness only)
- The local runner stopped at cell `L_chi128_i1_d12`. `numpy.linalg.svd` (LAPACK gesdd) raised
  "SVD did not converge". The supervisor relaunched it into the same deterministic failure 22 times,
  13:0x–13:17. No cell file was written for the failing cell.
- Fix (`own_mps.py`): on `LinAlgError`, fall back to `scipy.linalg.svd(..., lapack_driver="gesvd")`. This is the
  same decomposition with a more robust algorithm. The truncation rule is unchanged.
- The number of fallbacks per cell is recorded as `svd_fallbacks`.
- Cells completed before the fix never raised, so they are unaffected.

## D4 — the 4 h runtime-cap rule could not fire as coded (implementation fix, same rule)
- `JobResult.run_start` is `None` while a job is RUNNING. BlueQubit fills it only at completion.
- So the PREREG §4 cap ("any job running longer than 4 h is cancelled") could never trigger in `controller.py`.
- Fix: the running time is measured from the first poll that sees status RUNNING (`first_seen_running`).
- For the three jobs already in flight at 13:2x, the value was set to their submission time. That was P1, P2 and
  M_i1_d36_chi256. This choice is conservative for the cap: it counts queue time as running time. Observed queue
  times so far were 1.7 min (V3).
- BlueQubit's own runtime estimates, seen at 13:21, were 5071 s for P1 (χ = 128) and 18587 s (5.2 h) for P2 and
  M_i1 (χ = 256). `estimate()` was already recorded as unreliable in PREREG §4 (off by 0.25×–35× on the validation jobs).

## D5 — shots cut to 2e5 on every 61q cell, `force_run=True`, and the three 1e6-shot jobs cancelled and requeued
**Decided at 15:44 (2026-09-26), blind:** no 61q BlueQubit analysis value had been returned. Only V1–V3 (validation)
had completed.

**What we observed**
- BlueQubit `mps.cpu` wall time is set by the number of shots, not by χ:
  - the 16q validation jobs took 391–437 s at every χ from 4 to 256 (1e5 shots each);
  - V3 (61q, χ = 64, 1e4 shots) took 198 s;
  - own numpy MPS evolves the same 61q d36 circuit at χ = 128 in about 2.5 min.
- P1 (61q d36 χ = 128, 1e6 shots, job `K9Jesm1R0UgsbTkZ`) was **TERMINATED by the server at 15:40** after 3.25 h,
  with the message "taking much longer than the estimated runtime of 5071 s".
- At about 20 ms per shot at 61q, 1e6 shots cannot finish under the PREREG 4 h cap.

**Changes**
1. Every remaining 61q non-validation cell uses **2e5 shots**. This is PREREG §4's own value for χ ≥ 512, with its
   stated resolution argument: at the hardware d36 level of 2.241e-3, 2e5 shots gives ≥ 448 expected hits, and the
   zero-hit upper limit is 1.5e-5.
   Contingency, stated now and based only on runtime: if the first completed 2e5-shot d36 cell took > 2 h, the cells
   not yet submitted use 1e5.
2. `force_run=True` on every 61q non-validation submission. The server-side runtime termination is the "runtime"
   case of PREREG §4. The controller had misclassified P1's termination as an ordinary failure and resubmitted it
   without force_run (job `65spVJwN1kABGWSa`, cancelled at 15:44 before any result). That misfire is not counted as
   the cell's retry.
   The 4 h own cap and the 9.5 h deadline are unchanged and binding.
3. P2 (`kUToY3H5K2Ya5eeX`) and M_i1_d36_chi256 (`G1bju9sxfaZ2Dhxh`), both χ = 256 at 1e6 shots, running since
   12:28/12:31, were cancelled at 15:44 and requeued at 2e5.
   - Reason: P1 at the cheaper χ = 128 had not finished in 3.25 h. These jobs would very likely hit the own 4 h cap
     at 16:28/16:31 and return nothing, and requeuing gives the three d36 instances slot-time before the deadline.
   - All cancelled jobs reported cost 0.0.
4. The controller now takes a heartbeat lockfile, so a second controller cannot run and double-submit.

**Unchanged:** priority order, runtime-prediction rule, statistics, and verdict wording.

## D6 — the BlueQubit arm is void: the service removes U·U† before any MPS truncation (post-hoc diagnosis)
**What triggered it**
- Two 61q d36 cells returned **200000/200000**: P1_i0_d36_chi128 (`MoR7ocniChE76r2B`) and M_i1_d36_chi256
  (`b1fgyZTXjqDMV7CD`), completed 16:48. Both had `mps_build_time` ≈ 1.8–1.9 s and a single distinct string.
- Own MPS gives 1.2e-7 (χ = 128) and 1.3e-6 (χ = 256) for inst 0 on the same circuit.
- At 16:49 the controller was stopped and two just-started main jobs were cancelled: M_i2_d36_chi256
  `qtLl3lJPF9DxdG64` and M_i1_d36_chi128 `6i58BaXnYErprfx1`. Both cost 0.0.

**Post-hoc diagnostics** (not pre-registered; scripts `posthoc_diag_collapse.py` and `posthoc_diag_buildtime.py`;
results in `results/posthoc_diag_*.json`). All use inst 0, input k = 0, force_run.

| Job | Circuit | χ | Survival | Distinct strings | `mps_build_time` | Own MPS (same circuit) |
|---|---|---|---|---|---|---|
| (a) `n2hpUi8taRGSZeGm` | derived d36 mirror, no barriers | 16 | 200/200 | 1 | 1.86 s | 2.5e-10 |
| (b) `P3tPl9GtXdAPNQDF` | same mirror, barrier after every released segment | 16 | 200/200 | 1 | 1.95 s | — |
| (c) `whzBEkNfkOCtsQ2W` | forward-only U (18 cycles, no inverse) | 256 | — | 100/100 | **351.4 s** | — |
| (d) `yvh6cl1eCw9AYB9u` | the mirror with rx(π) on q30 inserted between U and U† | 256 | input key 0/100 | 100/100 | **471.9 s** | — |

**Reading**
- The plain mirror is never evolved as a circuit. Its build time is about 1/200 of the build time of its own
  first half.
- A deep 61q circuit cannot be exact at χ = 16. So BlueQubit `mps.cpu` simplifies U·U† (inverse-gate cancellation)
  before simulation.
- The cancellation also works across barriers (b).
- The 16q validation path did evolve: V2 gave 0.199 / 0.028 / 0.618 at χ = 4 / 8 / 16, not 1. Why the 16q and 61q
  paths differ is **unexplained**. It is also unknown whether partial cancellation affected V2.

**Consequence**
- Applied literally, PREREG §7/§8 would score the BlueQubit arm **MATCH** (F_mps(36) = 1 ≥ F_hw). That outcome is
  **void**: no bond-limited truncation happened, so the sentence "a free χ = … MPS matches" would be false.
- The verdict follows the pre-registered §9 route: V2 failed its consistency criterion, so the own-implementation
  MPS carries the verdict as a labelled substitute. D6 adds a second, independent reason for that route.
- All remaining pending BlueQubit mirror cells are marked NOT RUN, reason "D6: instrument invalid (compile-time
  U·U† cancellation)". Every one of them would return 1.0 and occupy the shared queue.
- P2 (`XtkW9KV80vuDviXD`) is collected and reported in the literal table, flagged `invalid_D6`.
- Cell F (the full logical d36 circuit, not a mirror) is unaffected and is still run as a feasibility fact. See D7.

## D7 — cell F: shots cut to 1e3; an extra χ = 512 feasibility run (exploratory)
- F's hits are meaningless: it is not a mirror. Its purpose is to record the job id and the runtime. At 1e6 or 2e5
  shots the sampling time (~19 ms/shot at 61q) would swamp the build time, so F runs with **1e3 shots**.
- χ is still the PREREG χ_top rule. It resolves to 256, because no χ ≥ 512 d36 cell ran (D6).
- Additionally, and exploratory: F at χ = 512 (1e3 shots), because its build is predicted to fit the deadline.
  - The prediction scales the diagnostic (c) build time of 351 s (401 CZ, χ = 256) by 918/401 CZ and by χ³.
  - That gives ≈ 804 s at χ = 256, ≈ 1.8 h at χ = 512, ≈ 14 h at χ = 1024 and ≈ 115 h at χ = 2048.
  - χ ≥ 1024 is recorded as NOT RUN on that prediction.

## D8 — D6 corrected: the cancellation is intermittent, not systematic. A build-time validity rule, and re-runs of collapsed cells
**What changed our reading**
- P2_i0_d36_chi256 (job `XtkW9KV80vuDviXD`, 2e5 shots, the same circuit family as P1) finished at 17:36 with
  **`mps_build_time` = 847.5 s** and hits = **1/200000**. There were 100000 distinct strings in the truncated list,
  and the input key was present.
- So the service **genuinely evolved** this mirror.
- Of the 4 plain 61q mirrors run, 3 collapsed (build ≈ 1.8–1.9 s, survival exactly 1): P1 χ = 128, M_i1 χ = 256, and
  diagnostic (a)/(b) at χ = 16. One was genuine: P2.
- The trigger is unknown. It is not χ and not the instance: inst 0 collapsed at χ = 128 but not at χ = 256.
- D6's statement "the BlueQubit arm is void" is corrected to: **each BlueQubit 61q mirror result must be classified
  as evolved or collapsed.**

**Validity rule** (fixed at 17:40, before any re-run result exists, and independent of hits)
- A 61q mirror cell is **collapsed** if `mps_build_time` < 10 s. Collapsed cells are invalid.
- For comparison: genuine 61q builds seen so far are 351–847 s; the collapsed ones are 1.8–1.9 s.
- Collapsed cells get **one re-run**. If the re-run also collapses, the cell is NOT RUN (collapsed ×2).
- An evolved re-run counts whatever its hits are.

**Re-queued**
- M_i1_d36_chi256, M_i2_d36_chi256 (the latter was cancelled at 16:49 before any result), P1_i0_d36_chi128,
  M_i1_d36_chi128, M_i2_d36_chi128, all in PREREG priority order.
- The scan_256 cells are also set back to pending in PREREG order. The 9.5 h deadline (21:45) will cut them.
- Shots stay at 2e5: the D5 contingency did not fire, because P2 took 6680 s < 2 h.
- The D6 diagnostics remain valid as a description of the collapsed runs.

## D9 — bookkeeping of collapsed runs
- Collapsed cell files were moved to `results/cells_collapsed/<id>.runN.json`. They are excluded from the analysis
  under the D8 rule, and the raw content is unchanged.
- Every job id, including the superseded and collapsed ones, is kept in `results/state.json`
  (`superseded_jobs` / `collapsed_jobs`) and in the cost journal `results/bq_jobs.jsonl` (all rcs wave6 costs are 0.0).
- The deadline cancelled S256_i1_d28 (`VJ5I6Xsv3Bs8NUXV`) and S256_i2_d28 (`26jbQ4nw9LqvqaJU`) at 21:46. Both are
  NOT RUN.

## D10 — analysis-side departures from PREREG §7/§8 (none of them touches the headline)
1. `pool_bq` uses se_i = √(max(p(1−p), 1e-12)/shots), not √(p(1−p)/shots). This is the same floor as wave-3's
   `instance_survival`. It matters only at p = 1, and p = 1 occurs only in the collapsed (void, D6/D8) cells, where
   the literal formula gives se = 0 and an undefined IVW.
2. `verdict()`: when no χ has all 3 instances completed, χ_max falls back to the largest χ run. PREREG §8 defined
   χ_max over all 3 instances. The field `chi_max_has_all3` records which case applies. For the BlueQubit arm it is
   False (2 of 3 instances), so all text says "χ ≤ 256 on 2 of 3 instances".
3. Post-hoc uncertainty statements (`results_intervals.py` → `results/intervals.json`, lesson A8):
   - exact Poisson (Garwood) 95% interval on the 4 pooled BlueQubit hits at d36 χ = 256, which gives a ratio range
     of 88–822;
   - per-instance ratio range for the own MPS: 1712–8604.
   Neither is a pre-registered statistic.
4. The only BlueQubit d36 instance that never evolved was inst 1. In the own MPS it has the lowest survival
   (2.6e-7), so its absence is probably not random: had it evolved, the BlueQubit ratio would likely be higher.
   This is post-hoc reasoning, not a measurement.
