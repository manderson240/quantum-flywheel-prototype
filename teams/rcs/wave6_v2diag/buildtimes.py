"""D2 follow-up (exploratory): read mps_build_time and survival for every 16q mirror job (original V2 + R + repeats)."""
import json, re, sys, glob
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]; sys.path.insert(0, str(ROOT))
import bluequbit
from kicked_ising_crosscheck import load_token
bq = bluequbit.init(load_token())
jobs = {}
for x in (4, 8, 16):
    d = json.load(open(HERE.parent / "wave6" / "results" / "cells" / f"V2_16q_d36_chi{x}.json")); jobs[f"V2orig_chi{x}"] = (d["job_id"], d["hits"] / d["shots"])
for f in sorted(glob.glob(str(HERE / "results" / "cells*" / "*.json"))):
    d = json.load(open(f))
    if d["id"].startswith(("R_", "F_chi16")):
        c = d["counts"] or {}; n = sum(c.values()) or 1
        jobs[d["id"]] = (d["job_id"], c.get("1110101001000101", 0) / n if d["id"].startswith("R_") else None)
out = {}
for k, (jid, surv) in jobs.items():
    j = bq.get(jid); rr = str(j.run_results)
    m = re.search(r"mps_build_time['\"]?\s*[:=]\s*([0-9.]+)", rr)
    out[k] = {"job": jid, "survival": surv, "mps_build_time_s": float(m[1]) if m else None, "run_time_ms": j.run_time_ms}
    print(k, out[k], flush=True)
(HERE / "results" / "buildtimes.json").write_text(json.dumps(out, indent=1))
