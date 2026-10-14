"""Allowance probe (2026-10-06, after the $25 credit expired 2026-10-05): do the CPU simulators still run at $0?
Submits two tiny 4-qubit jobs (statevector `cpu`, and `mps.cpu` at chi=4), 100 shots each, and reads the BILLED cost
back from the job record, not from an estimate. Writes results/probe_allowance_20261006.json. No token is printed."""

import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bluequbit
from cost_ledger import ok_to_spend, record_cost, record_job
from kicked_ising_crosscheck import load_token
from qiskit import QuantumCircuit


c = QuantumCircuit(4)
c.h(0)
[c.cx(0, k) for k in range(1, 4)]
c.measure_all()
bq = bluequbit.init(load_token())
out = {}
for dev, opts in (("cpu", {}), ("mps.cpu", {"mps_bond_dimension": 4})):
    assert ok_to_spend(0.0)
    j = bq.run(
        c, device=dev, shots=100, options=opts, asynchronous=True, job_name=f"probe-allowance-{dev}"
    )
    record_job(j.job_id, device=dev, purpose="allowance probe 2026-10-06")
    for _ in range(60):
        j = bq.get(j.job_id)
        if str(j.run_status) in (
            "COMPLETED",
            "FAILED_VALIDATION",
            "CANCELED",
            "TERMINATED",
            "FAILED",
        ):
            break
        time.sleep(5)
    record_cost(j.job_id, j.cost, device=dev, purpose="allowance probe 2026-10-06")
    out[dev] = {
        "job_id": j.job_id,
        "status": str(j.run_status),
        "cost": j.cost,
        "err": str(j.error_message),
        "counts": j.get_counts() if str(j.run_status) == "COMPLETED" else None,
        "run_time_ms": j.run_time_ms,
    }
    print(dev, {k: v for k, v in out[dev].items() if k != "counts"}, flush=True)
(ROOT / "results" / "probe_allowance_20261006.json").write_text(
    json.dumps(out, indent=1, default=str)
)
