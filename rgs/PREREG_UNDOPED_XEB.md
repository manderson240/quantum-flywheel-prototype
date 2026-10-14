# Pre-registration (DRAFT — freeze with sha256 before any GPU run): classical XEB of IBM's undoped RGS samples

Status: PARKED 2026-09-28. Mike directed that compute come from the BlueQubit subscription plus the competition promo code;
BlueQubit runs circuits on its own backends (gpu statevector ≤ 34 qubits) and cannot run this custom 70-qubit amplitude
method, so this run does not fit. Kept for Stage 1 if GPU hours are awarded. Was DRAFT 2026-09-28. Becomes binding when its sha256 prefix is written to rgs/PREREG_UNDOPED_XEB.sha16 and added
to graph/gate.py PREREGS, before the timing probe runs. No result exists yet; nothing is posted anywhere.

## 1. Question
IBM/UChicago report, for the undoped 70-qubit random-graph-state circuit, a post-selected state fidelity of 0.37 from direct
fidelity estimation, "bounded above 0.092 with 95% confidence" (tracker/cv/random_graph_sampling_README.md, Fig. 4). XEB
needs classical output probabilities, which the submission says "can only be extrapolated for the full-depth circuit", so
no XEB of the 1,726 post-selected samples has been reported. We compute the exact output
probability of each sample and report the linear XEB of IBM's own samples.

What this is and is not (tracker #151 thread, 2026-05-13): the task is sampling from |R⟩, and the accepted classical
refutation is classical sampling with XEB ≳ 0.37 (or state fidelity significantly above 0.01). Scoring IBM's samples is
therefore an independent classical VERIFICATION of the device samples, not a refutation attempt. The authors state the
ensemble's second moment is Porter–Thomas-like, so linear XEB is on the fidelity scale; we checked this on truncated slices
of the same circuit (all gates among qubits 0..k−1, exact statevector): ideal linear XEB 2^k Σp² − 1 = 1.025, 0.956, 0.929,
1.023, 0.973 for k = 8, 10, 12, 14, 16. Slices are not the 70-qubit ensemble; this supports, not proves, the normalization.

## 2. Scope (carried into every wording)
- XEB is not state fidelity. The two agree only under weak-noise and anticoncentration assumptions, which have not been
  shown for this ensemble in a product basis. We report XEB and compare it with the fidelity bound; we do not re-estimate
  fidelity.
- One circuit, one sample set (tracker #151 attachment, 1,726 samples). No claim about the hardness of the task or about
  other circuits.
- Method: our graph-state amplitude method (validated to max relative error < 1e-9 against the reference on 9–14-qubit
  slices, rgs/README.md). It is an independent classical entry using a published method, not a new method.

## 3. Estimator (frozen; rgs/score_undoped_gpu.py as of the freeze hash)
- p_i = |⟨x_i|ψ⟩|² in complex128. Linear XEB F = 2^70 · mean(p_i) − 1; SE = 2^70 · sd(p_i) / √M (sample SD, ddof = 1).
- Log XEB is reported as secondary (γ + 70 ln 2 + mean ln p_i) with SE = sd(ln p_i)/√M, with no decision attached.
- All 1,726 samples are scored. A sample that fails (error or non-finite p) is reported and counted; if more than 1% fail,
  the verdict is INCOMPLETE and no verdict key below is used.

## 4. Verdict keys (frozen wording)
z = (F − 0.092) / SE.
- **ABOVE** (z ≥ 3): "Exact classical scoring of IBM's 1,726 post-selected samples gives linear XEB F = <F> ± <SE>, above
  the reported 0.092 fidelity bound."
- **BELOW** (z ≤ −3): "... gives linear XEB F = <F> ± <SE>, below the reported 0.092 fidelity bound; XEB and fidelity need
  not agree (§2), so this is a discrepancy to explain, not a refutation."
- **INCONCLUSIVE** (−3 < z < 3): "... gives linear XEB F = <F> ± <SE>, not distinguishable from 0.092 at 3σ."
Second comparison (reported with every verdict): whether IBM's DFE point estimate 0.37 lies inside F ± 1.96·SE. Frozen
wording: "IBM's direct-fidelity point estimate of 0.37 is <inside / outside> this interval."
Every use carries the first sentence of §2 and the sentence "This is a classical check of IBM's samples, not a classical
sampler."

## 5. Spend and stop rules
- Hardware: one 80 GB H100, rented by Mike on his account; Claude never enters payment or credentials.
- Hard spend cap: $<CAP> total (Mike sets it at approval). Log every hour of rental in results/bq_jobs.jsonl-style
  journal results/gpu_jobs.jsonl.
- Step 1 `--validate` must print max rel err < 1e-9, else stop.
- Step 2 timing probe on the first 5 samples: if > 20 s per sample, or if peak GPU memory > 72 GiB, stop and re-cost
  before scoring the rest (runbook rule).
- Step 3 score all samples (resumable). If the cap would be exceeded, stop; the verdict is INCOMPLETE.

## 6. Verification before any use
Independent verifier round on the result file and the wording, with two verifiers from different model families
(lesson P6), plus a re-computation of 5 sample amplitudes chosen by a seed fixed here (seed = 20260928) with the numpy
backend on the rental host's CPU (not the shared local machine; a 2^32 complex128 message is 64 GiB), which must agree with
the GPU values to 1e-9 relative. Nothing goes to the tracker without Mike's explicit decision.
