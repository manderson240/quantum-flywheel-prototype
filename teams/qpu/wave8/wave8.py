"""Wave 8 QPU runner (PREREG.md, sha16 in PREREG.sha16). Token read in-process, never printed.
python wave8.py exact            # local exact values + oracle19 provenance check ($0)
python wave8.py validate         # builder check on mps.cpu ($0)
python wave8.py run              # J0..J11 on device 'quantum' under the stop rules
python wave8.py analyze          # fixed analysis -> results/analysis.json
"""

import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np


HERE = Path(__file__).parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
assert (
    hashlib.sha256((HERE / "PREREG.md").read_bytes()).hexdigest()[:16]
    == (HERE / "PREREG.sha16").read_text().strip()
)
from cost_ledger import ok_to_spend, record_cost, record_job, spent
from floquet_oracle19 import circuit, lattice, pairs_at, three_colour
from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp, Statevector


RES = HERE / "results"
RES.mkdir(exist_ok=True)
N, EDGES = lattice()
LAYERS = three_colour(EDGES)
S = np.random.default_rng(20261005).integers(0, 2, N)
PAIRS2 = pairs_at(N, EDGES, 2)
TERM = {
    "COMPLETED",
    "FAILED_VALIDATION",
    "NOT_ENOUGH_FUNDS",
    "CANCELED",
    "TERMINATED",
    "JOBS_LIMIT_EXCEEDED",
}


def floquet(c):
    return circuit(N, LAYERS, c)


def jobs():
    j = {}
    q = QuantumCircuit(N)
    q.x(range(N))
    j["J0"] = ("readout", 0, q)
    for i, c in enumerate((1, 2, 3, 4), 1):
        j[f"J{i}"] = ("floquet", c, floquet(c))
    for i, c in enumerate((1, 2, 3, 4), 5):
        q = QuantumCircuit(N)
        for k in range(N):
            if S[k]:
                q.x(k)
        u = floquet(c)
        q.compose(u, inplace=True)
        q.compose(u.inverse(), inplace=True)
        j[f"J{i}"] = ("mirror", c, q)
    j["J9"] = ("floquet", 1, floquet(1))
    j["J10"] = ("floquet", 6, floquet(6))
    j["J11"] = ("floquet", 8, floquet(8))
    out = {}
    for k, (kind, c, q) in j.items():
        q = q.copy()
        q.measure_all()
        out[k] = (kind, c, q)
    return out


def zlabel(qs):
    s = ["I"] * N
    for q in qs:
        s[N - 1 - q] = "Z"
    return "".join(s)


def exact(c):
    sv = Statevector(floquet(c))
    m = float(
        np.real(
            sv.expectation_value(SparsePauliOp.from_list([(zlabel([q]), 1 / N) for q in range(N)]))
        )
    )
    zz = float(
        np.real(
            sv.expectation_value(
                SparsePauliOp.from_list([(zlabel(p), 1 / len(PAIRS2)) for p in PAIRS2])
            )
        )
    )
    return m, zz


def zs(counts):
    """Per-shot arrays: z[shot, q] (keys qubit-0-first, wave-6 D1)."""
    rows = []
    for k, v in counts.items():
        b = np.array([int(ch) for ch in k.replace(" ", "")])
        rows += [1 - 2 * b] * v
    return np.array(rows)


def score(counts):
    z = zs(counts)
    n = len(z)
    per = z.mean(1)
    m = per.mean()
    se = per.std(ddof=1) / math.sqrt(n)
    zz = np.mean([z[:, a] * z[:, b] for a, b in PAIRS2], axis=0)
    return dict(
        shots=n,
        M=float(m),
        M_se=float(se),
        ZZd2=float(zz.mean()),
        ZZd2_se=float(zz.std(ddof=1) / math.sqrt(n)),
    )


def retention(counts, target):
    z = zs(counts)
    t = 1 - 2 * np.asarray(target)
    agree = (z * t).mean(0)  # per qubit 1-2P(flip)
    return float(agree.mean()), float(agree.std(ddof=1) / math.sqrt(len(agree))), agree.tolist()


def cmd_exact():
    ref = {
        (r["cycles"], r["obs"]): r["exact"]
        for r in json.loads((ROOT / "results/floquet_oracle19.json").read_text())
    }
    out = {}
    for c in (1, 2, 3, 4, 6, 8):
        m, zz = exact(c)
        dm, dz = abs(m - ref[(c, "mag")]), abs(zz - ref[(c, "zzd2")])
        print(c, m, zz, "provenance diffs", dm, dz)
        assert dm < 1e-9 and dz < 1e-9, "STOP: circuit differs from oracle19"
        out[c] = {"M": m, "ZZd2": zz}
    (RES / "exact.json").write_text(json.dumps(out, indent=1))


def bq_client():
    import bluequbit
    from kicked_ising_crosscheck import load_token

    return bluequbit.init(load_token())


def wait(bq, jid, limit_s=4 * 3600):
    t0 = time.time()
    while True:
        r = bq.get(jid)
        if r.run_status in TERM:
            return r
        if time.time() - t0 > limit_s:
            return r
        time.sleep(20)


def cmd_validate():
    bq = bq_client()
    ex = json.loads((RES / "exact.json").read_text())
    rep = {}
    q = QuantumCircuit(N)
    q.x(0)
    q.measure_all()
    r = wait(
        bq,
        bq.run(
            q, device="mps.cpu", shots=1000, asynchronous=True, options={"mps_bond_dimension": 64}
        ).job_id,
    )
    keys = list(r.get_counts())
    rep["bitorder"] = keys
    ok = keys == ["1" + "0" * (N - 1)]
    for k, (kind, c, qc) in jobs().items():
        if k in ("J0", "J9", "J10", "J11"):
            continue
        r = wait(
            bq,
            bq.run(
                qc,
                device="mps.cpu",
                shots=1000,
                asynchronous=True,
                options={"mps_bond_dimension": 512},
            ).job_id,
        )
        cnt = r.get_counts()
        if kind == "floquet":
            s = score(cnt)
            z = (s["M"] - ex[str(c)]["M"]) / s["M_se"]
            rep[k] = {**s, "z_vs_exact": z}
            ok &= abs(z) <= 4
        else:
            tgt = "".join(map(str, S))
            h = cnt.get(tgt, 0)
            rep[k] = {"hits": h, "distinct": len(cnt)}
            ok &= h == 1000
        print(k, rep[k], flush=True)
    rep["pass"] = bool(ok)
    (RES / "validate_mpscpu.json").write_text(json.dumps(rep, indent=1))
    print("VALIDATE", ok)


def cmd_run():
    v = json.loads((RES / "validate_mpscpu.json").read_text())
    assert v["pass"], "STOP: builder not validated"
    bq = bq_client()
    fails = 0
    for k, (kind, c, qc) in jobs().items():
        out = RES / f"{k}.json"
        if out.exists() and json.loads(out.read_text()).get("status") == "COMPLETED":
            continue
        wave = sum((json.loads(p.read_text()).get("cost") or 0) for p in RES.glob("J*.json"))
        est = float(bq.estimate(qc, device="quantum").estimated_cost or 0)
        if not ok_to_spend(est) or wave + est > 9.0:
            print(f"STOP cap: wave ${wave:.2f} + est ${est:.2f}; ledger ${spent():.2f}")
            return
        j = bq.run(qc, device="quantum", shots=1000, asynchronous=True)
        record_job(j.job_id, device="quantum", purpose=f"wave8_qpu {k} {kind} c{c}", est_cost=est)
        r = wait(bq, j.job_id)
        record_cost(j.job_id, r.cost, device="quantum")
        rec = {
            "job": k,
            "kind": kind,
            "cycles": c,
            "job_id": j.job_id,
            "status": r.run_status,
            "cost": r.cost,
            "est_cost": est,
            "error": r.error_message,
            "device_options": str(r.device_options),
            "queue_time_ms": getattr(r, "queue_time_ms", None),
            "run_time_ms": getattr(r, "run_time_ms", None),
            "run_start": str(r.run_start),
            "run_end": str(r.run_end),
        }
        if r.run_status == "COMPLETED":
            rec["counts"] = r.get_counts()
        out.write_text(json.dumps(rec, indent=1))
        print(k, rec["status"], rec["cost"], rec["queue_time_ms"], rec["run_time_ms"], flush=True)
        if r.run_status == "NOT_ENOUGH_FUNDS":
            print("STOP funds")
            return
        if (r.cost or 0) > 1.08:
            print("STOP cost > 1.5x estimate")
            return
        fails = fails + 1 if r.run_status != "COMPLETED" else 0
        if fails >= 2:
            print("STOP two non-COMPLETED in a row")
            return


def cmd_analyze():
    ex = json.loads((RES / "exact.json").read_text())
    J = {p.stem: json.loads(p.read_text()) for p in RES.glob("J*.json")}
    ok = {k: v for k, v in J.items() if v.get("status") == "COMPLETED"}
    out = {
        "prereg_sha16": (HERE / "PREREG.sha16").read_text().strip(),
        "cost_total": sum(v.get("cost") or 0 for v in J.values()),
        "jobs": {
            k: {x: v.get(x) for x in ("job_id", "status", "cost", "queue_time_ms", "run_time_ms")}
            for k, v in J.items()
        },
    }
    rho = rho_se = None
    if "J0" in ok:
        rho, rho_se, _ = retention(ok["J0"]["counts"], [1] * N)
        out["readout"] = {
            "rho": rho,
            "rho_se": rho_se,
            "all_ones_fraction": ok["J0"]["counts"].get("1" * N, 0) / 1000,
        }
    mir = {}
    for k in ("J5", "J6", "J7", "J8"):
        if k in ok:
            c = ok[k]["cycles"]
            r, rse, per = retention(ok[k]["counts"], S)
            mir[c] = {
                "r": r,
                "r_se": rse,
                "survival": ok[k]["counts"].get("".join(map(str, S)), 0) / 1000,
            }
    out["mirror"] = mir
    rows = []
    for k in ("J1", "J2", "J3", "J4", "J10", "J11"):
        if k not in ok:
            continue
        c = ok[k]["cycles"]
        s = score(ok[k]["counts"])
        e = ex[str(c)]
        row = {
            "job": k,
            "cycles": c,
            **s,
            "M_exact": e["M"],
            "ZZd2_exact": e["ZZd2"],
            "delta": s["M"] - e["M"],
            "z": (s["M"] - e["M"]) / s["M_se"],
        }
        if rho is not None and c in mir and mir[c]["r"] > 0 and rho > 0:
            a = math.sqrt(mir[c]["r"] * rho)
            pred = e["M"] * a
            pse = (
                abs(e["M"])
                * 0.5
                * a
                * math.sqrt((mir[c]["r_se"] / mir[c]["r"]) ** 2 + (rho_se / rho) ** 2)
            )
            row.update(
                M_pred=pred,
                M_pred_se=pse,
                agree_3sigma=abs(s["M"] - pred) <= 3 * math.sqrt(s["M_se"] ** 2 + pse**2),
            )
        rows.append(row)
    out["floquet"] = rows
    if "J1" in ok and "J9" in ok:
        out["repeat_identical_counts"] = ok["J1"]["counts"] == ok["J9"]["counts"]
    hints = []
    if (
        out.get("readout", {}).get("all_ones_fraction") == 1.0
        and mir
        and all(m["survival"] == 1.0 for m in mir.values())
    ):
        hints.append("consistent with a noiseless simulator")
    if out.get("repeat_identical_counts"):
        hints.append("consistent with a seeded emulator")
    out["attribution_hints"] = hints
    (RES / "analysis.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in out if k != "jobs"}, indent=1))


if __name__ == "__main__":
    {"exact": cmd_exact, "validate": cmd_validate, "run": cmd_run, "analyze": cmd_analyze}[
        sys.argv[1]
    ]()
