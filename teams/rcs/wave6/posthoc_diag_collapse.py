import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 20') if m < 20*2**20 else None
"""POST-HOC DIAGNOSTIC (not pre-registered; DEVIATIONS D6). P1 and M_i1_d36_chi256 returned survival 200000/200000 at
61q d36 with mps_build_time ~1.9 s, while own MPS gives ~1e-7..1e-6 at chi 128..256. Hypothesis H: BlueQubit's
pipeline simplifies U U^dagger (adjacent inverse gates cancel) before the MPS runs, so the mirror is never simulated.
Test: same circuit at chi=16 (own MPS: 2.5e-10), (a) without barriers as in the main scan, (b) with a barrier after
every released segment (barriers block gate cancellation). H predicts (a) ~1 and (b) ~0. 200 shots each."""
import json, math, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT))
import bluequbit
from qiskit import QuantumCircuit
from kicked_ising_crosscheck import load_token
from cost_ledger import record_job, record_cost, ok_to_spend
from mirror_lib import load_instance, derived_ops, to_qiskit, bitstring_key
import plan

bits = plan.INPUTS[0][0]; key = bitstring_key(bits)
fwd, bwd = load_instance(0)
def barriered(bits):
    c = QuantumCircuit(61)
    for q, x in enumerate(bits):
        if x: c.rx(math.pi, q)
    c.barrier()
    for s in fwd + bwd:
        for g in s:
            if g[0] == "cz": c.cz(g[1], g[2])
            else: getattr(c, g[0])(g[1], g[2])
        c.barrier()
    c.measure_all(); return c
circs = {"a_no_barrier": to_qiskit(derived_ops(0, 36), bits), "b_barrier_every_segment": barriered(bits)}
bq = bluequbit.init(load_token()); out = {}
jobs = {}
for name, c in circs.items():
    assert ok_to_spend(0.0)
    j = bq.run(c, device="mps.cpu", shots=200, options={"mps_bond_dimension": 16}, asynchronous=True,
               job_name=f"rcs-w6-diag-{name}", force_run=True)
    record_job(j.job_id, device="mps.cpu", purpose=f"rcs wave6 posthoc diag {name}"); jobs[name] = j.job_id
    print("submitted", name, j.job_id, flush=True)
while jobs:
    time.sleep(30)
    for name, jid in list(jobs.items()):
        j = bq.get(jid)
        if str(j.run_status) in ("COMPLETED", "FAILED_VALIDATION", "CANCELED", "TERMINATED", "FAILED"):
            record_cost(jid, j.cost, device="mps.cpu", purpose=f"rcs wave6 posthoc diag {name}")
            cnt = j.get_counts() or {}
            out[name] = {"job_id": jid, "status": str(j.run_status), "err": str(j.error_message), "hits": cnt.get(key, 0),
                         "shots": 200, "n_distinct": len(cnt), "run_time_ms": j.run_time_ms, "cost": j.cost,
                         "run_results": str(j.run_results), "top3": dict(sorted(cnt.items(), key=lambda kv: -kv[1])[:3])}
            print(name, out[name], flush=True); del jobs[name]
(HERE / "results" / "posthoc_diag_collapse.json").write_text(json.dumps(out, indent=1))
