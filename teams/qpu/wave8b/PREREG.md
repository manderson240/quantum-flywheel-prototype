# Wave 8b (QPU): barrier mirrors, testing whether wave 8's mirrors were compiled away — PRE-REGISTRATION

Frozen 2026-10-05 before any job of this wave. Authorisation: Mike, 2026-10-05 ("Proceed"), on the remaining BlueQubit
account credit expiring 2026-10-05. Same caveat as wave 8: device `quantum`, backend not reported; no hardware claims.

## Question
Wave 8's mirror retention r_c did not fall with depth (0.942, 0.945, 0.934, 0.940 at c = 1–4). Post-hoc hypothesis H:
the platform compiler cancelled U·U†. Test: the identical mirrors with a barrier between U and U† (and between every
Floquet layer), which a standard (Qiskit-type) transpiler must not optimise across.

## Jobs (4 × $0.72; 1,000 shots; device quantum; fixed order K1–K4)
K_c, c = 1…4: X on input bits s (same s as wave 8, rng 20261005), U(c) with a barrier after every layer, a full
barrier, U(c)† with a barrier after every layer, measure_all. Nothing else changes from wave 8 J5–J8.
Wave cap $3.00; stop on billed cost > $1.08 or NOT_ENOUGH_FUNDS; all four submitted together (credit expiry).
Before submission: free mps.cpu check at χ = 512 returns s in 1000/1000 shots for each K_c (else stop).

## Analysis (fixed now; binomial SEs √(1 − r²)/√(19 000))
- r_c^b = mean_q (1 − 2·P(q ≠ s_q)) for K_c; r_c = wave-8 J5–J8 values.
- H SUPPORTED if r_c^b < r_c by more than 3σ (combined) at both c = 3 and c = 4, AND r_4^b < r_1^b by more than 3σ.
  H NOT SUPPORTED if |r_c^b − r_c| ≤ 3σ at all four c. Otherwise MIXED.
- Calibration re-test (secondary): M_pred,c = M_exact,c · √(r_c^b · ρ) with wave-8 ρ and wave-8 J1–J4 ⟨M⟩; report
  agreement within 3σ at k of 4 depths.

## Frozen wording
"With barriers preventing compiler cancellation, mirror retention on the same device was <r1..r4> at 1–4 cycles
(versus <r1..r4> without barriers): the compiled-away hypothesis is <SUPPORTED/NOT SUPPORTED/MIXED>; the re-calibrated
model agrees with the device within 3σ at <k> of 4 depths." Backend not reported; no hardness claim.
