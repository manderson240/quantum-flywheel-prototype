"""Instrument checks BEFORE the prereg freeze (no truncated-run error values are computed or printed):
(1) exact reproduction: max_bond=None, cutoff=0 run must reproduce all 81 stored exact values (3 regimes).
(2) timing/cost only (errors NOT computed) for constant chi in {8,16,32,64} on the dev circuit."""
import json, sys
from pathlib import Path
import probe_engine as E
out = {"order": E.ORDER, "n": E.N, "n_edges": len(E.EDGES)}
for reg in E.REGIMES:
    tr = E.load_truth(reg)
    r = E.simulate(reg, [(None, 0.0)]*16, cutoff_mode="abs")
    diffs = [abs(r["vals"][f"{c}|{o}"] - tr[(c, o)]) for (c, o) in tr]
    out[f"exact_{reg}"] = {"max_abs_diff": max(diffs), "n": len(diffs), "wall_s": r["wall_s"], "cost": r["cost"]}
timing = {}
for chi in (8, 16, 32, 64):
    r = E.simulate("dev_tracker", [(chi, 1e-10)]*16, cutoff_mode="rel")
    timing[chi] = {"cost": r["cost"], "wall_s": r["wall_s"], "violations": r["violations"], "maxbond_end": r["maxbond"][-1]}
out["timing_dev_const_chi"] = timing
out["pass"] = all(out[f"exact_{g}"]["max_abs_diff"] < 1e-6 for g in E.REGIMES) and all(t["violations"] == 0 for t in timing.values())
Path("results/instrument_check.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1)); sys.exit(0 if out["pass"] else 1)
