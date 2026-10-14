# Pilot 2 — ordering-invention calibration: INCONCLUSIVE (instrument), no agent run

**Status (2026-09-23):** stopped at calibration. No pre-registration was frozen and no agent ran, so there is no
verdict. Stopping rather than searching for a lattice/χ/observable that shows headroom (that would be forking paths).

**What was measured** (`calibration.json`, `calibrate.py`, all BlueQubit `mps.cpu`, exact from local statevector):
19-qubit heavy-hex (dev) and 4×5 square lattice (held-out test), Floquet mixed-field Ising at the tracker parameters,
4 instances each (cycles 6, 12 × magnetization, ZZ_{d=2}), χ ∈ {4, 8, 16}; orderings: native, RCM, spectral (Fiedler),
cutwidth simulated annealing (4 seeds), random (6 seeds). Relabelling invariance of the exact value asserted.

**Finding (narrow):** ordering matters (random/native vs best: ~0.1–0.4 log10 in MPS error), but the best textbook
orderings — spectral and cutwidth annealing — land within 0.01–0.05 log10 of each other on both lattices at every χ
tested. So there is **no evidence of headroom above textbook orderings at exactly verifiable sizes**, and a test of
"agent-invented ordering beats best textbook ordering" cannot discriminate here.

**Limits of this finding:** the 4 annealing seeds all start from the spectral ordering (near-copies, not an
independent sample of cutwidth-optimal orderings); only 4 instances at one parameter point. It does NOT show that
all cutwidth-optimal orderings are equivalent, nor anything about larger lattices.

**Also noted:** on the 4×5 square lattice RCM (cutwidth 7) is worse than row-major native order (cutwidth 6).

**Consequence for the proposal:** qubit ordering is not where agent invention can be shown at verifiable sizes; the
grant targets a richer strategy space (method hybrids, truncation schedules) where only cross-method / near-Clifford
checks exist. Sandbox note: agent code would run via `cohezion.compound.sandboxed_exec.run_untrusted`; in this agent
shell isolation is the rlimit layer only (bwrap namespaces unavailable) — allowed imports: math, itertools,
collections, functools, statistics, numpy.
