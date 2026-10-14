# Replication of the BlueQubit-arm 224.08 cells: RESULT (2026-10-08)

The pre-registration is PREREG.md (frozen with sha16 4829ad8d514ea995 and registered in the gate). It covered 3 jobs, all billed $0.00 on mps.cpu at 61q, d36, χ = 256, with 2e5 shots each.

| Cell | Original (wave 6) | Replicate | Build time | Collapsed (D8 rule: build time < 10 s) |
|---|---|---|---|---|
| P2_i0 | 1 / 2e5 hits | **1 / 2e5 hits** | 821.5 s | no (the circuit was simulated) |
| M_i2, attempt 1 | 3 / 2e5 hits | 200000 / 2e5 (survival = 1) | 1.92 s | **yes** |
| M_i2, attempt 2 | — | 200000 / 2e5 | 1.86 s | **yes** → NOT RUN (collapsed twice) |

## Verdict (pre-registered rule): **INCONCLUSIVE**, because one cell is NOT RUN
- P2 reproduced exactly: 1 hit in each run.
- M_i2 collapsed on both attempts. BlueQubit cancelled U·U† at compile time, so no evolved replicate exists. This is the intermittent cancellation that wave-6 D8 already documented, observed again today.
- Descriptive only: on the one cell where the circuit was actually simulated twice, the BlueQubit number reproduces.

## Consequence
- No text change. The kit already labels this arm "instrument validation failed (V2); post-hoc build-time filter; 2 of 3 instances".
- The replication shows two things:
  1. The evolved cell reproduces exactly.
  2. Whether a cell evolves at all is not under our control: M_i2 evolved in September and collapsed twice today.
- Both support keeping the own-implementation arm as the headline and the BlueQubit arm as a labelled secondary number. The kit already does both.
