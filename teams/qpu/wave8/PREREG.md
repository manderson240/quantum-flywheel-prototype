# Wave 8 (QPU): classically scored device output on circuits with exactly known answers — PRE-REGISTRATION

Frozen 2026-10-05 before any job of this wave (sha16 in PREREG.sha16, listed in graph/gate.py PREREGS).
Authorisation: Mike, 2026-10-05, "focus on what's available to us with the bluequbit environment"; budget = the BlueQubit
account credit that expires 2026-10-05, nothing else.

## Question
Our application's thesis is classical scoring of quantum-device output. Wave 6 ran one 61-qubit mirror job on BlueQubit's
`quantum` device ($0.72; 28/1000 survival) but had no circuit with a known answer. This wave runs circuits whose exact
answer we compute locally (19-qubit statevector; the same 19-qubit Floquet mixed-field Ising patch as
results/floquet_oracle19.json, tracker angles θx = 1.56567, θz = 0.33879, θzz = π/3) and scores the device output against
it, with a mirror calibration measured on the same device in the same session.

## Device caveat (fixed now, applies to every sentence written from this wave)
BlueQubit reports no backend name for `quantum` (wave 6: empty device_options, run_time_ms = 1, queue 13 s). Every result
is worded "BlueQubit 'quantum' device (backend not reported by the platform)". Nothing here may be called "IBM hardware"
or "real hardware" unless BlueQubit names the backend in writing. Attribution hints below are hints, not proof.

## Jobs (fixed order; 1,000 shots each, the configuration wave 6 was billed for; circuits end in measure_all)
- J0 readout: X on all 19 qubits.
- J1–J4 Floquet: cycles c = 1, 2, 3, 4 from |0…0⟩ (floquet_oracle19.circuit, three_colour seed 0).
- J5–J8 mirror: input bitstring s (numpy default_rng(20261005), 19 bits, applied as X), then U(c) then U(c)†, c = 1…4.
- J9 repeat: J1 resubmitted unchanged.
- J10, J11 Floquet c = 6, 8 (only if J0–J9 billed as estimated).
Maximum 12 jobs, $8.64 at the estimated $0.72/job. Budget guard: cost_ledger CAP and wave cap $9.00.

## Stop rules
- Before J0: the builder passes on mps.cpu (free): Floquet ⟨M⟩ within 4 SE of exact at c = 1…4 with 1,000 shots; mirrors
  return s in 1000/1000 shots; X on qubit 0 alone shows '1' in key position 0 (qubit-0-first keys, wave-6 D1).
- After any job: stop the wave if its billed cost exceeds $1.08 (1.5× estimate), if the status is not COMPLETED twice in a
  row, or on NOT_ENOUGH_FUNDS. No retries of a COMPLETED job. A FAILED job may be resubmitted once.
- Exact values are recomputed locally (qiskit Statevector) and must equal results/floquet_oracle19.json `exact` for
  (c, mag) and (c, zzd2) to 1e-9, else stop before scoring (wrong circuit).

## Analysis (fixed now)
Keys are qubit-0-first. Per shot, z_q = 1 − 2·bit_q.
- M_hw = mean over shots and qubits of z_q; SE = std over shots of the per-shot mean / √shots. Secondary: ZZ_d2 (pairs at
  graph distance 2, as in oracle19), same SE construction.
- Δ_c = M_hw − M_exact, z_c = Δ_c / SE.
- Readout attenuation ρ = mean_q (1 − 2·P(q reads 0 | X applied)) from J0.
- Mirror retention r_c = mean_q (1 − 2·P(q ≠ s_q)) from J5–J8.
- Model (descriptive, single-qubit depolarising + symmetric readout): M_pred,c = M_exact,c · √(r_c · ρ). Agreement means
  |M_hw − M_pred| ≤ 3·√(SE² + SE_pred²), SE_pred by the delta method from the binomial SEs of r_c and ρ. Reported for every
  c either way; this model is a calibration story, not a claim about the device.
- Attribution hints (reported, never claimed as proof): ρ = 1 exactly and all mirrors 1000/1000 → "consistent with a
  noiseless simulator"; J9 counts identical to J1 → "consistent with a seeded emulator".

## Frozen wording (numbers filled from the analysis; no other claim)
"On BlueQubit's 'quantum' device (backend not reported by the platform), 19-qubit Floquet Ising circuits with exactly
computed answers gave ⟨M⟩ = <M_hw ± SE> against exact <M_exact> at <c> cycles; a mirror calibration measured on the same
device predicts <M_pred>, <agreeing/not agreeing> within 3σ at <k> of <K> depths. This exercises our scoring pipeline on
device output; it says nothing about classical hardness."
