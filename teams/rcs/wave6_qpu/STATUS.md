# wave6_qpu STATUS (2026-09-26). PREREG sha16 3facc6f83d950e40 (frozen 12:07:54, before any QPU job). Spend $0.72 of the approved $3.
1. Builder validated free on mps.cpu (χ=256): derived mirrors at d = 4, 8, 12 return the input in 1000/1000 shots. The first run
   exposed a bit-order bug in our comparison; BlueQubit keys are qubit-0-first (DEVIATIONS.md D1).
2. QPU, d = 4 (94 CZ, 61 qubits), job Z83WrUyTxMvrOqaQ, cost $0.72: 28/1000 survive, p = 0.028, Wilson 95% [0.019, 0.040].
   898 distinct outcomes.
3. Nighthawk r2 pooled survival at d = 4 (paper's released counts, wave-3 estimator): 0.2136 ± 0.0014. Ratio 0.13.
4. Frozen wording: "On <BlueQubit 'quantum' device, backend not reported> via BlueQubit, a mirror derived from the paper's
   released 36-cycle instance 0 returns its input in 0.028 [0.019, 0.040] of 1,000 shots at depth 4, against 0.214 pooled on
   Nighthawk r2. Different device, layout, transpilation, instance depth and inputs: this is a descriptive cross-hardware data
   point, not a replication and not evidence about the paper's advantage claim."
5. INSTRUMENT CAVEAT: the result reports no backend name, empty device_options, run_results None, and run_start = run_end
   (1 ms). Whether `quantum` is physical hardware or an emulator is UNKNOWN. Treat the value as unattributed until BlueQubit
   confirms the backend (a question only the user can send).
6. Stopped after d = 4, as the PREREG permits (its conditions are necessary, not sufficient). At this survival level, d = 8 is
   expected near the 1,000-shot floor, and the backend is unresolved. d = 8 and d = 12 were NOT RUN.
7. Bit-order check (Fable review 2, C2; free re-fetch, results/quantum_d4_bitorder_check.json): q0-first order gives 28 hits,
   mean Hamming distance to the input 3.62, 50.8% of shots within 3 bits; reversed order gives 0 hits, mean distance 28.61
   (random ≈ 30.5). The q0-first scoring is confirmed on the QPU counts, and p = 0.028 stands. The backend is still unattributed.
