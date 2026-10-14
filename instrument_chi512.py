import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 20') if m < 20*2**20 else None
"""Instrument check (iii), re-run 2026-09-27 to give report line 37 a raw result: BlueQubit mps.cpu at chi=512 (exact capacity
at 19 qubits) vs the local statevector on the 19q kicked-Ising circuits, plus a bit-identical repeat. Free tier; ids journaled."""
import json, math
import bluequbit
from kicked_ising_crosscheck import OUT, heavy_hex_edges, kicked_ising, mean_z_terms, exact_mean_z, load_token
from cost_ledger import ok_to_spend, record_job, record_cost
n, edges = heavy_hex_edges(3); terms = mean_z_terms(n); bq = bluequbit.init(load_token()); rows = []
for th in [math.pi / 8, math.pi / 4, 3 * math.pi / 8]:
    qc = kicked_ising(n, edges, th, 5); ex = exact_mean_z(qc, terms); vals = []
    for rep in (1, 2):
        assert ok_to_spend(0.0)
        j = bq.run(qc, device="mps.cpu", pauli_sum=terms, options={"mps_bond_dimension": 512}, asynchronous=True)
        record_job(j.job_id, device="mps.cpu", purpose="instrument_chi512"); r = bq.wait(j.job_id)
        record_cost(j.job_id, r.cost, device="mps.cpu"); assert (r.cost or 0) == 0, r.cost
        vals.append(float(r.expectation_value))
    rows.append({"theta_h": th, "n": n, "exact_local": ex, "mps512": vals, "abs_diff": abs(vals[0] - ex), "repeat_identical": vals[0] == vals[1]})
    print(rows[-1], flush=True)
(OUT / "instrument_chi512.json").write_text(json.dumps({"rows": rows, "max_abs_diff": max(r["abs_diff"] for r in rows),
    "all_repeats_identical": all(r["repeat_identical"] for r in rows)}, indent=1))
