"""POST-HOC: per-cycle |err| of S* (best dev schedule) vs B* (best constant) at each level, dev regime.
Re-simulates the two specs (deterministic engine) because run records store only aggregate metrics."""
import json, numpy as np
import runner as R, probe_engine as E
d = json.load(open("results/verdict.json")); tr = E.load_truth("dev_tracker"); out = {}
for lv, L in d["levels"].items():
    row = {}
    for name in ("B_star", "S_star"):
        sched, mode = R.realise(L[name]["spec"]); r = E.simulate("dev_tracker", sched, cutoff_mode=mode)
        row[name] = {c: round(float(np.mean([abs(r["vals"][f"{c}|{o}"] - tr[(c, o)]) for o in ("mag", "zzd2", "zzd3")])), 4)
                     for c in (4, 6, 8, 10, 13, 16)}
        row[name + "_cost"] = r["cost"]
    row["late_worse"] = all(row["S_star"][c] > row["B_star"][c] for c in (13, 16))
    out[lv] = row
json.dump(out, open("results/percycle_posthoc.json", "w"), indent=1); print(json.dumps(out, indent=1))
