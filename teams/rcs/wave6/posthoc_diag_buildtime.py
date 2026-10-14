import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 20') if m < 20*2**20 else None
"""POST-HOC DIAGNOSTIC 2 (DEVIATIONS D6). posthoc_diag_collapse showed survival 200/200 at chi=16 with or without
barriers, mps_build_time ~1.9 s. If BlueQubit genuinely evolved the mirror, a circuit with no cancellation possible
should take a comparable build time. Test at chi=256, 100 shots: (c) forward-only U (18 cycles, first half of the
d36 mirror of inst 0, no inverse); (d) the d36 mirror with rx(pi) on qubit 30 inserted between U and U^dagger
(blocks inverse-pair cancellation at the centre). Record mps_build_time and run_time."""
import json, math, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT))
import bluequbit
from kicked_ising_crosscheck import load_token
from cost_ledger import record_job, record_cost, ok_to_spend
from mirror_lib import load_instance, to_qiskit, bitstring_key
import plan
bits = plan.INPUTS[0][0]; key = bitstring_key(bits)
fwd, bwd = load_instance(0)
ops_f = [g for s in fwd for g in s]
ops_x = ops_f + [("rx", math.pi, 30)] + [g for s in bwd for g in s]
circs = {"c_forward_only_U18": to_qiskit(ops_f, bits), "d_mirror_with_mid_X30": to_qiskit(ops_x, bits)}
bq = bluequbit.init(load_token()); out = {}; jobs = {}
for name, c in circs.items():
    assert ok_to_spend(0.0)
    j = bq.run(c, device="mps.cpu", shots=100, options={"mps_bond_dimension": 256}, asynchronous=True,
               job_name=f"rcs-w6-diag-{name}", force_run=True)
    record_job(j.job_id, device="mps.cpu", purpose=f"rcs wave6 posthoc diag {name}"); jobs[name] = j.job_id
    print("submitted", name, j.job_id, flush=True)
t0 = time.time()
while jobs and time.time() - t0 < 3 * 3600:
    time.sleep(30)
    for name, jid in list(jobs.items()):
        j = bq.get(jid)
        if str(j.run_status) in ("COMPLETED", "FAILED_VALIDATION", "CANCELED", "TERMINATED", "FAILED"):
            record_cost(jid, j.cost, device="mps.cpu", purpose=f"rcs wave6 posthoc diag {name}")
            cnt = j.get_counts() or {}
            out[name] = {"job_id": jid, "status": str(j.run_status), "err": str(j.error_message), "hits_input_key": cnt.get(key, 0),
                         "shots": 100, "n_distinct": len(cnt), "run_time_ms": j.run_time_ms, "cost": j.cost,
                         "run_results": str(j.run_results), "top3": dict(sorted(cnt.items(), key=lambda kv: -kv[1])[:3])}
            print(name, out[name], flush=True); del jobs[name]
            (HERE / "results" / "posthoc_diag_buildtime.json").write_text(json.dumps(out, indent=1))
for name, jid in jobs.items():
    out[name] = {"job_id": jid, "status": "NOT FINISHED within 3 h poll window"}
(HERE / "results" / "posthoc_diag_buildtime.json").write_text(json.dumps(out, indent=1))
