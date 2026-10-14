# Pre-registration addendum — bracket at 27 cycles (frozen before any data, 2026-09-24)
Purpose: the 74qx27c tracker candidate runs 27 cycles; our bracket was validated only to 16 cycles (PATCH_PREREG.md,
hash ad33761e…). Same hypothesis, counting rule and success threshold as PATCH_PREREG.md, applied to:
patches n in {27, 33} (same BFS patches of the tracker's own 51q lattice and its edge layers), cycles {20, 27},
observables {mag, zzd2, zzd3}; truth = BlueQubit statevector (device=cpu); Pauli-path delta 1e-3, 1e-4; MPS chi 64, 256.
Supported if >= 95% of points are in bracket at each n; falsified otherwise. Server-terminated jobs: at most 2 retries,
then reported as missing. No other parameters will be tried to rescue the hypothesis.
Only if supported at both n will the 74qx27c bracket (run 2) be reported as "consistent with / inconsistent with"
QESEM; otherwise it is reported as raw values with no bracket interpretation.
