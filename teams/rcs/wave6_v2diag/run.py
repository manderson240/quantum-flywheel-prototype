"""V2 diagnostic (PREREG.md, frozen bd0b051e5df63034): submit cells F_chi, B_chi (chi 4/8/16) and R_chi (chi 4/8) on
BlueQubit mps.cpu, 16q, 1e5 shots; collect full counts to results/cells/<id>.json. No token is printed."""

import json
import math
import sys
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
W6 = HERE.parent / "wave6"
sys.path.insert(0, str(W6))
sys.path.insert(0, str(ROOT))
import bluequbit
import plan
from cost_ledger import ok_to_spend, record_cost, record_job
from kicked_ising_crosscheck import load_token
from mirror_lib import derived_ops, load_instance, to_qiskit
from own_mps import restrict


N = 16
BITS = plan.INPUT16
fwd, _ = load_instance(0)
F_OPS = restrict([g for s in fwd[:36] for g in s], N)
M_OPS = restrict(derived_ops(0, 36), N)
k = len(F_OPS)
assert M_OPS[:k] == F_OPS, "mirror must start with the forward half"
B_OPS = F_OPS + [("rx", math.pi, 0)] + M_OPS[k:]
CELLS = {f"F_chi{x}": (F_OPS, x) for x in (4, 8, 16)}
CELLS |= {f"B_chi{x}": (B_OPS, x) for x in (4, 8, 16)}
CELLS |= {f"R_chi{x}": (M_OPS, x) for x in (4, 8)}


def ops_of(cid):
    return CELLS[cid][0]


if __name__ == "__main__":
    out_dir = HERE / "results" / "cells"
    out_dir.mkdir(parents=True, exist_ok=True)
    bq = bluequbit.init(load_token())
    jobs = {}
    for cid, (ops, chi) in CELLS.items():
        if (out_dir / f"{cid}.json").exists():
            continue
        assert ok_to_spend(0.0)
        j = bq.run(
            to_qiskit(ops, BITS, nq=N),
            device="mps.cpu",
            shots=100_000,
            options={"mps_bond_dimension": chi},
            asynchronous=True,
            job_name=f"v2diag-{cid}",
            force_run=True,
        )
        record_job(j.job_id, device="mps.cpu", purpose=f"v2diag {cid}")
        jobs[cid] = j.job_id
        print("submitted", cid, j.job_id, flush=True)
    while jobs:
        time.sleep(20)
        for cid, jid in list(jobs.items()):
            j = bq.get(jid)
            if str(j.run_status) not in (
                "COMPLETED",
                "FAILED_VALIDATION",
                "CANCELED",
                "TERMINATED",
                "FAILED",
            ):
                continue
            record_cost(jid, j.cost, device="mps.cpu", purpose=f"v2diag {cid}")
            if j.cost and float(j.cost) > 0:
                print("BILLED > $0:", cid, j.cost, "-- stopping per PREREG", flush=True)
            cnt = j.get_counts() if str(j.run_status) == "COMPLETED" else None
            (out_dir / f"{cid}.json").write_text(
                json.dumps(
                    {
                        "id": cid,
                        "job_id": jid,
                        "chi": CELLS[cid][1],
                        "status": str(j.run_status),
                        "err": str(j.error_message),
                        "cost": j.cost,
                        "run_time_ms": j.run_time_ms,
                        "counts": cnt,
                    },
                    default=str,
                )
            )
            print(
                cid,
                str(j.run_status),
                "cost",
                j.cost,
                "distinct",
                len(cnt or {}),
                "sum",
                sum((cnt or {}).values()),
                flush=True,
            )
            del jobs[cid]
            if j.cost and float(j.cost) > 0:
                sys.exit(2)
