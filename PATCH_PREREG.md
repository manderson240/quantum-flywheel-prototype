# Pre-registration — intermediate-size bracket check (frozen before any patch data, 2026-09-24)
Hypothesis (from the 19-qubit oracle, report §5): at the tracker's Floquet parameters, truncated Pauli-path (delta=1e-4)
is at or below the exact value and truncated MPS (chi=64) at or above it, for mag / zzd2 / zzd3.
Test: patches of the tracker's own 51-qubit lattice, n in {27, 33} (BFS ball about the minimum-eccentricity qubit, the
tracker's own edge layers), cycles {1, 2, 4, 8, 13, 16}; truth = BlueQubit statevector (device=cpu).
Counting rule (as at 19q): a point is "in bracket" if pp_1e-4 - 0.005 <= exact <= mps_64 + 0.005; "two-sided" if
pp_1e-4 > 0.005. Report counts in / total, and two-sided in / two-sided total, per n, whichever way they fall.
Supported if >= 95% of points are in bracket at each n; falsified otherwise. Also reported (descriptive, not tested):
MPS excess over exact at chi 64 vs 256 (the tightening rate).
No re-running with other parameters to rescue the hypothesis.
