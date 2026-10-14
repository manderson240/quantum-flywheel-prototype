# PREREG — rcs wave 2: independent reproduction of the released d36 patch-XEB numbers

Frozen before any XEB value, ideal probability, or collision ratio was computed by this team. The only computation
before freezing is `precheck.py` (structural, no simulation): see `results/precheck.json`.
Source: arXiv:2609.28657 release, repo pinned at commit b9dd86b0; local copy `refs/rcs-nighthawk-data/` (93 files).

## 1. Scope (what this does and does not test)
- Tests: that the released d36 patch-XEB numbers follow from the released d36 counts and patched circuits under the
  estimator the authors describe. It is a re-analysis of released data.
- Does NOT test: the other five depths (20–32, 40), the mirror estimator, hardware provenance of the counts,
  the exponential fit, or classical hardness. No statement about those may be drawn from this result.

## 2. Pre-freeze structural facts (precheck.py, no simulation)
- All 38 files used (15+15 patched .qasm, 2 npz, layout.json, patch_xeb.json, 4 source files) + meta full d36 qasm
  + meta fidelity_vs_depth.json match their git blob SHA-1 at b9dd86b0 (computed as sha1("blob <len>\0"+bytes)).
- For all 30 circuits: the CZs absent relative to full d36 are exactly the partition's boundary edges × 9 uses;
  0 surviving CZ crosses a patch; the layout boundary equals the true cut; measurement is c[i]=q[i]; each
  patch_qubits list is ascending. Counts: 30 arrays, uint64, 36,000 shots each, all values < 2^61.

## 3. Estimator (copied in formula form from rcs/estimators.py `patched_xeb`, read not executed)
- Bitstring convention (rcs/io.py): shot integer x = Σ_q bit_q 2^q over logical qubits q.
- ASSUMED, not read from source (`rcs/circuits.py::split_patched_circuit` is not in the 93 files): within patch r,
  sub-circuit qubit j = `patch_qubits[r][j]` (list order, ascending), and ideal-probability index bit j = outcome of
  sub-circuit qubit j (Qiskit little-endian). Sub-bitstring x_r has bit j = bit patch_qubits[r][j] of x.
  Falsifier: a wrong order drives patch fidelities to ≈ 0 (see control N2); a match confirms it.
- p_r = |ψ_r|² by exact double-precision statevector of patch r's gates (rz(θ)=exp(−iθZ/2), rx(θ)=exp(−iθX/2),
  cz = diag(1,1,1,−1)), my own numpy implementation, no Qiskit in the primary path.
- I_r = 2^{n_r} Σ_x p_r(x)² − 1 ("patch_ideal_xeb"). Per shot s_r = (2^{n_r} p_r(x_r) − 1)/I_r.
- patch_fidelity F_r = mean over shots of s_r. Circuit fidelity F = Π_r F_r.
- se: second-order delta method on the product, cov = np.cov(scores, bias=True)/n_shots (population covariance
  across patches); first = gᵀCg with g_i = Π_{k≠i} F_k; second = ½ tr((CH)²), H_ij = Π_{k≠i,j} F_k (i≠j), H_ii = 0.
- Pooled d36 point per K: inverse-variance weighted mean over the 15 circuits (5 partitions × 3 instances),
  se = sqrt(1/Σw), w = 1/se² (from analysis/fidelity_vs_depth.py).

## 4. Targets (32 primary comparison units)
- U1–U30: each d36 record in data/results/patch_xeb.json (K∈{3,4}, partition 0–4, instance 0–2). A unit is compared
  on `fidelity`; its `se`, every `patch_fidelity` and every `patch_ideal_xeb` are compared as sub-results under the
  SAME tiers (lesson A3) and reported, but the unit verdict is set by the worst tier among all its fields.
- U31, U32: pooled 3-patch and 4-patch d36 points in refs/rcs-nighthawk-meta/data/results/fidelity_vs_depth.json
  (released: 3-patch 1.8390523976486782e-3 ± 4.0850529700543075e-5; 4-patch 1.999385896123157e-3 ±
  3.216069760032846e-5). Each compared on fidelity and se. Also reported: my pooled value recomputed from the
  RELEASED 15 records (tests the pooling rule alone).

## 5. Tolerance tiers and verdict rule (fixed now)
- Relative error ρ = |mine − released| / |released| (for patch_ideal_xeb, on I_r itself).
- EXACT: ρ ≤ 1e-6. NUMERICAL: 1e-6 < ρ ≤ 1e-3. DISCREPANT: ρ > 1e-3.
  Additionally reported for every fidelity: |Δ| / released se (for context only; it does not change the tier).
- Verdict: REPRODUCED iff 32/32 units are EXACT. REPRODUCED-NUMERICAL iff all 32 are EXACT or NUMERICAL and ≥1 is
  NUMERICAL. PARTIAL (k/32 EXACT, m/32 DISCREPANT) otherwise. NOT REPRODUCED iff ≥ 16/32 DISCREPANT.
- Every DISCREPANT unit is reported with released value, mine, ρ, |Δ|/se, and the most likely cause; it is not tuned away.

## 6. Controls (expected bands fixed now)
- P1 (simulator, diagnostic): a 10-qubit test block = the gates of K4 partition 0 instance 0 acting only on the
  first 10 qubits of its patch "0" (CZs leaving the block dropped). My statevector vs (a) a dense unitary built by
  np.kron gate by gate and (b) qiskit.quantum_info.Statevector built from gate CALLS (never its QASM loader):
  max |Δp| ≤ 1e-12 each. Diagnostic only; failure = instrument bug, stop and report.
- N1 (mapping, negative): K3 partition 0 — counts of instance i scored against circuits of instance (i+1) mod 3.
  Expected |F| ≤ 5 × its own se for each of the 3 pairings.
- N2 (bit order, negative): K3 partition 0 instance 0 with the within-patch bit order reversed. Expected |F| ≤ 5 se.
- Note: patch_ideal_xeb is invariant under bit permutation; it validates the simulator, not the mapping.

## 7. Missing / retry / resource rules
- Before each heavy step (each circuit's simulation), check MemAvailable. If < 20 GiB: wait with backoff
  60, 120, 240, 480, 600, 600 … s, cap 60 min total per step. After the cap the unit is DEFERRED (counted missing,
  not EXACT); the floor is never lowered. Process RSS guard 0.9 GB (abort → missing). `nice -n 10`.
- A unit that raises (parse error, RSS abort) may be retried once unchanged; a second failure = missing. Missing
  units count against REPRODUCED (32/32 needed).
- No input substitution: if a file had failed integrity it would be missing (none did).
- Post-hoc rule: any rerun with changed conventions (bit order, gate sign, normalisation) after results are seen is
  labelled POST-HOC DIAGNOSTIC in the outputs and cannot change the verdict.
- No BlueQubit jobs, no downloads, no posting; npz via np.load(allow_pickle=False) only; nothing is unpickled.
