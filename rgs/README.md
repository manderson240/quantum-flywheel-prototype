# RGS target — IBM/UChicago undoped random graph-state sampling (70q × depth 70)

Status 2026-09-24. Nothing posted anywhere.

## Verified
- The target (`tracker/cv/random_graph_sampling_..._basis_fstate.qasm`) has the identical ordered 2,415-CZ sequence as
  the doped circuit that Manabe, Gu & Pan contracted (arXiv:2608.13110; Zenodo 10.5281/zenodo.21912448, CC-BY-4.0,
  checksums OK). All 140 non-Clifford gates come after each qubit's last CZ.
- IBM's 1,726 post-selected samples (tracker issue #151 attachment, `data/rgs/samples_undoped.npy.zip`, 27.6 KB) are
  70-char strings in Qiskit little-endian order (rightmost char = q0). Criterion: classical XEB on these samples
  significantly above 0.092, or classical sampling with XEB ≳ 0.37.
- We reproduce Manabe et al.'s log-XEB (0.350338 vs published 0.3503365, same SE) from their released amplitudes. This
  checks our bitstring convention and estimator.
- `mini_validate.py`: quimb from-QASM amplitudes match an exact statevector (≤4e-11) on 12- and 16-qubit slices.
- `sweep.py` (our reimplementation of the spatial / temporal-boundary sweep): matches the exact statevector to ~1e-15
  on five slices (k ≤ 12 qubits) of IBM's circuit (`mini_sweep_validate.py`). It is not the authors' code.

## Cost
- Published schedule: ~280 GPU-s per amplitude batch (2,051 batches in 37.3 min on 256 H100s), so 1,726 samples
  ≈ 134 H100-h. That is ≈ 16.8 node-hours of p5.48xlarge: ≈ $920 on-demand at $55.04/h, ≈ $630–700 on Capacity Blocks at
  $37.76–41.53/h. These prices come from third-party trackers in 2026-09; confirm in the AWS console, where p5 also needs a quota
  request.
- Our sweep peaks at rank 37 (1 TiB complex64) against their 35 (256 GiB). The single-qubit gates between every CZ block
  the commuting reorder, so as written it costs up to ~4× more. Porting their compiled width-35 program means
  reverse-engineering how they absorb gates into the 4,760 rank-3 tensors; their builder code is not released, only verify.py.

## Honest framing
- Runtime: IBM's undoped quantum run took 1,950 s. The published classical cost is ~37 min on 256 H100s, i.e. roughly
  parity, not a decisive break.
- Method: an independent classical entry using a published method, not a new method.

## Runbook — score IBM's 1,726 undoped samples on one NVIDIA H100 (80 GB)  [prepared 2026-09-24; not yet run]
Estimated cost: ≈ 1 GPU-hour extrapolated from a measured CPU inner-loop rate; the first 5 samples are a timing probe.
1. Rent any single 80 GB H100 (e.g. AWS p5 single-GPU capacity, Lambda, RunPod). Mike creates the account and approves spend.
2. Copy this project, then:
   ```bash
   pip install numpy qiskit cupy-cuda12x
   python rgs/score_undoped_gpu.py --validate                  # must print max rel err < 1e-9 (CPU, seconds)
   python rgs/score_undoped_gpu.py --backend cupy --limit 5    # timing probe: prints seconds per sample
   python rgs/score_undoped_gpu.py --backend cupy              # all 1,726 (resumable JSONL in results/)
   ```
3. Stop rule: if the probe exceeds 20 s per sample (≈ 10 h total), stop and re-cost before continuing.
4. Output: `results/rgs_undoped_amplitudes.jsonl` plus a printed linear and log XEB with standard error. Criterion (#151):
   XEB on IBM's samples significantly above 0.092. Report whichever way it falls. Nothing gets posted to the tracker before acceptance.
5. Precision: use complex128. complex64 gave 4e-7 relative error at 16 q, and at 70 q it is unverified.
Validated locally: the chunked scorer equals the reference implementation exactly on 9–14-qubit slices (both chunk paths),
and the full plan peaks at 2^31 (message 32 GiB in complex128; peak ≈ 64 GiB with old and new messages).
