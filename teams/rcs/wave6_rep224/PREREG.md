# Replication of the BlueQubit-arm cells behind the kit's 224.08 figure (pre-registered 2026-10-08)

POST HOC relative to wave 6/7. Frozen (PREREG.sha16) before any job below is submitted. Private; not to be posted.

## Why
The kit quotes the BlueQubit mps.cpu arm as a ratio of 224.08. It is pooled from two evolved 61q d36 χ=256 mirror cells:
- P2_i0: 1 hit / 2e5 shots
- M_i2: 3 hits / 2e5 shots

That gives 4 / 4e5 hits; F_hw(36) = 2.2408e-3, and 224.08 = F_hw / (4/4e5).

The V2 diagnostic (teams/rcs/wave6_v2diag/RESULT.md) found that mps.cpu mirror survivals at 16q have run-to-run outliers well beyond shot noise. Does the 61q figure reproduce?

## Jobs ($0, mps.cpu)
- An exact resubmission of each cell: same circuit (`to_qiskit(ops_for(cell), cell.bits, nq=61)` from wave-6 controller.py), χ = 256, 2e5 shots, options `{"mps_bond_dimension": 256}`, force_run.
- **Collapse rule** (wave-6 D8, unchanged): `mps_build_time` < 10 s means collapsed. A collapsed cell gets one resubmission; if that also collapses, the cell is NOT RUN.
- Every job passes through `cost_ledger.ok_to_spend(0.0)`. If any job is billed above $0, stop.

## Measures and decision rule
- **Replicate pooled hits:** H_rep over the evolved replicates. The replicate ratio is F_hw / (H_rep / shots_rep).
- **REPRODUCED** if the original pooled rate 4/4e5 lies inside the exact Poisson (Garwood) 95% interval of H_rep, **and** H_rep/shots_rep lies inside the Garwood 95% interval of the original 4 hits (1.09–10.24 hits per 4e5, i.e. a ratio of 88–822).
- **NOT REPRODUCED** if both conditions fail.
- **INCONCLUSIVE** if only one fails, or if any cell is NOT RUN.
- Per-cell values are reported descriptively.

## Consequence
- The result is reported whichever way it falls, in RESULT.md.
- **NOT REPRODUCED:** decision for Mike on whether the kit's BlueQubit-arm sentence needs a clause, with a two-family round before any text change.
- **REPRODUCED or INCONCLUSIVE:** no text change.
