# Independent recompute of wave 8 / wave 8b (2026-10-06)

Written by the parent session from the verifier agent's returned text; the agent was not permitted to write files.
I spot-checked that recompute.py imports nothing from wave8.py, wave8b.py, check_claims.py or analysis.json; its only
project import is the floquet_oracle19 builders.

**Script:** recompute.py (this directory). **Output:** recompute.json.

**Inputs:**
- raw counts in wave8/results/J0–J9.json and wave8b/results/K1–K4.json;
- results/floquet_oracle19.json, used only for comparison.

No jobs were submitted and no paid API was called. Local compute was one 19-qubit statevector per depth.

## Conventions, checked independently
- **Bit order:** J0 cannot settle it, because the all-ones string is symmetric. The mirrors with input
  s = 0000101001110100000 do settle it. Reading keys qubit-0-first gives r = 0.94 and 522–593 survivals; reversed order
  gives r ≈ −0.04 and 0 survivals. This confirms wave-6 D1.
- **Exact values:** our own Statevector agrees with oracle19 "exact"/mag to 2.8e-16 at c = 1–4.
- **SE:** ddof 0 and ddof 1 differ by less than 4e-6.

| # | Claim | Recomputed | Match | Note |
|---|---|---|---|---|
| 1a | c1 0.321±0.008 | 0.3215±0.0075 | yes | |
| 1b | c2 0.151±0.008 | 0.1514±0.0081 | yes | |
| 1c | c3 0.131±0.008 | 0.1306±0.0084 | yes | |
| 1d | c4 0.085±0.008 | 0.0848±0.0081 | yes | |
| 1e | exact 0.463/0.201/0.273/0.411 | 0.4634/0.2010/0.2732/0.4114 | yes | |
| 2 | ρ=0.892; 358/1000 | 0.8923; 358 | yes | "±0.012" is std over qubits/√19; binomial SE is 0.0033 (not a tested claim) |
| 3a | r 0.942/0.945/0.934/0.940 | 0.9419/0.9446/0.9344/0.9403 | yes | |
| 3b | survival .580/.593/.522/.564 | 580/593/522/564 | yes | |
| 4 | J9≠J1 | differ, TVD 0.964 | yes | J9 ⟨M⟩ 0.326±0.007 |
| 5a | rb .297/.019/−.028/−.013 | .2973/.0188/−.0279/−.0126 | yes | |
| 5b | survival 0 each | 0,0,0,0 | yes | |
| 5c | H SUPPORTED | z −87.8/−121.3/−125.0/−124.4; r4b−r1b z −30.9 | yes | |
| 6a | wave-8 recal 0/4 | \|z\| 13.6/4.1/14.2/35.8 | yes | delta method, binomial SEs |
| 6b | wave-8b recal 0/4 | pred .239/.026/0/0; \|z\| 10.3/13.1/15.6/10.5 | yes | r≤0 clipped to 0 |
| 7 | 14 jobs, $0.72, 2026-10-05 | 14 COMPLETED, 0.72, dated 10-05; ids match bq_jobs.jsonl | yes | both sources are self-recorded, not a BlueQubit invoice |

**Residual risk:** if the original analysis and this recompute misread the same PREREG sentence, both are wrong in the
same way.

RECOMPUTE: MATCH=19 MISMATCH=0
