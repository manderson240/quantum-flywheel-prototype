# Pre-registration amendment L1: local-CPU subset scoring of IBM's undoped RGS samples (frozen 2026-10-09, before any timing probe)

This amendment makes rgs/PREREG_UNDOPED_XEB.md (PARKED 2026-09-28) runnable on the local machine at $0, approved by Mike on 2026-10-09 ("probe first"). The parent's sections §1–§4 and §6 apply unchanged except where amended here. Nothing is posted anywhere. Nothing reaches the tracker without Mike's explicit decision.

## A. Hardware and arithmetic (replaces parent §5 hardware)
- **Machine:** the shared local AMD box (32 threads, ~122 GB). Code: numpy, rgs/score_undoped_gpu.py with the annealed order, `--dtype complex64`. The chunk loop may be parallelised over threads or processes, but the arithmetic per entry must stay unchanged.
- **Why complex64:** complex128 at 2^31 entries needs 64 GiB and does not fit beside the other workloads. Two checks cover the precision risk:
  - **P1:** run `--validate` with complex64 on the slices. Max relative error must be ≤ 1e-5.
  - **P2:** compute the amplitude of the first subset sample in two different qubit orders, the annealed order and a second order with peak cut-rank ≤ 31 found by a deterministic greedy over cut-ranks. Both use complex64 and must agree to ≤ 1e-4 relative.
- **Memory guard:** inside the script, abort if MemAvailable < 52 GiB at start, or < 16 GiB at any check during the run.

## B. Subset (amends parent §3, "all 1,726 samples are scored")
- `numpy.random.default_rng(20261009).permutation(1726)` fixes the order. Samples are scored in that order, so any prefix is a uniformly random subset.
- **M_final** is the number scored before the cutoff in §C(c). The estimator, SE and verdict keys of parent §3–§4 are applied to those M_final samples.
- Every wording says "a random subset of M_final of IBM's 1,726 samples", replacing "1,726 post-selected samples" as the number scored.

## C. Timeline and stop rules (fixed now)
- **(0) Timing probe, this step, small memory:** measure ns per entry-update for the chunk loop at 2^24–2^27 entries, single-threaded and with 4, 8 and 16 threads. Go only if the projected time per 70-qubit amplitude is ≤ 300 s with the best thread count, using total work 2^33.81 entry-updates for the annealed order. Otherwise stop, with no full run and no text change.
- **(a) By 2026-10-10 22:00Z:** P1 and P2 both pass, or abandon.
- **(b) By 2026-10-11 16:00Z:** at least 100 samples scored, or abandon.
- **(c) Cutoff 2026-10-12 04:00Z:** stop scoring and compute the verdict on M_final. The cutoff is a time, not an outcome.

## D. Inclusion
If (a) and (b) pass, the result goes into the application, whichever verdict key it gets. It goes through a two-family verification round on the result file and the wording (parent §6).
- **Recomputation check (replaces parent §6):** 5 amplitudes chosen with seed 20260928 from the scored subset are recomputed in the second order, and must agree to ≤ 1e-4 relative.
- **Required sentences in every use:** the first sentence of parent §2; "This is a classical check of IBM's samples, not a classical sampler."; and the subset size. The words "classical entry" and "break" are not used.
