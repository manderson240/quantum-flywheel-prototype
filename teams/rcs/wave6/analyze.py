import sys

m = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1])
sys.exit(f"MemAvailable {m / 2**20:.1f} GiB < 20") if m < 20 * 2**20 else None
"""rcs wave 6 analysis: implements PREREG.md §6-§9 literally. Reads results/cells/*.json, results/local/*.json,
results/state.json; writes results/analysis.json. No network."""
import hashlib
import json
import math
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "teams/rcs/wave3"))
from mirror_analysis import instance_survival, ivw  # noqa: E402  (main() not run)


h = hashlib.sha256((HERE / "PREREG.md").read_bytes()).hexdigest()[:16]
assert h == (HERE / "PREREG.sha16").read_text().strip()
DEPTHS = [8, 12, 16, 20, 24, 28, 32, 36]
RES = HERE / "results"

# ---- §6 hardware ----
mir = json.loads((ROOT / "refs/rcs-nighthawk-data/data/counts/mirror_survival.json").read_text())[
    "depths"
]
hw = {}
for d in DEPTHS:
    p, se, _ = instance_survival(mir[str(d)]["hits"], mir[str(d)]["shots"])
    F, s, c2 = ivw(p, se)
    hw[d] = {"F": F, "se": s, "B": max(1.0, math.sqrt(c2 / 2)), "per_instance": p.tolist()}

# ---- load cells ----
bq = [json.loads(f.read_text()) for f in sorted((RES / "cells").glob("*.json"))]
for r in bq:  # DEVIATIONS D1: cells processed before the key fix stored hits under the wrong (qubit-0-rightmost) key
    if r.get("key_convention") != "q0_leftmost":
        r["hits_old_key"], r["hits"], r["reversed_key_hits"] = r["hits"], r["reversed_key_hits"], r["hits"]
        r["hits_flag"] = "exact" if r["hits"] > 0 else "zero"; r["rescored_D1"] = True
loc = [json.loads(f.read_text()) for f in sorted((RES / "local").glob("L_*.json"))]
state = json.loads((RES / "state.json").read_text())


def pool_bq(rows):
    ps, ses, upper = [], [], False
    for r in rows:
        n = r["shots"]
        if r["hits_flag"] == "zero" or r["hits"] == 0:
            ps.append(3 / n)
            upper = True
        elif r["hits_flag"].startswith("upper_bound"):
            ps.append(r["hits"] / n)
            upper = True
        else:
            p = r["hits"] / n
            ps.append(p)
            ses.append(math.sqrt(max(p * (1 - p), 1e-12) / n))  # same variance floor as wave-3 instance_survival
    if upper:
        return {
            "F": float(np.mean(ps)),
            "se": 0.0,
            "B": 1.0,
            "k": len(rows),
            "mode": "upper_bound",
            "p_i": ps,
        }
    F, s, c2 = ivw(ps, ses)
    k = len(rows)
    B = max(1.0, math.sqrt(c2 / (k - 1))) if k >= 2 else 1.0
    return {"F": F, "se": s, "B": B, "k": k, "mode": "exact", "p_i": ps}


def pool_local(rows):
    v = [r["survival"] for r in rows]
    k = len(v)
    return {
        "F": float(np.mean(v)),
        "se": float(np.std(v, ddof=1) / math.sqrt(k)) if k >= 2 else 0.0,
        "B": 1.0,
        "k": k,
        "mode": "exact_own",
        "p_i": v,
    }


def z_exceed(d, P):
    den = math.sqrt((hw[d]["se"] * hw[d]["B"]) ** 2 + (P["se"] * P["B"]) ** 2)
    return (hw[d]["F"] - P["F"]) / den


def table(rows, pool):
    grid = {}
    for r in rows:
        grid.setdefault(r["chi"], {}).setdefault(r["d"], []).append(r)
    out = {}
    for chi, byd in sorted(grid.items()):
        out[chi] = {}
        for d, rs in sorted(byd.items()):
            P = pool(rs)
            z = z_exceed(d, P)
            out[chi][d] = {
                **P,
                "z": z,
                "exceeds": z > 3,
                "ratio_hw_over_mps": hw[d]["F"] / P["F"] if P["F"] > 0 else None,
                "instances": sorted(r["inst"] for r in rs),
            }
    return out


def dstar(byd):
    ds = sorted(byd)
    if not ds:
        return {"d_star": None, "note": "no data"}
    ex = [byd[d]["exceeds"] for d in ds]
    cands = [d for i, d in enumerate(ds) if all(ex[i:])]
    mono = all(ex[i] <= ex[i + 1] for i in range(len(ex) - 1))
    if not any(ex):
        return {"d_star": None, "note": "not reached within the scanned depths", "depths": ds}
    if not mono:
        return {"d_star": None, "note": "non-monotone", "pattern": dict(zip(ds, ex))}
    d0 = cands[0]
    return {"d_star": d0, "note": f"d*(chi) <= {d0}" if d0 == ds[0] else "", "depths": ds}


main = [
    r
    for r in bq
    if r["n"] == 61
    and r["group"] in ("pilot", "main", "scan_top", "scan_256")
    and r["input_idx"] == 0
]
Tb = table(main, pool_bq)
Tl = table(loc, pool_local)
res = {
    "prereg_sha16": h,
    "hardware": hw,
    "bq_table": Tb,
    "own_table": Tl,
    "bq_dstar": {chi: dstar(v) for chi, v in Tb.items()},
    "own_dstar": {chi: dstar(v) for chi, v in Tl.items()},
}


def verdict(T, label):
    d36 = {chi: v[36] for chi, v in T.items() if 36 in v}
    full = [chi for chi, v in d36.items() if v["k"] == 3]
    if not d36:
        return {"key": "NO_DATA", "instrument": label}
    chi_max = max(full) if full else max(d36)  # if no chi has all 3 instances, the largest chi run (flagged below)
    best = max(d36, key=lambda c: d36[c]["F"])
    B = d36[best]
    match = [c for c, v in d36.items() if v["mode"] != "upper_bound" and v["F"] >= hw[36]["F"]]
    ratio = hw[36]["F"] / B["F"]
    rstr = (">" if B["mode"] == "upper_bound" else "") + f"{ratio:.4g}"
    if match:
        key, chi = "MATCH", max(match)
        text = (
            f"on the paper's mirror metric a free chi={chi} MPS matches or exceeds the device at 36 cycles; the mirror "
            "benchmark does not by itself separate the device from this classical simulator; hardness then rests on the patch estimates."
        )
    elif B["z"] > 3:
        key = "EXCEED"
        text = f"the device exceeds a free chi <= {chi_max} MPS on its own mirror metric by factor {rstr} at 36 cycles"
    else:
        key = "INCONCLUSIVE"
        text = f"at 36 cycles the device and a free chi <= {chi_max} MPS are not separated at 3 sigma on the paper's mirror metric (ratio {rstr})."
    return {
        "key": key,
        "instrument": label,
        "best_chi": best,
        "chi_max": chi_max, "chi_max_has_all3": bool(full) and chi_max in full, "k_best": B["k"],
        "F_mps_best": B["F"],
        "mode_best": B["mode"],
        "z_best": B["z"],
        "d36_ratio": ratio,
        "d36_ratio_str": rstr,
        "F_hw36": hw[36]["F"],
        "wording": text,
    }


res["verdict_bq"] = verdict(Tb, "BlueQubit mps.cpu")
res["verdict_bq"]["invalid_D6"] = True  # DEVIATIONS D6: service removes U U^dagger before MPS truncation
res["verdict_bq"]["note"] = "literal PREREG scoring shown for completeness; VOID (D6). Headline = own-MPS (PREREG §9 substitute)."
res["verdict_own"] = verdict(Tl, "own-implementation MPS")
res["verdict_final"] = {**res["verdict_own"], "route": "PREREG §9 substitute (V2 inconsistent) + D6 (BlueQubit arm void)"}
for name in ("posthoc_diag_collapse", "posthoc_diag_buildtime", "posthoc_routing61", "posthoc_v2_routing"):
    f = RES / f"{name}.json"
    if f.exists():
        res.setdefault("posthoc_exploratory", {})[name] = json.loads(f.read_text())

# ---- §9 validation ----
V = {r["id"]: r for r in bq if r["group"] == "validation"}
vl = json.loads((RES / "local" / "V_local_16q.json").read_text())
val = {}
if "V3_61q_d2_chi64" in V:
    r = V["V3_61q_d2_chi64"]
    val["V3"] = {
        "survival": r["hits"] / r["shots"],
        "reversed_key_hits": r["reversed_key_hits"],
        "pass": r["hits"] >= 0.99 * r["shots"]
        and (r["reversed_key_hits"] or 0) <= 0.01 * r["shots"],
    }
if "V1_16q_d36_chi256" in V:
    r = V["V1_16q_d36_chi256"]
    val["V1"] = {
        "survival": r["hits"] / r["shots"],
        "own_statevector": vl["statevector_survival"],
        "pass": r["hits"] >= 0.99 * r["shots"] and abs(vl["statevector_survival"] - 1) < 1e-9,
    }
v2 = {}
for x in (4, 8, 16):
    k = f"V2_16q_d36_chi{x}"
    if k in V:
        s = V[k]["hits"] / V[k]["shots"]
        o = vl[f"chi{x}"]["survival"]
        v2[x] = {"bq": s, "bq_hits": V[k]["hits"], "own": o, "ratio": s / o if o else None}
if v2:
    ok = all(v["ratio"] is not None and 0.5 <= v["ratio"] <= 2 for v in v2.values()) and all(
        v2[a]["bq"] <= v2[b]["bq"] for a, b in zip(sorted(v2), sorted(v2)[1:])
    )
    val["V2"] = {"rows": v2, "consistent": ok and len(v2) == 3}
res["validation"] = val

# ---- bookkeeping ----
res["cells_status"] = {
    k: {
        "status": c["status"],
        "reason": c.get("reason") or c.get("cancel_reason"),
        "job_id": c.get("job_id"),
        "run_time_ms": c.get("run_time_ms"),
        "cost": c.get("cost"),
        "predicted_s": c.get("predicted_s"),
    }
    for k, c in state["cells"].items()
}
res["total_cost_reported"] = sum(float(c.get("cost") or 0) for c in state["cells"].values())
res["exploratory"] = {
    "input2": [
        {"inst": r["inst"], "hits": r["hits"], "shots": r["shots"]}
        for r in bq
        if r["group"] == "input2"
    ],
    "feasibility_full_logical": [
        {k: r[k] for k in ("job_id", "chi", "shots", "run_time_ms", "cost")}
        for r in bq
        if r["group"] == "feasibility"
    ],
}
(RES / "analysis.json").write_text(json.dumps(res, indent=1, default=float))
print(
    json.dumps(
        {"verdict_bq": res["verdict_bq"], "verdict_own": res["verdict_own"], "validation": val},
        indent=1,
        default=float,
    )
)
