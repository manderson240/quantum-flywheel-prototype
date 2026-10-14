# Wave 8 (QPU) result — PREREG sha16 c29f1ce2d3ca4d2c; deviations D1, D2

Run 2026-10-05. 10 jobs (J0–J9) on BlueQubit device `quantum`, all COMPLETED, billed $0.72 each = $7.20 (account
credit). J10/J11 not run (D2). Source: results/J*.json, results/analysis.json. Not yet independently verified.

## Pre-registered analysis (results/analysis.json)
| cycles | device ⟨M⟩ ± SE | exact ⟨M⟩ | Δ (z) | mirror-model prediction | within 3σ |
|---|---|---|---|---|---|
| 1 | 0.321 ± 0.008 | 0.463 | −0.142 (−18.9) | 0.425 | no |
| 2 | 0.151 ± 0.008 | 0.201 | −0.050 (−6.1) | 0.185 | no |
| 3 | 0.131 ± 0.008 | 0.273 | −0.143 (−17.0) | 0.249 | no |
| 4 | 0.085 ± 0.008 | 0.411 | −0.327 (−40.2) | 0.377 | no |
ZZ_d2 (secondary): device 0.116 / 0.038 / 0.058 / 0.025 vs exact 0.222 / 0.274 / 0.289 / 0.362.
Readout (J0, X on all): ρ = 0.892 ± 0.012 (across-qubit SE; binomial SE 0.003, see D3); all-ones string in 358/1000 shots. Mirror retention r_c = 0.942, 0.945, 0.934,
0.940 (c = 1–4); mirror survival 0.580, 0.593, 0.522, 0.564. J9 (repeat of J1) counts differ from J1.
Attribution hints: none fired (readout is not perfect; the repeat is not identical).

Frozen wording, filled exactly per the template (c = 1; other depths are in the table): "On BlueQubit's 'quantum' device
(backend not reported by the platform), 19-qubit Floquet Ising circuits with exactly computed answers gave ⟨M⟩ =
0.321 ± 0.008 against exact 0.463 at 1 cycles; a mirror calibration measured on the same device predicts 0.425,
agreeing within 3σ at 0 of 4 depths. This exercises our scoring pipeline on device output; it says nothing about
classical hardness." (Template grammar is kept verbatim, including "1 cycles".)
SE convention (D3): with the pre-registered binomial SEs for r_c and ρ, agreement is still 0 of 4 (|z| = 13.6, 4.1,
14.1, 35.8).

## Post hoc (NOT pre-registered; labelled as such wherever used)
- The mirror calibration is very likely degenerate: retention and survival do not fall with depth (r ≈ 0.94 and survival
  ≈ 0.55 at c = 1 and c = 4, where the forward circuits lose most of their signal). The most likely cause is that the
  platform's compiler cancels U·U† (the mirror is an exact inverse pair with no barrier), so the mirror measured state
  preparation + readout only. Not verified: BlueQubit returns no transpiled circuit. Consequence: the pre-registered
  model's failure at 4/4 depths does not show the depolarising model is wrong; it shows this calibration measured the wrong
  thing. TESTED in wave 8b (pre-registered, same day): with barriers, retention falls to 0.30 at c = 1 and ≈ 0 from
  c = 2; the compiled-away hypothesis is SUPPORTED (teams/qpu/wave8b/RESULT.md).
- Readout is asymmetric (all-ones string only 35.8% of shots, per-qubit ρ = 0.89), consistent with T1-type decay during
  readout. A symmetric-readout model under-corrects.
- Device attenuation relative to exact, M_hw/M_exact = 0.694, 0.753, 0.478, 0.206 at c = 1–4, is depth-dependent but NOT
  monotone (c = 2 is better than c = 1). The gap is many σ at every depth.
- Evidence about the backend points both ways. Pointing to a physical device: imperfect and asymmetric readout,
  J9 ≠ J1 counts, and a long queue (22–55 min; wave 6: 13 s). Pointing to an emulator or batched service: run_time_ms = 1
  on every job, and 9 of 10 jobs started within 2.0 s of each other (18:51:27.234–18:51:29.245 UTC, about 250 ms
  apart). A noisy emulator could also produce the first group. The backend remains unattributed until BlueQubit names it.

## What this adds
A worked, pre-registered example of the proposal's core loop on device output: exact classical answers, device
estimates with error bars, a calibration attempt, and a failure caught and explained rather than hidden.
Ledger: $12.38 prior + $7.20 = $19.58 (+ wave 8b $2.88 = $22.46) total, all within the subscription + account credit.
