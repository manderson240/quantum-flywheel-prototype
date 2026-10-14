import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 20') if m < 20*2**20 else None
"""rcs wave 6 BlueQubit controller (implements PREREG.md §4-§5). Resumable: all state in results/state.json.
Run: BLUEQUBIT_ENV_FILE=... nohup nice -n 10 python controller.py >> results/controller.log 2>&1 &"""
import hashlib, json, math, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT))
import bluequbit
from kicked_ising_crosscheck import load_token
from cost_ledger import record_job, record_cost, ok_to_spend
from mirror_lib import derived_ops, to_qiskit, bitstring_key, n_cz
from own_mps import restrict
import plan

MAX_INFLIGHT, CAP_S, SUBMIT_UNTIL_H, CANCEL_AT_H = 3, 4 * 3600, 9.0, 9.5
RES = HERE / "results"; CELLS = RES / "cells"; CELLS.mkdir(parents=True, exist_ok=True)
STATE = RES / "state.json"; STOP = RES / "STOP_COST"
TERMINAL_OK = {"COMPLETED"}
TERMINAL_BAD = {"FAILED_VALIDATION", "FAILED", "CANCELED", "CANCELLED", "NOT_ENOUGH_FUNDS", "TERMINATED"}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def check_prereg():
    h = hashlib.sha256((HERE / "PREREG.md").read_bytes()).hexdigest()[:16]
    assert h == (HERE / "PREREG.sha16").read_text().strip(), f"PREREG hash mismatch {h}"
    return h


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"T0": None, "chi_top": None, "cells": {c["id"]: {**c, "status": "pending", "attempts": 0} for c in plan.bq_cells()}}


def save(st):
    tmp = STATE.with_suffix(".tmp"); tmp.write_text(json.dumps(st, indent=1)); tmp.replace(STATE)


def full_logical_ops():
    import re
    from qasm_angle import angle
    ops = []
    for ln in (ROOT / "refs/rcs-nighthawk-meta/data/circuits/full/d36_logical.qasm").read_text().splitlines():
        mm = re.match(r"(rx|rz)\((.+)\) q\[(\d+)\];", ln)
        if mm: ops.append((mm[1], angle(mm[2]), int(mm[3]))); continue
        mm = re.match(r"cz q\[(\d+)\], ?q\[(\d+)\];", ln)
        if mm: ops.append(("cz", int(mm[1]), int(mm[2])))
    assert n_cz(ops) == 918
    return ops


def ops_for(c):
    if c["group"] == "feasibility": return full_logical_ops()
    ops = derived_ops(c["inst"], c["d"])
    return restrict(ops, c["n"]) if c["n"] < 61 else ops


def done_61(st):
    return [c for c in st["cells"].values() if c["status"] == "done" and c["n"] == 61 and c.get("run_time_ms")]


def predict_s(st, chi, d):
    """PREREG §5: T = T_ref (chi/chi_ref)^alpha * CZ_d/CZ_ref; ref = completed 61q cell with largest chi (ties: largest d);
    alpha from the two largest distinct completed chi at d=36 (mean T per chi), floored at 2; default 3."""
    dn = done_61(st)
    if not dn: return None
    ref = max(dn, key=lambda c: (c["chi"], c["d"]))
    d36 = {}
    for c in dn:
        if c["d"] == 36: d36.setdefault(c["chi"], []).append(c["run_time_ms"] / 1000)
    ks = sorted(d36)
    alpha = 3.0
    if len(ks) >= 2:
        a, b = ks[-2], ks[-1]
        ta, tb = sum(d36[a]) / len(d36[a]), sum(d36[b]) / len(d36[b])
        alpha = max(2.0, math.log(tb / ta) / math.log(b / a))
    czr = n_cz(derived_ops(0, ref["d"])); czd = 918 if d == "full" else n_cz(derived_ops(0, d))
    return ref["run_time_ms"] / 1000 * (chi / ref["chi"]) ** alpha * czd / czr, alpha


def pilots_done(st):
    return all(st["cells"][k]["status"] in ("done", "notrun", "failed") for k in ("P1_i0_d36_chi128", "P2_i0_d36_chi256"))


def resolve_chi_top(st):
    """PREREG §5: largest chi in {2048,1024,512,256} whose three d36 inst cells (P2 = inst0 at 256) all completed."""
    d36 = [c for c in st["cells"].values() if c["n"] == 61 and c["d"] == 36 and c["group"] in ("pilot", "main") and c["input_idx"] == 0]
    if any(c["status"] in ("pending", "submitted") and isinstance(c["chi"], int) and c["chi"] >= 256 for c in d36):
        return None
    for x in (2048, 1024, 512, 256):
        if sum(1 for c in d36 if c["chi"] == x and c["status"] == "done") == 3:
            return x
    return 256


def process(bq, c, j):
    key = bitstring_key(c["bits"])
    top = j.top_128_results or {}
    counts = j.get_counts() or {}
    src = "top_128" if key in top else "get_counts"
    total = sum(counts.values()) if counts else None
    if key in top: hits, flag = top[key], "exact"
    elif key in counts: hits, flag = counts[key], "exact"
    elif len(counts) >= 100_000: hits, flag = min(counts.values()), "upper_bound_min_count_truncated_list"
    else: hits, flag = 0, "zero"
    hist = {}
    kx = int(key, 2)
    for s, v in counts.items():
        h = bin(int(s, 2) ^ kx).count("1"); hist[h] = hist.get(h, 0) + v
    rkey = key[::-1]
    out = {**{k: c[k] for k in ("id", "n", "inst", "d", "chi", "input_idx", "bits", "shots", "group")},
           "job_id": c["job_id"], "key": key, "hits": hits, "hits_flag": flag, "hits_source": src, "key_convention": "q0_leftmost",
           "reversed_key_hits": counts.get(rkey, top.get(rkey, 0)) if rkey != key else None,
           "n_distinct_returned": len(counts), "sum_counts_returned": total, "hamming_hist": {str(k): hist[k] for k in sorted(hist)},
           "top5": dict(sorted(counts.items(), key=lambda kv: -kv[1])[:5]),
           "run_time_ms": j.run_time_ms, "queue_time_ms": j.queue_time_ms, "cost": j.cost, "device": j.device,
           "device_options": str(j.device_options), "run_results": str(j.run_results), "n_cz": n_cz(ops_for(c)),
           "run_start": str(j.run_start), "run_end": str(j.run_end)}
    (CELLS / f"{c['id']}.json").write_text(json.dumps(out, indent=1))
    return out


LOCK = RES / "controller.lock"


def take_lock():
    if LOCK.exists() and time.time() - LOCK.stat().st_mtime < 150:
        sys.exit("another controller holds a fresh lock")
    LOCK.write_text(str(time.time()))


def main():
    check_prereg()
    take_lock()
    bq = bluequbit.init(load_token())
    st = load_state(); save(st)
    while True:
        if STOP.exists():
            log("STOP_COST present: no submissions"); break
        now = time.time()
        inflight = [c for c in st["cells"].values() if c["status"] == "submitted"]
        # ---- poll ----
        for c in inflight:
            try: j = bq.get(c["job_id"])
            except Exception as ex: log("get err", c["id"], str(ex)[:200]); continue
            s = str(j.run_status)
            if s in TERMINAL_OK:
                record_cost(c["job_id"], j.cost, device="mps.cpu", purpose=f"rcs wave6 {c['id']}")
                if j.cost is not None and float(j.cost) > 0:
                    STOP.write_text(f"{c['id']} {c['job_id']} cost {j.cost}\n"); log("COST > 0 -> STOP", c["id"], j.cost)
                out = process(bq, c, j)
                c.update(status="done", run_time_ms=j.run_time_ms, cost=j.cost, hits=out["hits"])
                try: build = float(dict(j.run_results or {}).get("mps_build_time"))
                except Exception: build = None
                c["mps_build_time"] = build
                if c["n"] == 61 and c["group"] not in ("validation", "feasibility") and build is not None and build < 10:  # D8
                    (CELLS / f"{c['id']}.json").replace(RES / "cells_collapsed" / f"{c['id']}.run{c.get('collapse_reruns', 0) + 1}.json")
                    c.setdefault("collapsed_jobs", []).append(c["job_id"])
                    if c.get("collapse_reruns", 0) < 1:
                        c.update(status="pending", attempts=0, collapse_reruns=c.get("collapse_reruns", 0) + 1)
                    else:
                        c.update(status="notrun", reason="D8: collapsed x2 (mps_build_time < 10 s)")
                    log("COLLAPSED", c["id"], "build", build, "->", c["status"])
                log("DONE", c["id"], "hits", out["hits"], "/", c["shots"], "rt_s", j.run_time_ms / 1000 if j.run_time_ms else None, "cost", j.cost)
            elif s in TERMINAL_BAD:
                record_cost(c["job_id"], j.cost, device="mps.cpu", purpose=f"rcs wave6 {c['id']} {s}")
                c.setdefault("errors", []).append(f"{s}: {str(j.error_message)[:300]}")
                runtime_term = "estimated runtime" in str(j.error_message).lower()  # D5: server runtime termination
                if runtime_term and not c.get("force_run") and not c.get("cancel_reason"):
                    c["force_run"] = True; c["status"] = "pending"; c["attempts"] -= 1
                else:
                    c["status"] = "pending" if c["attempts"] < 2 and not c.get("cancel_reason") else ("notrun" if c.get("cancel_reason") else "failed")
                log("BAD", c["id"], s, str(j.error_message)[:200], "->", c["status"])
            else:
                started = j.run_start.timestamp() if j.run_start is not None else None
                if started is None and s == "RUNNING":  # DEVIATIONS D4: run_start is None while RUNNING
                    c.setdefault("first_seen_running", now); started = c["first_seen_running"]
                if started is not None:
                    run_s = now - started
                    if run_s > CAP_S and not c.get("cancel_reason"):
                        c["cancel_reason"] = f"runtime cap {CAP_S}s exceeded"; bq.cancel(c["job_id"]); log("CANCEL cap", c["id"])
                if st["T0"] and now > st["T0"] + CANCEL_AT_H * 3600 and not c.get("cancel_reason"):
                    c["cancel_reason"] = "wall-clock deadline"; bq.cancel(c["job_id"]); log("CANCEL deadline", c["id"])
        save(st)
        # ---- submit ----
        inflight = [c for c in st["cells"].values() if c["status"] == "submitted"]
        past_submit = st["T0"] and now > st["T0"] + SUBMIT_UNTIL_H * 3600
        for c in st["cells"].values():
            if len(inflight) >= MAX_INFLIGHT or past_submit: break
            if c["status"] != "pending": continue
            if c["n"] == 61 and not c["id"].startswith("V3"):
                v3 = st["cells"]["V3_61q_d2_chi64"]
                if v3["status"] != "done": continue
                if v3.get("hits", 0) < 0.99 * v3["shots"]:
                    log("V3 endianness/pipeline control FAILED: main scan blocked"); STOP.write_text("V3 failed\n"); break
            if c["group"] in ("scan_top", "feasibility"):
                if st["chi_top"] is None:
                    st["chi_top"] = resolve_chi_top(st)
                    if st["chi_top"] is None: continue
                    log("chi_top resolved", st["chi_top"])
                c["chi"] = st["chi_top"]; c["shots"] = c["shots"] or plan.shots_for(c["chi"])
                if c["chi"] == 256 and c["group"] == "scan_top":  # identical to the scan_256 cells: run once, under the S256 id
                    c["status"] = "notrun"; c["reason"] = "chi_top=256 duplicates scan_256"; continue
            if c["n"] == 61 and c["group"] not in ("validation", "pilot") and (c["chi"] >= 512 or c["group"] in ("scan_top", "feasibility")):
                if not pilots_done(st): continue
                p = predict_s(st, c["chi"], "full" if c["group"] == "feasibility" else c["d"])
                if p is None: continue
                pred, alpha = p; c["predicted_s"], c["alpha"] = pred, alpha
                remaining = (st["T0"] + CANCEL_AT_H * 3600 - now) if st["T0"] else 1e9
                if pred > CAP_S or pred > remaining:
                    c["status"] = "notrun"; c["reason"] = f"predicted {pred:.0f}s (alpha {alpha:.2f}) > min(cap {CAP_S}, remaining {remaining:.0f})"
                    log("NOTRUN", c["id"], c["reason"]); continue
            if c["n"] == 61 and c["group"] != "validation" and c["shots"] == 200_000:  # D5 contingency (runtime only)
                slow = [x for x in st["cells"].values() if x["status"] == "done" and x["n"] == 61 and x["d"] == 36
                        and x["shots"] == 200_000 and (x.get("run_time_ms") or 0) > 7200e3]
                if slow: c["shots"] = 100_000; c["shots_note"] = "D5 contingency: first 2e5 d36 cell took > 2 h"
            if not ok_to_spend(0.0):
                log("ledger refuses"); STOP.write_text("ledger refused\n"); break
            circ = to_qiskit(ops_for(c), c["bits"], nq=c["n"])
            try:
                j = bq.run(circ, device="mps.cpu", shots=c["shots"], options={"mps_bond_dimension": c["chi"]},
                           asynchronous=True, job_name=f"rcs-w6-{c['id']}", force_run=bool(c.get("force_run")))
            except Exception as ex:
                msg = str(ex)
                if "LIMIT" in msg.upper() and "JOB" in msg.upper():
                    log("jobs limit, backing off", c["id"]); break
                if "runtime" in msg.lower() and not c.get("force_run"):
                    c["force_run"] = True; log("runtime rejection -> force_run next", c["id"], msg[:200]); continue
                c["attempts"] += 1; c.setdefault("errors", []).append(msg[:300])
                if c["attempts"] >= 2: c["status"] = "failed"
                log("submit err", c["id"], msg[:300]); continue
            c.update(status="submitted", job_id=j.job_id, submitted_at=time.time()); c["attempts"] += 1
            record_job(j.job_id, device="mps.cpu", purpose=f"rcs wave6 {c['id']}", chi=c["chi"], shots=c["shots"])
            if st["T0"] is None: st["T0"] = time.time()
            inflight.append(c); log("SUBMIT", c["id"], j.job_id, "chi", c["chi"], "shots", c["shots"]); save(st)
        save(st)
        live = [c for c in st["cells"].values() if c["status"] in ("pending", "submitted")]
        if not live: log("all cells terminal"); break
        if st["T0"] and now > st["T0"] + CANCEL_AT_H * 3600 and not [c for c in live if c["status"] == "submitted"]:
            for c in live: c["status"] = "notrun"; c["reason"] = "wall-clock deadline"
            save(st); log("deadline: remaining cells NOT RUN"); break
        LOCK.write_text(str(time.time()))
        time.sleep(60)


if __name__ == "__main__":
    main()
