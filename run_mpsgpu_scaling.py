"""PREREG_MPSGPU_ADDENDUM1.md runner: measure mps.gpu cost scaling (74q at chi=512, then 51q at chi=1024)."""
import json

import run_mpsgpu as R
from cost_ledger import CAP, spent

REF = {"A_74qx27c_chi512": 0.5435972771734179, "B_51qx30c_chi1024": 0.5383666430889399}
C1, T1 = R.state["V_51qx30c_chi512"]["cost"], R.state["V_51qx30c_chi512"]["wall_h"]
rate = C1 / T1
out = {}
for key, tag, chi, C, T in (("A_74qx27c_chi512", "74qx27c", 512, C1 * 74 / 51, T1 * 74 / 51),
                            ("B_51qx30c_chi1024", "51qx30c", 1024, C1 * 8, T1 * 8)):
    if R.state.get(key, {}).get("status") is None and (spent() + C > CAP or T > 7.0):
        R.state[key] = {"status": "NOT RUN", "reason": f"predicted ${C:.2f} / {T:.2f} h vs remaining ${CAP - spent():.2f}"}
        R.save(); print(key, "NOT RUN", flush=True); continue
    rec = R.run_step(key, tag, chi, rate_per_h=rate)
    if rec.get("value") is not None:
        rec["abs_diff_vs_cpu"] = abs(rec["value"] - REF[key]); rec["validated"] = rec["abs_diff_vs_cpu"] <= 1e-3
    rec.update(predicted_cost=C, predicted_h=T); R.save()
print("SCALING_DONE", json.dumps({k: {x: R.state[k].get(x) for x in ("status", "cost", "wall_h", "abs_diff_vs_cpu")}
                                   for k in REF if k in R.state}), flush=True)
