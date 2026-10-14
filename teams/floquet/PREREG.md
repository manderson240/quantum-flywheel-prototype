# PREREG — floquet team, wave 1: NLCE feasibility for late-cycle Floquet magnetization

Frozen 2026-09-25 before any NLCE prediction exists. The sha256 16-hex prefix is in PREREG.sha16.

## Question
The finite-cluster / NLCE route (decision-path doc, row 6) has two parts:
1. Can a site-based numerical linked-cluster expansion (NLCE), built only from exact simulations of clusters with at most 16 sites, predict the EXISTING exact patch magnetization at n = 27 and n = 33 qubits?
2. Up to which cycle does it work?

## Disclosures
- The exact target values below were visible to the team before this freeze (`results/floquet_patch{27,33}*.json`). Only the NLCE predictions do not exist yet.
- The causal-cone geometry was computed before the freeze (`teams/floquet/results/cone_geometry.json`). It is geometry only: gate supports, no dynamics.
- Max backward-cone size at c = 1/2/3/4, n = 27: 7 / 16 / 25 / 27. For n = 33: 7 / 17 / 29 / 33.
- No BlueQubit job is planned. So there is no ledger entry and no token read. All compute is local, below 1 GB per process, under `nice -n 10`.

## Targets (fixed)
- Observable: `mag` = mean over patch sites of ⟨Z_i⟩. Patches are `floquet_patch_oracle.patch(n)` for n ∈ {27, 33}.
- Cycles c ∈ {1, 2, 4, 8, 13, 16, 20, 27}. That gives 16 points.
- Truth is the `exact` field (BlueQubit statevector) in the existing JSONs:
  - `floquet_patch27.json` and `floquet_patch33.json` for c ≤ 16;
  - the `*_27cyc.json` files for c = 20 and 27.

## Method (fixed)
**Cluster family.** All connected induced subgraphs of the patch graph, with ≤ K sites. Each cluster keeps the tracker's three RZZ edge layers restricted to the cluster, exactly as `floquet_patch_oracle.patch` restricts them.

**Gate content.** Identical to `floquet_patch_oracle.build`. Each cycle consists of 3 layers. Each layer applies, in order:
1. RX(θx/3) on every site;
2. RZ(θz/3) on every site;
3. RZZ(π/3) on that layer's edges.

The parameters are θx = 1.56567 and θz = 0.33879. The initial state is |0…0⟩.

**Enumeration.** ESU-style: each connected set is visited exactly once.

**Simulation.** Exact local numpy statevector for each cluster. This gives P(c, t) = Σ_{i∈c} ⟨Z_i(t)⟩ for t = 1..30.

**Weights.** W(c) = P(c) − Σ_{s ⊊ c, s connected induced} W(s).

**Estimator.**
- Order-K estimate: S_K = (1/n) Σ_{|c|≤K} W(c).
- **Primary estimator: the raw site-based sum at K = 16.** Orders 1..15 are reported as a descriptive series.
- Resummations (Wynn/Euler) may be reported ONLY as descriptive values. They can never rescue a failed gate.

**Baseline (placebo).** The exact mean ⟨Z⟩ of the 16-site BFS ball `patch(16)`, simulated with the same code. This is bare-cluster exact diagonalization at the same maximum cluster size.

**Convergence diagnostic.** δ_K = |S_16 − S_15|.

## Primary test (decides feasibility)
Error metric: e(n, c) = |S_16(n, c) − exact(n, c)|.

**PASS (the route is worth attempting at larger n)** requires BOTH of the following:
- (i) e ≤ 0.02 at all 6 late points: c ∈ {16, 20, 27}, n ∈ {27, 33}. This is the §5 oracle gate of `research/20260925-floquet-decision-path.md`.
- (ii) Over those 6 points, the NLCE mean |error| is strictly smaller than the baseline mean |error|.

**Otherwise FAIL.** Points at c ≤ 2 are expected to pass by construction (the cone fits inside 16–17 sites), so they carry no weight.

## Secondary (descriptive, pre-specified)
1. **Tracking horizon C\*(n):** the largest target cycle c such that e ≤ 0.02 at every target cycle ≤ c.
2. **Fraction within 0.02:** the fraction of the 16 points with e ≤ 0.02, and whether it is ≥ 90%.
3. **Diagnostic calibration:** the number of "false-confidence" points, where δ_16 ≤ 0.01 but e > 0.02, out of the 16 points. At 51 qubits δ is the only error signal available, so a diagnostic with any false-confidence point at c ≥ 4 is declared NOT CALIBRATED.
4. The baseline error at every point.

**Stated in advance.** The cone argument predicts that exactness is lost from c ≈ 3, and that no guarantee exists at c ≥ 4. Late-time agreement, if any, would have to come from relaxation (1711.01284). It would not come from causality.

## What each outcome licenses for 51q×30c
- **FAIL:** "the NLCE route closes at cluster order ≤ 16 for this circuit family; tracks exact to cycle C\*." No statement about the 51q×30c value.
- **PASS with a calibrated diagnostic:** "worth attempting on the 51q graph at order 16, reported with δ as its error signal." Even then, the result does NOT give a decided 51q×30c value: 30 cycles lies outside the validated depth of 27.
- **PASS with an uncalibrated diagnostic:** "agreement on patches, but no trustworthy error signal at 51q"; not usable.

## Instrument controls (must pass before scoring; if any fails, report an instrument failure and do NOT score)
- **C1 — same constructor.** For 5 clusters, including one containing the loop, the numpy simulator must match qiskit `Statevector` on `floquet_patch_oracle.build(...)` circuits. Tolerance: ⟨Z_i⟩ to 1e-8, at cycles 1, 2, 5.
- **C2 — full-order identity.** On a connected ≤ 14-site subgraph of the 33q patch that contains a loop, NLCE at K = N must equal the direct statevector to 1e-9 at all t.
- **C3 — independent convention check.** Reproduce `results/floquet_oracle19.json` exact `mag`, using that script's own lattice and colouring (imported read-only), to 1e-6 at all its cycles.
- **C4 — enumeration.** ESU counts must equal brute-force counts over all subsets, on a ≤ 14-site subgraph with a loop.

## Missing-point and retry rules
- A cluster simulation that raises an error or returns a non-finite value is retried once.
- If it fails again, every order ≥ that cluster's size is marked missing. The primary test is then evaluated at the highest complete order K′ < 16, labelled as such.
- A target point with no exact value is reported as missing and counts as a failure for (i).
- If `MemAvailable` < 20 GiB: pause with backoff (60, 120, 240 … s, capped at 30 min). This is not a failure.
- No other orders, cluster families or estimators will be tried to rescue the test.
