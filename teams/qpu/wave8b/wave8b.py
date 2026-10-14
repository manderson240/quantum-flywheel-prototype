"""Wave 8b barrier mirrors (PREREG.md). Token read in-process, never printed.
python wave8b.py validate | submit | collect | analyze
"""

import hashlib
import json
import math
import sys
import time
from pathlib import Path


HERE = Path(__file__).parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "teams/qpu/wave8"))
assert (
    hashlib.sha256((HERE / "PREREG.md").read_bytes()).hexdigest()[:16]
    == (HERE / "PREREG.sha16").read_text().strip()
)
from cost_ledger import ok_to_spend, record_cost, record_job
from floquet_oracle19 import TX, TZ, TZZ
from qiskit import QuantumCircuit
from wave8 import LAYERS, TERM, N, S, bq_client, retention


RES = HERE / "results"
RES.mkdir(exist_ok=True)
IDS = RES / "job_ids.json"
W8 = ROOT / "teams/qpu/wave8/results"


def floquet_layers(c):
    out = []
    for _ in range(c):
        for lay in LAYERS:
            q = QuantumCircuit(N)
            for k in range(N):
                q.rx(TX / 3, k)
                q.rz(TZ / 3, k)
            for a, b in lay:
                q.rzz(TZZ, a, b)
            out.append(q)
    return out


def build(c):
    q = QuantumCircuit(N)
    for k in range(N):
        if S[k]:
            q.x(k)
    q.barrier()
    L = floquet_layers(c)
    for l in L:
        q.compose(l, inplace=True)
        q.barrier()
    q.barrier()
    for l in reversed(L):
        q.compose(l.inverse(), inplace=True)
        q.barrier()
    q.measure_all()
    return q


TARGET = "".join(map(str, S))


def validate():
    bq = bq_client()
    rep = {}
    ok = True
    for c in (1, 2, 3, 4):
        j = bq.run(
            build(c),
            device="mps.cpu",
            shots=1000,
            asynchronous=True,
            options={"mps_bond_dimension": 512},
        )
        while (r := bq.get(j.job_id)).run_status not in TERM:
            time.sleep(10)
        h = r.get_counts().get(TARGET, 0)
        rep[f"K{c}"] = h
        ok &= h == 1000
        print(f"K{c}", h, flush=True)
    rep["pass"] = bool(ok)
    (RES / "validate_mpscpu.json").write_text(json.dumps(rep, indent=1))
    print("VALIDATE", ok)


def submit():
    assert json.loads((RES / "validate_mpscpu.json").read_text())["pass"], "STOP: not validated"
    ids = json.loads(IDS.read_text()) if IDS.exists() else {}
    for c in (1, 2, 3, 4):
        k = f"K{c}"
        if k in ids:
            continue
        assert ok_to_spend(0.72) and 0.72 * (len(ids) + 1) <= 3.0
        j = bq_client().run(build(c), device="quantum", shots=1000, asynchronous=True)
        record_job(
            j.job_id, device="quantum", purpose=f"wave8b_qpu {k} barrier mirror c{c}", est_cost=0.72
        )
        ids[k] = j.job_id
        IDS.write_text(json.dumps(ids, indent=1))
        print("submitted", k, flush=True)


def collect():
    bq = bq_client()
    ids = json.loads(IDS.read_text())
    while True:
        pending = 0
        for k, jid in ids.items():
            out = RES / f"{k}.json"
            if out.exists():
                continue
            r = bq.get(jid)
            if r.run_status not in TERM:
                pending += 1
                continue
            rec = {
                "job": k,
                "job_id": jid,
                "status": r.run_status,
                "cost": r.cost,
                "queue_time_ms": r.queue_time_ms,
                "run_time_ms": r.run_time_ms,
                "run_start": str(r.run_start),
                "error": r.error_message,
            }
            if r.run_status == "COMPLETED":
                rec["counts"] = r.get_counts()
            out.write_text(json.dumps(rec, indent=1))
            record_cost(jid, r.cost, device="quantum")
            print(k, r.run_status, r.cost, r.queue_time_ms, flush=True)
            if (r.cost or 0) > 1.08:
                print("STOP cost", flush=True)
                for k2, j2 in ids.items():
                    if not (RES / f"{k2}.json").exists():
                        bq.cancel(j2)
        if pending == 0:
            print("ALL_COLLECTED", flush=True)
            return
        time.sleep(60)


def bse(r):
    return math.sqrt(max(1 - r * r, 0)) / math.sqrt(N * 1000)


def analyze():
    w8 = json.loads((W8 / "analysis.json").read_text())
    rho = w8["readout"]["rho"]
    out = {"prereg_sha16": (HERE / "PREREG.sha16").read_text().strip(), "per_c": {}}
    rb = {}
    for c in (1, 2, 3, 4):
        f = RES / f"K{c}.json"
        if not f.exists() or json.loads(f.read_text())["status"] != "COMPLETED":
            continue
        j = json.loads(f.read_text())
        r, _, _ = retention(j["counts"], S)
        rb[c] = r
        r0 = w8["mirror"][str(c)]["r"]
        s = math.hypot(bse(r), bse(r0))
        out["per_c"][c] = {
            "r_barrier": r,
            "r_nobarrier": r0,
            "diff": r - r0,
            "z": (r - r0) / s,
            "survival": j["counts"].get(TARGET, 0) / 1000,
            "cost": j["cost"],
        }
    pc = out["per_c"]
    if len(pc) == 4:
        sup = (
            all(pc[c]["z"] < -3 for c in (3, 4))
            and (rb[4] - rb[1]) / math.hypot(bse(rb[4]), bse(rb[1])) < -3
        )
        nsup = all(abs(pc[c]["z"]) <= 3 for c in pc)
        out["H"] = "SUPPORTED" if sup else ("NOT SUPPORTED" if nsup else "MIXED")
        k = 0
        rows = []
        for row in w8["floquet"]:
            c = row["cycles"]
            A = math.sqrt(max(rb[c], 0) * rho)
            pred = row["M_exact"] * A
            pse = abs(row["M_exact"]) * 0.5 * A * math.hypot(bse(rb[c]) / rb[c], bse(rho) / rho)
            ag = abs(row["M"] - pred) <= 3 * math.hypot(row["M_se"], pse)
            k += ag
            rows.append({"c": c, "M_hw": row["M"], "M_pred_barrier": pred, "agree": ag})
        out["recalibration"] = {"rows": rows, "k_of_4": k}
    (RES / "analysis.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"validate": validate, "submit": submit, "collect": collect, "analyze": analyze}[sys.argv[1]]()
