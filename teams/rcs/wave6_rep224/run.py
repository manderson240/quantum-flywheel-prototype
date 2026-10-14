"""Replication per PREREG.md (frozen 4829ad8d514ea995): resubmit P2_i0_d36_chi256 and M_i2_d36_chi256 on mps.cpu, with
the D8 collapse rule (build < 10 s -> one resubmission). Writes results/<cell>.<attempt>.json. No token printed."""
import json, re, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]; W6 = HERE.parent / "wave6"
sys.path.insert(0, str(W6)); sys.path.insert(0, str(ROOT))
import bluequbit
from kicked_ising_crosscheck import load_token
from cost_ledger import record_job, record_cost, ok_to_spend
from mirror_lib import to_qiskit, bitstring_key
from controller import ops_for

CELLS = ["P2_i0_d36_chi256", "M_i2_d36_chi256"]
out = HERE / "results"; out.mkdir(exist_ok=True)
bq = bluequbit.init(load_token())
def submit(cid, attempt):
    c = json.load(open(W6 / "results" / "cells" / f"{cid}.json"))
    assert ok_to_spend(0.0)
    j = bq.run(to_qiskit(ops_for(c), c["bits"], nq=61), device="mps.cpu", shots=200_000,
               options={"mps_bond_dimension": 256}, asynchronous=True, job_name=f"rep224-{cid}-a{attempt}", force_run=True)
    record_job(j.job_id, device="mps.cpu", purpose=f"rep224 {cid} a{attempt}"); print("submitted", cid, attempt, j.job_id, flush=True)
    return {"cid": cid, "attempt": attempt, "job": j.job_id, "key": bitstring_key(c["bits"])}
live = [submit(c, 1) for c in CELLS]
while live:
    time.sleep(120)
    for r in list(live):
        j = bq.get(r["job"])
        if str(j.run_status) not in ("COMPLETED", "FAILED_VALIDATION", "CANCELED", "TERMINATED", "FAILED"): continue
        record_cost(r["job"], j.cost, device="mps.cpu", purpose=f"rep224 {r['cid']} a{r['attempt']}")
        if j.cost and float(j.cost) > 0: print("BILLED > $0, stopping", flush=True); sys.exit(2)
        m = re.search(r"mps_build_time['\"]?\s*[:=]\s*([0-9.]+)", str(j.run_results)); bt = float(m[1]) if m else None
        top = j.top_128_results or {}; cnt = j.get_counts() or {} if str(j.run_status) == "COMPLETED" else {}
        hits = top.get(r["key"], cnt.get(r["key"], 0)) if str(j.run_status) == "COMPLETED" else None
        rec = {**r, "status": str(j.run_status), "cost": j.cost, "mps_build_time_s": bt, "hits": hits, "shots": 200_000,
               "run_time_ms": j.run_time_ms, "collapsed": (bt is not None and bt < 10), "n_distinct": len(cnt)}
        (out / f"{r['cid']}.a{r['attempt']}.json").write_text(json.dumps(rec, default=str, indent=1)); print(rec, flush=True)
        live.remove(r)
        if rec["collapsed"] and r["attempt"] == 1: live.append(submit(r["cid"], 2))
