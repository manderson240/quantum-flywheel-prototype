# PREREG — Headroom probe for Experiment A (ai_contribution, wave 1, 2026-09-25)

Status at freeze: NO probe data exists. The only runs so far are instrument checks:
- `feasibility_pergate.py` (12 qubits, exact-checkable), and
- `instrument_check.py`, which ran exact MPS runs and recorded timing/cost for constant χ.

No truncated-run error on any 19-qubit circuit has been computed or printed. `instrument_check.py` computes errors only for the exact runs.

## Question
Experiment A (research/20260925-ai-contribution.md §3) asks whether an LLM program search over MPS truncation schedules beats textbook truncation at equal cost. That question is only informative if a schedule better than the best constant truncation setting exists at all. This probe tests that precondition. It runs strong non-LLM searches, and every searcher is scored against exact oracles:

> At equal deterministic cost, does any per-cycle truncation schedule beat the best **constant** truncation setting by at least 0.10 log10 on the dev circuit, and does the dev-selected schedule stay ahead on held-out circuits?

## Environment (discrepancy recorded)
The brief pointed to the cohezion venv. quimb is **not** installed there. The system Python has it: linuxbrew Python 3.14.3 (`python3`), with quimb 1.13.0, cotengra 0.7.5, numpy 2.4.4 and qiskit 2.5.2. Nothing was installed for this probe.

Run conditions:
- every process: `OMP_NUM_THREADS=1`, `nice -n 10`
- 4 workers
- peak RSS per run: 395 MB at χ ≤ 64 and 340 MB at χ = 128 (both measured)

## Feasibility result (step 1, before this freeze)
quimb's `Circuit._apply_gate` merges options as `opts = {**self.gate_opts, **gate_opts}`, so a per-call value overrides the constructor default. This was checked with 12 qubits, including non-adjacent gates on the swap path (`results/feasibility_pergate.json`, sha16 d80d8326110dc850). Results:
- per-gate `max_bond=4` over a constructor default of 32: realised bonds [4]*6, fidelity 0.38 against 0.95
- per-gate `cutoff=1e-2` (rsum2): bonds [4,7,8,7,6,5] against [4,16,64,…]
- a per-layer χ schedule [2..64] is realised exactly
- a misspelled key **raises** a TypeError, so it is not silently ignored
- the exact engine matches an independent dense statevector (fidelity 1 − 3e-15)

## Instruments (frozen)
- **Engine:** `probe_engine.py` runs quimb `CircuitMPS` with the default `swap+split` method. The circuit content is imported read-only from `floquet_oracle19.py`:
  - per layer: RX(tx/3) and RZ(tz/3) on every qubit, then RZZ(π/3) on one edge colour
  - 3 layers per cycle, 16 cycles
  - 19-qubit heavy-hex (distance 3)
  - qubit→site ordering is the spectral (Fiedler) ordering, fixed; pilot 2 found no headroom in ordering
- **Truth:** the stored exact values are reused, not recomputed:
  - dev = `results/floquet_oracle19.json` (tx=1.56567, tz=0.33879, colour seed 0; sha16 50574b3018f0c628)
  - held-out HO1 = `results/floquet_oracle19_tx4.7_tz0.3_c5.json` (sha16 39b326aa6ba1d6a4)
  - held-out HO2 = `results/floquet_oracle19_tx2.4_tz0.9_c5.json` (sha16 2b7231c30002aacc)
  - Instrument check: the engine run exactly (max_bond=None, cutoff=0) reproduces all 81 stored values to ≤ 1.9e-14 (`results/instrument_check.json`, sha16 9c9b8eacb3041f6f). That is a second, independent implementation of the Qiskit-Statevector truth.
- **Cost (the budget metric):** Σ over the 48 RZZ layers of Σ_bonds χ_b³, measured after each layer. It is deterministic and tracks SVD cost. Wall time is logged as a secondary measure and is not used for scoring.
- **Silent-ignore detectors (frozen):**
  - after every layer, the realised max bond must be ≤ the scheduled max_bond
  - at χ=64, every grid run with ε ≥ 1e-4 must end with a smaller max bond than the ε=0 run at χ=64 on the same regime
  - any violation makes the verdict INCONCLUSIVE (instrument)
- **Metric (primary):** the one Exp A uses. Take the median over the 18 dev instances (cycles 4, 6, 8, 10, 13, 16 × {mag, ZZ d=2, ZZ d=3}) of log10|err|, with |err| floored at 1e-12. Lower is better. **Secondary:** log10 of the mean absolute error, reported only.

## Budget levels
C_k is the dev cost of the library default at constant χ_k:

| Level | χ_k | C_k |
|---|---|---|
| L8 | 8 | 331,215 |
| L16 | 16 | 2,227,151 |
| L32 | 32 | 14,240,719 |

These come from `instrument_check.json`. Only timing and cost were used there, not errors.

## Arms (equal budget)
1. **Constant settings, the baseline (B).** A 2-D grid of χ ∈ {4,5,6,7,8,10,12,14,16,20,24,28,32,40,48,56,64} × ε ∈ {0, 1e-8, 1e-7, 1e-6, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2}, making 187 settings, run on all 3 regimes.
   - ε = 0 means quimb's **library default** cutoff and mode (1e-10, `rel`) with max_bond = χ. This column is the "library default truncation". quimb's *unconstrained* default (max_bond=None) is exact at 19 qubits (cost 1.3e10, about 40 s), so it cannot serve as a budgeted baseline. We state that openly.
   - ε > 0 uses `rsum2`, the textbook discarded-weight truncation. The χ=64 row with ε > 0 is the "textbook adaptive cutoff".
   - B*_k is the best constant setting with dev cost ≤ C_k. Q_k is the number of grid settings with dev cost ≤ C_k.
2. **Random search over schedules (3 seeds).**
   - The schedule is χ(cycle), interpolated linearly in log2 χ through 4 knots at cycles 1, 6, 11 and 16 and then rounded. There is also one ε (rsum2), drawn log-uniform on [1e-9, 1e-2].
   - Knots are drawn uniform on [2, log2(2χ_k)] **per level**.
   - Each seed evaluates its seeded draw stream in chunks of 40 until it has Q_k in-budget evaluations, up to a maximum of 748 draws.
   - Only its first Q_k in-budget evaluations, in draw order, are scored. This gives equal in-budget evaluation counts with the baseline.
3. **Hill-climb, the oracle-side upper-bound probe.** This is a deterministic greedy coordinate search over the 4 knots and log10 ε.
   - It starts from B*_k.
   - Steps are ±0.5 in log2 χ per knot, all knots together, or ±0.5 in log10 ε. The step halves after any pass with no improvement, down to a minimum of 0.0625.
   - A candidate is accepted only if cost ≤ C_k and the metric is strictly lower.
   - It gets 187 simulations per level; duplicate integer schedules are cached and not counted. This is more search than B gets, which is deliberate: it makes a NO-HEADROOM verdict strong. A positive verdict is guarded by the held-out test.
4. **S*_k** is the best dev schedule at level k over arm 3 plus the scored evaluations of arm 2. S*_k is then run on HO1 and HO2.

## Scoring (analyze.py, frozen)
- **Dev headroom at level k:** Δ_dev = m(B*_k) − m(S*_k), required to be ≥ 0.10 (log10).
- **Held-out, primary:** conservative hindsight frontier. For each HO regime r, F_r is the best constant grid setting on r whose r-cost is ≤ the r-cost of S*_k. Then Δ_ho,r = m_r(F_r) − m_r(S*_k). The level passes held-out if the mean over the two regimes is ≥ 0.05 and both values are > 0.
- **Held-out, secondary (reported, not scored):** transfer. Δ = m_r(B*_k) − m_r(S*_k), with both costs reported.
- A level is **scored** only if every random seed reached Q_k in-budget evaluations. Otherwise it is UNSCORED, which is not the same as a negative.

## Verdict (frozen rules)
| Verdict | Condition |
|---|---|
| INCONCLUSIVE | Any instrument failure (bond violation, cutoff ignored, or > 5% failed runs in any phase), OR fewer than 2 scored levels |
| HEADROOM | At least 2 scored levels pass both the dev and held-out criteria |
| DEV-ONLY (headroom does not transfer) | At least 2 levels pass dev, but fewer than 2 pass both |
| NO HEADROOM | Otherwise |

## Missing runs / retries / memory
- A failed simulation is retried once with identical input, then recorded as `failed` and excluded. It still counts toward the draw budget.
- Before every run, the worker checks MemAvailable. Below 20 GiB it waits 60 s, doubling to at most 900 s. After more than 2 h of waiting it aborts and the verdict is INCONCLUSIVE.
- A phase interrupted for any other reason is resumed from its JSONL. Records are keyed, so there is no re-scoring. An interrupted hill-climb level is re-run from its start.
- No BlueQubit jobs are needed and none will run.

## What we will conclude
- **NO HEADROOM.** At 19 qubits on this family, textbook constant truncation (library default or discarded-weight cutoff) is already within 0.10 log10 of the best schedule that strong non-LLM search finds. Experiment A as designed would be uninformative here, and the application must not promise it as the positive AI test. The honest alternative is to state the negative and redirect any AI claim.
- **DEV-ONLY.** Schedules can be over-fitted to one circuit, but the gain does not transfer. Exp A's held-out test would likely return False, and running it would mainly re-measure over-fitting.
- **HEADROOM.** A gap exists that a searcher can find and that transfers across regimes. Exp A is worth running, and it must beat this probe's hill-climb and random-search arms, which become Exp A's non-LLM baselines.
- **Limits in every case:** one lattice at 19 qubits, one family, 3 regimes, 18 instances per regime, and one ordering. The result says nothing about 51 qubits.

## Frozen code (sha256 prefix, 16 hex)
| File | sha16 |
|---|---|
| probe_engine.py | d83a9ec26cf6fc4d |
| runner.py | ebb4084e6e2d819a |
| analyze.py | d83a48ad4af31567 |
| feasibility_pergate.py | f075a9376dfd4f40 |
| instrument_check.py | 2d266770b3b1f1e3 |
| ../../floquet_oracle19.py (read-only import) | 374645fa52daa897 |

Run order: `runner.py grid` → `runner.py random` → `runner.py hillclimb` → `runner.py heldout` → `analyze.py`.
