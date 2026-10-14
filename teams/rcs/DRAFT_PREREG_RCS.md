# DRAFT: NOT FROZEN, NOT HASHED. Pre-registration of a finite-fidelity MPS sampling test of arXiv:2609.28657 (drafted 2026-09-25)

> Status: **DRAFT for review.** Nothing in this file is binding until the core block (§A) is copied to
> `RCS_PREREG.md`, frozen and hashed the way PATCH_PREREG.md was. No simulation has been run, and no
> counts or samples have been opened. Private, and not to be posted. The disclosure of what was examined
> before drafting is in §D.

## A. Core block (the part to be frozen; PATCH_PREREG style)

Claim under test: arXiv:2609.28657 (BlueQubit; IBM Nighthawk r2, 61 q, 36 cycles, 918 CZ). The quoted
fidelity is F(36) = 2.3e-3, from the mirror fit 0.326*0.872^d. The paper leaves finite-fidelity MPS/DMRG
explicitly unpriced (Sec. III(iv)).

Data: github.com/BlueQubitDev/rcs-nighthawk, pinned to commit b9dd86b016743465ebc97fb9f6677f4a251a3baa.
Before any use, the SHA-256 of every circuit file is checked at run time against
`data/circuits/manifest.json`. A mismatch aborts the run.

Circuits:
- Target: `data/circuits/full/d40_logical.qpy`, instance 0. Its gate list has `d04`…`d36_logical`
  as exact prefixes; d08 ⊂ d36 ⊂ d40 was checked on the qasm. The cycle-36 state is the sampled
  circuit `full/d36_logical`.
- Calibration C1 (released): `data/circuits/patched/K3/d{20,24,28,32,36,40}/partition{0..4}_instance0.qpy`
  and `…/K4/…`. These are the target circuit with the cut couplers removed, so each is an independent
  set of 15–21-qubit patches.
- Calibration C2 (OUR construction, not released): row bands of `d40_logical`, namely device rows 1–3
  and 6–8 (23 q, full 8-column width). CZs that touch qubits outside the band are dropped.

Method:
- Qubit-level MPS, ordered row-major. This is the identity on logical indices; logical order was checked
  to equal row-major.
- Every CZ is applied as a bond-2 MPO over its span, with the MPS mixed-canonical at the active bond.
  Each bond is SVD-truncated to at most χ kept values, with no relative cutoff. Arithmetic is complex64.
- χ ladder, full target: {64, 128, 256, 512, 1024}. Calibration ladders: C1 {4, 8, 16, 32, 64, 128};
  C2 {8, 16, 32, 64, 128, 256}. All rungs are run and reported.
- χ = 2048 is run locally only if the measured peak RSS at χ = 1024 is ≤ 0.95 GB.
- Column-major ordering is run on C1/C2 only, and is descriptive.
- No other ordering, algorithm or gate fusion will be tried to rescue a result.

Fidelity estimator: F̃(d) = ∏ over truncations of (1 − w_k), where w_k is the discarded weight
(Zhou et al. Eq. 17 form).
- On C1/C2 the exact fidelity F = |<ψ_exact|ψ_MPS>|² is computed by local statevector.
- F_B, the linear XEB of the MPS distribution against the exact one, is computed exactly by summing
  over the full distribution, not from samples.

Hypotheses and counting rules:
- **H-est (instrument):** |log10(F̃/F)| ≤ 0.3 at ≥ 95% of C1+C2 points with F ≥ 1000/2^n **and**
  F̃ < 0.99 (points where truncation actually ran; trivially exact points do not count).
  The validated range is therefore F ≳ 1000/2^n, about 5e-4 (21 q) to 1e-4 (23 q). A full-size F̃
  below that range is reported as **estimator extrapolation**, not as a calibrated value.
  - If H-est fails, the full-size F̃ is reported as uncalibrated and cannot satisfy S-T2.
  - If F̃/F > 1 at any calibration point, the full-size F̃ is divided by the worst observed ratio
    before any comparison.
- **S-T2 (primary):** corrected F̃(36) ≥ 2.3e-3 at any χ in the ladder, within budget.
- **S-T1 (secondary, conditional):** corrected F̃(36) ≥ (2.3e-3)² = 5.3e-6, **and**
  |log10(F_B/√F)| ≤ 0.3 at ≥ 80% of the C1+C2 points counted for H-est. The S-T1 bar lies below the
  validated range, so S-T1 is uncalibrated by construction and can only ever be a prediction.
- Otherwise, report:
  - the gap Δ = log10(2.3e-3 / F̃_max(36)) in decades;
  - the crossing depth d*, the largest cycle d ∈ {1, …, 36} with F̃(d) ≥ 0.326·0.872^d (the d40 prefix
    gives F̃ at every cycle; the fit is the paper's, used here only as a reference curve);
  - the saturated per-event error ε̂ (median of w_k over bonds whose cumulative crossings exceed log2 χ);
  - the χ needed to close the gap, marked **extrapolated**.

Budget:
- Local: ≤ 48 h wall per run, ≤ 16 cores, < 4 GB RSS per process.
- BlueQubit mps.cpu (free / fair-use): vendor arm only.
- BlueQubit mps.gpu: $0 committed. It is spent (≤ $25) only if gate G passes.

Stage 0 control (must pass before any MPS number counts):
- Using our own code, reproduce `data/results/patch_xeb.json` for K3/d36/instance0, partitions 0–4, from
  the released counts. Each partition's `fidelity` must match within 1e-6 relative; for example,
  partition 0 is 1.6349e-3.
- In addition, the MPS at χ = 2^⌈n/2⌉ must give F = 1 ± 1e-5 on every C1 patch.

Missing points and retries:
- A local OOM or a run over 48 h is a missing point. At most one identical rerun is allowed, and only
  for a documented infrastructure fault.
- BlueQubit server-terminated or time-capped jobs get at most 2 identical retries, then are reported as
  missing. A cap is never a reason to change χ.
- No futility stop. Every run continues to cycle 40 (snapshot at 36) unless it hits the 48 h wall.
  log F̃ is accumulated in float64 so it cannot underflow.
- Sampling seed 20260925. 10^6 samples are drawn from the best-χ cycle-36 MPS whatever the outcome
  (artifact only).

Vendor arm (descriptive only; cannot satisfy S-T1 or S-T2):
- Run BlueQubit mps.cpu at χ ∈ {256, 1024, 2048} on (i) the K3/d36 patched 61-q circuits, scored with
  the paper's own patched estimator against exact patch distributions, and (ii) `d36_logical`, which
  gives samples only.
- The backend exposes no truncation diagnostic that we know of, so its full-size fidelity is not
  estimated.

Gate G (GPU):
- Spend on mps.gpu χ = 4000 only if all three hold: (a) the backend exposes a truncation or fidelity
  diagnostic, checked on a trivial job; (b) the local corrected F̃(36) at the top rung is ≥ 5.3e-7
  (within one decade of the S-T1 bar); (c) H-est passed. Without (a) the gate stays closed whatever the
  numbers say, because a run whose fidelity cannot be estimated cannot satisfy any criterion.
- Expected: not triggered (§F).

Allowed wording (fixed in advance):
- If S-T2 holds, **and** a second implementation or independent non-author reviewer reproduces F̃
  within 0.3 decades, we may say: *"for this released instance, the 110-Frontier-year figure does not
  bound the finite-fidelity MPS class, which reaches estimated fidelity ≥ 2.3e-3 at cost X"*. We may use
  "refutes" only for that cost figure, against that class, for that instance. We will not say
  "refutes quantum advantage": 19 s on the QPU versus hours is still a time-to-solution gap.
- If S-T1 holds: *"predicted (not measured) XEB ≈ 2.3e-3 if the F_B ≈ √F relation transfers"*. We never
  say "refuted" on T1.
- Otherwise: *"the claim survives this method class by Δ decades at χ ≤ χ_max"*.
- We never write "the paper is wrong", and we never extrapolate past χ_max as if it were a measurement.

Published whichever way it falls, with all rungs, missing points and calibration tables.
COI: BlueQubit is the program's funder, and the vendor arm runs on its simulator. BlueQubit staff have
no editorial role, and no pre-approval of outcomes is sought.

## B. Why the criterion is T2 and not "XEB ≥ 2.3e-3"

- **The obvious criterion cannot be measured at full size.** "A classical sampler reaching XEB ≥ 2.3e-3
  on the full circuit" needs ideal amplitudes of the 61-q/36-cycle circuit. The paper quotes about
  1e22 operations per amplitude, and says the full-circuit XEB is never measured, not even for the
  device.
- **So the primary target is T2.** It asks for an estimated state overlap F̃ ≥ 2.3e-3, which is
  stronger than a score match.
- **The two sides use different definitions.** F̃ is a state overlap. The device's 2.3e-3 is a fitted
  proxy built from the mirror fit, with measured anchors at 36 cycles:
  - mirror 2.2e-3
  - 3-patch 1.8e-3
  - 4-patch 2.0e-3

  Comparing them is a deliberate, pre-stated choice. The threshold is fixed at 2.3e-3. The lowest
  measured anchor (1.8e-3, 3-patch) is reported next to it, as descriptive only. If F̃ falls between
  1.8e-3 and 2.3e-3, that is reported, and S-T2 is still not met.
- **XEB would overstate the MPS fidelity.** Ayral et al. (arXiv:2207.05612, Eqs. 14/35) found
  F_B ≈ √F for their DMRG outputs, with numerical evidence up to N = 36 (Fig. 10). An MPS sampler's XEB
  can therefore sit far above its true fidelity. That is why T1 is only a conditional, **predicted**
  quantity here, and why F_B is measured exactly on calibration circuits rather than assumed.

## C. Method choices and their sources (each verified 2026-09-25 against arXiv full text)

**Zhou, Stoudenmire, Waintal, arXiv:2002.07730**
- The abstract's own wording: for a 2D 54-q array with Control-Z gates, error rates better than devices
  of the time were obtained on a laptop within hours. "For more complex gates such as a swap gate
  followed by a controlled rotation, the error rate increases by a factor three for similar computing
  time."
- In the body that gate is iSθ (Eq. 36: iSWAP followed by a controlled z-rotation, θ = 1). Pure iSWAP
  is noted there as trivial to simulate, so we do not call it "iSWAP".
- The ×3 compares group-MPS for CZ with Split-and-Merge for iSθ. It is not a same-algorithm
  comparison.
- The 2D CZ reference point (Fig. 12, D = 20): ε_av ≤ 1.4% (F ≈ 0.002) at χ = 320 with the [4,2,2,4]
  column grouping, on one core in < 48 h, using 4.5 GB of memory. That footprint already exceeds our 4 GB
  per-process cap.
- The body (Sec. VI) also notes that handling 2D arrays by SWAP insertion is inefficient: the effective
  per-gate fidelity drops as the transverse dimension of the array grows.
- The same paper gives F ≈ ∏ f_n, checked against the direct F at N = 20 (Eq. 17, Fig. 6). We use that
  estimator, not Ayral's.

**Ayral, Louvet, Zhou, Lambert, Stoudenmire, Waintal, arXiv:2207.05612**
- Product fidelity F̃ matches exact F for N ≤ 36, with F̃ ≤ F, within a few percent. This was shown for
  their **DMRG** algorithm.
- We do **not** assume that conservativity transfers to our apply-and-truncate method. The H-est rule
  measures the direction of the error instead.

**Why qubit-level, row-major**
- Grouped MPS with one 8-qubit row per site needs dense two-row updates, (256χ)² per theta.
  Zhou-style group tensors for an 8-wide lattice do not fit in 4 GB.
- The row-major and column-major cut profiles are near-identical (static count: maximum crossings
  81/81, total bond crossings about 3,980). The identity ordering avoids relabelling errors.

**Released-data leverage**
- C1 patches share the single-qubit gates of the target exactly: the 6,588 rz/rx lines are identical,
  and K3/d36 partition 0 drops 108 of 918 CZ.
- The device's per-patch fidelities at d36 (0.08–0.16 for 20–21-q patches, from `patch_xeb.json`) give
  a descriptive comparison: the χ at which the MPS matches the device on the same released patch.

## D. What was examined before drafting (disclosure)

**Read:**
- the scoping report
- the repo tree (GitHub API; commit b9dd86b0 still HEAD on 2026-09-25)
- `README`, `data/README`, `manifest.json`, `layout.json`, `fidelity_vs_depth.json`, `patch_xeb.json`
- `rcs/circuits.py` (seeding)
- `scripts/build_circuits.py` (full = instance 0)
- `d08/d36/d40_logical.qasm`, and one patched qasm (K3/d36/partition0_instance0)

**Computed (static only):** CZ bond-crossing counts per ordering, the prefix check, and the feasibility
counts in §F.

**Not done:** no simulation, no job, and no opening of `counts/*.npz` or `samples/full_d36.npz`.

## E. Open items before freezing

- Confirm that BlueQubit mps.cpu pricing is $0 on our plan. The 2026-09-24 estimate showed $0.10/h,
  still unresolved (research/20260924-bluequbit-pricing-engine.md). Any non-zero charge counts against
  the $25.
- The free tier caps jobs at 15 min. Whether `force_run` applies on the free tier is unknown.
- The C2 band choice (rows 1–3 and 6–8) and the 0.3-decade tolerances are judgment calls. They should
  be reviewed before freezing.
- The Stage-0 tolerance of 1e-6 relative assumes our statevector matches Qiskit's convention for
  RZ·RX·RZ ordering and bit order (bit q = logical q). If not, the control catches it.
- Correction needed elsewhere: scoping §6 draft text says "iSWAP-family gates". It should say "a swap
  gate followed by a controlled rotation (iSθ)", per Zhou's abstract.

## F. Feasibility note: can χ ≤ 2048 (BlueQubit free MPS.CPU) reach meaningful fidelity at 61 q × 36?

**Short answer: not for T2. The expected shortfall is several decades. The T1-via-√F path is borderline
only under the most optimistic per-event error.**

**Model (stated assumptions; a bracket, not a measurement)**
- In row-major qubit order, every CZ adds at most 1 ebit to each bond it spans. Summed over the circuit,
  that is 3,978 bond-crossing events.
- A crossing is lossy once the bond's cumulative crossings exceed log2 χ, and only if the bond's maximum
  entanglement min(k, 61−k) exceeds log2 χ. That gives about 2,520 lossy events at χ = 1024 and about
  2,350 at χ = 2048.
- The model cannot distinguish χ = 2048 from 4000, since in both cases a bond saturates after 12 crossings.
- The dominant assumption is the per-lossy-event error ε. Zhou et al. (Sec. III.C, Fig. 5 discussion) find that in the
  chaotic stationary regime of 1D CZ circuits the error per gate saturates at ε_∞ ≈ 1e-2. Going below ε_∞ costs exponential effort, and χ helps only logarithmically there.
  Transferring that 1D per-gate value to a per-bond-event value on our row-major 2D ordering is an **assumption**.
- The GTE worst case for CZ is 1 − f_GTE = 3.8%.

**Required error rates.** To reach T2 at χ = 2048 we need ε ≤ 2.6e-3 per event. The T1 bar
(F ≥ 5.3e-6) needs ε ≤ 5.2e-3.

**Predicted outcomes by assumed ε**

| assumed ε per lossy event | F̃(36), χ=1024 | F̃(36), χ=2048 | T2 gap (decades, χ=2048) | predicted d* |
|---|---|---|---|---|
| 0.5 % (optimistic) | 3e-6 | 8e-6 | 2.5 | ≈ 14 |
| 1 % (Zhou 1D ε_∞) | 1e-11 | 7e-11 | 7.5 | 7–10 |
| 2 % | 1e-22 | 4e-21 | 18 | ≈ 7 |

**Prediction, stated before any run**
- F̃(36) at χ ≤ 2048 lies in [1e-22, 1e-5], with a central value near 1e-11.
- Δ_T2 is between 2.5 and 18 decades (central about 7.5).
- d* ≈ 7–14 cycles (every-cycle definition, χ = 1024–2048).
- Values of F̃ this small lie below the calibrated range (§A, H-est), so they will be reported as
  estimator extrapolation. The measured quantities that carry the result are ε̂, d* and the calibration
  tables.
- The mechanism: in the saturated regime the MPS loses roughly 0.8 nats per cycle (about 80 lossy events
  per saturated cycle × ε ≈ 1%). The device loses 0.137 nats per cycle (its fit). So once saturation begins, the
  classical sampler falls behind within a few cycles.

**What would falsify the prediction:**
- a measured saturated ε̂ < 2.6e-3 on C2 (full-width) bands, or
- F̃(36) ≥ 1e-5.

**Practical limits on BlueQubit's free tier**
- The internal algorithm is undocumented. It may be swap-routed, which by Zhou's statement degrades
  with transverse width. There is no known truncation diagnostic, so even a completed χ = 2048 run gives
  samples whose fidelity we cannot estimate.
- There is a 15-min job cap. The gate count (918 CZ) is within the 10,000 two-qubit-gate limit.

**Local compute (estimates)**
- The whole ladder is local and $0.
- Memory: χ = 1024 needs about 0.7 GB of tensors in complex64. χ = 2048 needs about 2.6 GB of tensors
  plus SVD workspace (about 3.3 GB), which is borderline under the 4 GB cap and hence the RSS rule.
- Time: about 4,000 truncating SVDs of size 2χ × 2χ. That is roughly hours at χ = 1024 and about
  10–20 h at χ = 2048. Unmeasured.

**Bottom line**
- The free tier and the local box can deliver a calibrated, publishable measurement of the gap and d*.
- A T2 success would contradict both Zhou's saturation result and our model. It is not impossible, but
  it is not what we expect, and gate G will almost certainly keep the $25 unspent.
- Only a grouped/DMRG method, which is out of scope under the 4 GB cap, could plausibly contest T1. If
  pursued, it needs its own pre-registration.
