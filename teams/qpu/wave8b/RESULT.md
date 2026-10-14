# Wave 8b (QPU) result: barrier mirrors. PREREG sha16 a9dc195995516c58

Run 2026-10-05. 4 jobs (K1–K4) on BlueQubit device `quantum`, all COMPLETED, $0.72 each = $2.88 of account credit
(ledger total $22.46). Queue 1.7–1.9 h per job. Validated beforehand: exact locally and 1000/1000 on mps.cpu at χ = 512.
Source: results/K*.json, results/analysis.json. Not yet independently verified.

## Pre-registered analysis
| cycles | r, barrier | r, no barrier (wave 8) | z (binomial) | survival, barrier |
|---|---|---|---|---|
| 1 | 0.297 | 0.942 | −87.8 | 0/1000 |
| 2 | 0.019 | 0.945 | −121.3 | 0/1000 |
| 3 | −0.028 | 0.934 | −125.0 | 0/1000 |
| 4 | −0.013 | 0.940 | −124.4 | 0/1000 |
Hypothesis H (wave 8's mirrors were compiled away): **SUPPORTED** by the pre-registered rule.
Re-calibration with the barrier r_c: agreement within 3σ at 0 of 4 depths (predicted 0.239, 0.026, 0.000, 0.000 vs
device 0.321, 0.151, 0.131, 0.085).

Frozen wording, filled: "With barriers preventing compiler cancellation, mirror retention on the same device was 0.297,
0.019, −0.028, −0.013 at 1–4 cycles (versus 0.942, 0.945, 0.934, 0.940 without barriers): the compiled-away hypothesis
is SUPPORTED; the re-calibrated model agrees with the device within 3σ at 0 of 4 depths." Backend not reported; no
hardness claim.

## Post hoc (NOT pre-registered)
- The two calibrations BRACKET the device at every depth. The no-barrier mirror (readout only) over-predicts ⟨M⟩, and the
  barrier mirror under-predicts it. Neither is a calibration of the forward circuits.
- The barrier mirror at c = 2 has exactly the gate content of the forward c = 4 circuit (80 RZZ, 228 RX + 228 RZ). It keeps
  r = 0.019, while forward c = 4 keeps M_hw/M_exact = 0.206. These are different observables: per-qubit retention of a
  random product input, against magnetization from |0…0⟩. Untested candidate explanations:
  - barriers block single-qubit gate fusion and routing optimisation, so the barrier circuits run more physical gates;
  - the forward circuits may themselves be partly simplified by the compiler;
  - the noise may be observable-dependent (for example, coherent errors that partly cancel in ⟨M⟩).
  Nothing here distinguishes these. BlueQubit returns no transpiled circuit.
- K1 and K2 gave 975 and 998 distinct outcomes, against 88–95 for wave-8 mirrors, and run_start values minutes apart.
  This is consistent with a full-depth circuit being executed.
- Lesson: on a platform that compiles but does not return the compiled circuit, a mirror calibration must carry barriers.
  Even then it calibrates the barrier circuit, not the forward one.
