"""D2 exploratory: same-day repeats of R_chi4, R_chi8 (x2) and F_chi16 (x2). Not pre-registered."""
import json, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[2]))
import run as R
import bluequbit
from kicked_ising_crosscheck import load_token
from cost_ledger import record_job, record_cost, ok_to_spend
from mirror_lib import to_qiskit
cells = {f"{c}_rep{r}": c for c in ("R_chi4", "R_chi8", "F_chi16") for r in (2, 3)}
out_dir = HERE / "results" / "cells_repeat"; out_dir.mkdir(parents=True, exist_ok=True)
bq = bluequbit.init(load_token()); jobs = {}
for cid, base in cells.items():
    ops, chi = R.CELLS[base]; assert ok_to_spend(0.0)
    j = bq.run(to_qiskit(ops, R.BITS, nq=R.N), device="mps.cpu", shots=100_000, options={"mps_bond_dimension": chi},
               asynchronous=True, job_name=f"v2diag-{cid}", force_run=True)
    record_job(j.job_id, device="mps.cpu", purpose=f"v2diag D2 {cid}"); jobs[cid] = j.job_id
while jobs:
    time.sleep(20)
    for cid, jid in list(jobs.items()):
        j = bq.get(jid)
        if str(j.run_status) not in ("COMPLETED", "FAILED_VALIDATION", "CANCELED", "TERMINATED", "FAILED"): continue
        record_cost(jid, j.cost, device="mps.cpu", purpose=f"v2diag D2 {cid}")
        (out_dir / f"{cid}.json").write_text(json.dumps({"id": cid, "job_id": jid, "status": str(j.run_status), "cost": j.cost,
            "counts": j.get_counts() if str(j.run_status) == "COMPLETED" else None}, default=str))
        print(cid, j.run_status, "cost", j.cost, flush=True); del jobs[cid]
