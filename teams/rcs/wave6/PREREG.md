# rcs wave 6 — PREREG: free bond-limited MPS vs the device on the paper's own mirror-survival metric

Frozen before any BlueQubit data job of this wave. sha256[:16] in `PREREG.sha16`; `controller.py` and
`local_runner.py` refuse to run on a hash mismatch. Scripts: `mirror_lib.py` (circuit derivation), `plan.py`
(frozen cells, inputs, order), `controller.py` (BlueQubit jobs), `own_mps.py` + `local_runner.py` (own MPS),
`analyze.py` (written after this freeze; it must implement §6–§8 literally).

## 1. Question and scope
arXiv:2609.28657 (61 qubits, IBM Nighthawk r2) uses a mirror benchmark: input bitstring x, circuit U·U†,
survival = fraction of shots returning x. Test: on that metric, how does a free, bond-dimension-limited MPS
(BlueQubit `mps.cpu`, χ ≤ 2048, $0) compare with the hardware as depth grows? Deliverables: d*(χ), the smallest
scanned depth from which the hardware exceeds the MPS (§7), and the ratio hardware/MPS at d = 36.

Scope limits, stated in advance:
- Mirror survival of U·U† is a proxy. It is not the fidelity of sampling the 36-cycle RCS circuit U. In a
  depth-d mirror the MPS truncates only through the d/2 forward cycles before the entanglement unwinds.
  **No claim about the RCS advantage claim itself** beyond this metric.
- Our depth-d circuits are **derived from the released d36 instances, same instance** (§2). The paper's depth-d
  hardware instances are separate random draws that are not in our download, so circuit-to-circuit scatter
  separates the two sides.
- The hardware input bitstrings were not released. Ours are seeded (§2).

## 2. Circuits and inputs
- Source: `refs/rcs-nighthawk-data/data/circuits/mirror/d36_instance{0,1,2}.qasm`. These are parsed by regex with
  `qasm_angle.angle`: no qasm3 importer, no eval.
- Each file is 61 `rx(θ_i)` input gates followed by 72 barrier-separated segments.
  - The first 36 segments are U: 18 cycles of (1q layer rz·rx·rz, CZ layer).
  - The last 36 segments are U†.
  - `mirror_lib.load_instance` asserts that backward segment k is the exact inverse of forward segment 35−k.
- The **derived depth-d mirror** (d even) is the input layer, then the first d/2 forward cycles, then the
  matching last d segments of the same file (their inverse). Scanned depths: d ∈ {8, 12, 16, 20, 24, 28, 32, 36}.
  d = 36 is the released circuit itself (802 CZ). The depth convention is the dataset's: "cycles of U U^dagger".
- Input x is prepared as rx(π) on each qubit with x_q = 1, as on the device (θ = π flips).
  Inputs: `plan.INPUTS[inst][k] = numpy.random.default_rng(20260926).integers(0,2,61)`, drawn in order
  inst 0..2, k 0..1. The main cells use k = 0. The low-priority cells I2 use k = 1.
- MPS chain order = logical qubit index, which is raster order over the 8×8 subgrid. We pass no reordering to
  BlueQubit. The own MPS routes non-adjacent CZs by SWAPs.
- **16-qubit analogue** (validation only): the gates of the derived d36 mirror of instance 0 restricted to
  logical qubits 0–15. Gates touching q ≥ 16 are dropped; restriction keeps the U·U† identity exactly.
  Input: `plan.INPUT16 = default_rng(16).integers(0,2,16)`.

## 3. Instruments
- **Primary:** BlueQubit `mps.cpu`, `options={"mps_bond_dimension": χ}`, default truncation threshold 1e-10.
  Survival is sampled with `shots`.
- **Secondary (independent own code, P2):** `own_mps.py`. It is a numpy MPS in mixed-canonical form. Each
  2-site update is SVD-truncated to χ, dropping s ≤ 1e-10·s_max, and renormalised. It returns the **exact**
  survival |⟨x|ψ_trunc⟩|² with no sampling.
  - It was unit-tested before this freeze on a non-analysis 10-qubit random circuit against its own
    statevector: max amplitude error 2.3e-15 at full χ.
  - Cells are in `plan.local_cells()`, frozen order:
    - χ ∈ {16, 32, 64, 128} × d ∈ {36, 32, …, 8} × inst 0–2, input k = 0;
    - then χ = 256 in d order 36, 28, 20, 32, 24, 16, 12, 8.
  - Limits: nice 10, OMP_NUM_THREADS = 4, peak RSS cap 1000 MB (stop on exceed), same deadline as §4.
  - Own-MPS results are reported separately and labelled "own-implementation MPS". They do not set the primary verdict.

## 4. BlueQubit cells, order, runtime and retry rules (`plan.bq_cells()`, `controller.py`)
Frozen priority order:
1. V3: 61q, d = 2, χ = 64, input = only qubit 0 flipped, 1e4 shots.
2. V1: 16q analogue, χ = 256 (exact).
3. V2: 16q analogue, χ ∈ {4, 8, 16}, 1e5 shots each.
4. P1: inst 0, d36, χ = 128.
5. P2: inst 0, d36, χ = 256.
6. d36 inst 1, 2 at χ = 256, then at χ = 128.
7. d36 inst 0–2 at χ = 512, then at 1024, then at 2048.
8. Depth scan at χ_top in d order 28, 20, 32, 24, 16, 12, 8 × inst 0–2.
9. Depth scan at χ = 256, same order.
10. I2: d36, χ = 256, second input, inst 0–2.
11. F: the full 61q d36 **logical** RCS circuit (`refs/rcs-nighthawk-meta/.../d36_logical.qasm`, 918 CZ,
    all-zero start) at χ_top with 2e5 shots. This is a feasibility fact only: we record job id and runtime.
    Its "hits" are meaningless.

P1 and P2 are ordinary grid points. Their survival values enter the analysis like any other cell.

Shots:
- 1e6 for χ ≤ 256; 2e5 for χ ≥ 512.
- Reason: resolution matters only near the hardware level. That level is 2.241e-3 at d36, which gives ≥ 448
  expected hits at 2e5. A value far below it is already decided as "below hardware".

Concurrency, cost and gating:
- At most **3** of our jobs queued or running at once (orchestrator instruction).
- `cost_ledger.ok_to_spend(0.0)` before each submission.
- `record_job` at submission; `record_cost` at completion.
- **Any completed job with cost > 0 → write `results/STOP_COST` and stop all submissions.**
- No 61q cell other than V3 is submitted until V3 has completed with survival ≥ 0.99.

Runtime rule (cells with χ ≥ 512, χ_top scan cells and F):
- These wait until P1 and P2 are terminal.
- Predicted run time is T = T_ref·(χ/χ_ref)^α·CZ_d/CZ_ref.
  - ref = the completed 61q cell with the largest χ; ties go to the largest d.
  - α = log(T_b/T_a)/log(b/a), where a and b are the two largest distinct χ with completed d36 cells (mean T
    per χ). α is floored at 2 and is 3 if fewer than two such χ exist.
- A cell is **NOT RUN** (with the prediction recorded) if T > 4 h or T > time left before the deadline.
- `estimate()` is not used for scheduling: it gave 47 min for d8 at χ = 256, which is not credible.

Clock:
- T0 = the first submission.
- No submissions after T0 + 9 h.
- At T0 + 9.5 h, running jobs are cancelled and all non-terminal cells are NOT RUN (deadline).
- Any job running longer than 4 h is cancelled and becomes NOT RUN (runtime cap).

χ_top:
- Resolved once all d36 main cells with χ ≥ 256 are terminal.
- χ_top = the largest χ ∈ {2048, 1024, 512, 256} with all three d36 instances completed.
- If χ_top = 256, the χ_top scan duplicates the χ = 256 scan and is marked NOT RUN as a duplicate.

Retries:
- A JOBS_LIMIT_EXCEEDED-type refusal backs off and retries later. It does not count as an attempt or a result.
- A submission rejected for "runtime" is resubmitted once with `force_run=True`.
- A failed or cancelled job (other than the cap/deadline cancels above) is resubmitted at most once. After a
  second failure it is FAILED (missing point).
- No other retries. A cell is never re-run to change its value.

## 5. Readout rule (per job)
Key = little-endian bit string (qubit 0 = rightmost character). V3 checks this convention.

hits:
- If the key is in `top_128_results`, hits = that count.
- Otherwise, if the key is in `get_counts()` (up to the top 100k), hits = that count.
- Otherwise, if that list has ≥ 100 000 entries, hits ≤ min(count) and the cell is flagged `upper_bound`.
- Otherwise hits = 0.

Stored per job:
- hits, shots, reversed-key hits, number of distinct strings returned;
- the Hamming-distance histogram relative to x (over the returned list), top 5 strings;
- job id, run/queue time, cost, device options.

Full count dicts are not stored.

## 6. Hardware estimator (reused, not re-derived)
- Hardware: `refs/rcs-nighthawk-data/data/counts/mirror_survival.json`, via wave 3's own `instance_survival` +
  `ivw` (imported from `teams/rcs/wave3/mirror_analysis.py`; its `main()` is not run).
- Per depth d:
  - F_hw(d), σ_hw(d) from IVW over the 3 instances;
  - B_hw(d) = max(1, √(χ²_d / 2)), the per-depth circuit-scatter inflation.

## 7. MPS pooling, the "hardware exceeds MPS" rule, d*(χ), and the d36 ratio
**BlueQubit, per (d, χ):**
- Per instance: p_i = hits/shots, se_i = √(p_i(1−p_i)/shots).
- If every available instance has exact hits > 0: F_mps = IVW mean, σ_mps its se,
  B_mps = max(1, √(χ²/(k−1))) for k ≥ 2 instances, else 1.
- **Upper-bound mode:** if any instance has 0 hits or an `upper_bound` flag.
  - Zero-hit instances use p_i = 3/shots (one-sided 95%); flagged ones use hits/shots.
  - F_mps = the plain mean of the p_i, σ_mps = 0.
  - F_mps is then labelled an upper bound, and any ratio F_hw/F_mps a lower bound (">").

**Own MPS, per (d, χ):** F_mps = the mean of exact survivals over the instances run, σ_mps = sd/√k (k ≥ 2), B = 1.

**Exceed rule:** hardware exceeds MPS at (d, χ) iff
z = (F_hw − F_mps) / √((σ_hw·B_hw)² + (σ_mps·B_mps)²) > 3.

**d*(χ):** the smallest scanned d with data at χ such that the exceed rule holds at d **and** at every larger
scanned d with data at χ.
- If the rule holds at the smallest depth with data, report "d*(χ) ≤ that depth".
- If it never holds, report "not reached within the scanned depths".
- A non-monotone pattern is reported as such, with no d* claimed.

**d36 ratio:**
- best χ = the χ with the highest pooled BlueQubit F_mps at d = 36 (an upper value in upper-bound mode).
- d36_ratio = F_hw(36) / F_mps(36, best χ).

## 8. Verdict keys and frozen wording (primary = BlueQubit; the own-MPS verdict is stated alongside)
Let χ_max = the largest χ actually completed at d36 on all 3 instances. Never write "χ ≤ 2048" unless 2048 ran.

- **MATCH** — for some χ run, the pooled point estimate F_mps(36) (not upper-bound mode) is ≥ F_hw(36).
  Wording: "on the paper's mirror metric a free χ=<χ> MPS matches or exceeds the device at 36 cycles; the mirror
  benchmark does not by itself separate the device from this classical simulator; hardness then rests on the
  patch estimates."
- **EXCEED** — not MATCH, and the exceed rule holds at d36 for best χ.
  Wording: "the device exceeds a free χ ≤ <χ_max> MPS on its own mirror metric by factor <z> at 36 cycles",
  where z = d36_ratio (">" if a lower bound).
- **INCONCLUSIVE** — neither. Wording: "at 36 cycles the device and a free χ ≤ <χ_max> MPS are not separated at
  3σ on the paper's mirror metric (ratio <r>)."

Every use of these wordings carries the scope sentences of §1. The proxy sentence, the no-claim-about-RCS
sentence and the derived-instances sentence are mandatory.

## 9. Validation (and what failure means)
- **V3 pipeline/endianness** (61q, d = 2, χ = 64). Pass: survival ≥ 0.99 and reversed-key hits ≤ 1% of shots.
  Fail blocks the 61q scan (enforced in `controller.py`); diagnosed in DEVIATIONS.
- **V1 exact case** (16q, χ = 256 = 2^8, exact). Pass: BlueQubit survival ≥ 0.99, and own statevector survival
  = 1 within 1e-9.
- **V2 small-χ agreement** (16q, χ ∈ {4, 8, 16}).
  - Consistent if BlueQubit/own-MPS survival ∈ [0.5, 2] at every χ and BlueQubit survival is non-decreasing in χ.
  - BlueQubit's internal SWAP routing and truncation order are unknown, so exact agreement is not expected.
    This is a factor-2 consistency check, not an identity test.
- If V1 or V2 fails, all BlueQubit results are still reported, labelled "instrument validation failed (V1/V2)".
  The own-MPS results then carry the verdict as a labelled substitute.

## 10. Prior knowledge (disclosed)
- The hardware numbers were known before this freeze (wave 3): F_hw(36) = 2.241e-3 with σ 5.57e-5; the full
  per-depth table is recomputed in §6.
- BlueQubit `estimate()` values were seen: d8 / d16 / d24 / d36 at default χ gave 2.81e6 / 4.75e6 / 6.94e6 /
  1.01e7 ms (`results/est_probe.json`).
- **Before this freeze, a code-timing run of `own_mps` was made on the analysis circuit** (inst 0, derived d36,
  all-zero input, which is not an analysis input).
  - It printed exact survival 3.39e-11 at χ = 32 (7.0 s) and 1.87e-9 at χ = 64 (46.7 s).
  - This informed the shots rule and the priority on high χ. It is not an analysis result, and it is not re-used.

## 11. Exploratory (labelled as such if reported)
- Any extrapolation of survival in χ or d.
- Input dependence (I2).
- Hamming-distance histograms.
- The own-vs-BlueQubit comparison at 61q.
- The runtime-scaling α.
