"""POST-HOC DIAGNOSTIC (not pre-registered; cannot change any PREREG verdict).
The per-depth ln(F_mirror/F_patch) scatter exceeds shot+Birge noise (pre-registered WLS chi2_res ~29/4).
Constant-ratio model: weighted mean over depths, extra depth-level variance tau^2 by method of moments about the
weighted mean (sum w*(y-mu_w)^2 = n-1 with w = 1/(v+tau^2)). Reported for all six depths and leave-one-depth-out
(d20 is a suspect: patches only start to anticoncentrate ~24 cycles per the paper). All variants reported, none chosen.
Reads only results/depth_dependence.json (variances = shot + pre-registered Birge inflation)."""
import json, math
from pathlib import Path
R = Path(__file__).resolve().parent / "results"
dd = json.loads((R / "depth_dependence.json").read_text())


def re_model(y, v):
    def stat(t2):
        w = [1 / (vi + t2) for vi in v]; mu = sum(wi * yi for wi, yi in zip(w, y)) / sum(w)
        return sum(wi * (yi - mu) ** 2 for wi, yi in zip(w, y)), mu, math.sqrt(1 / sum(w))
    q0, mu0, se0 = stat(0.0)
    t2 = 0.0
    if q0 > len(y) - 1:
        lo, hi = 0.0, 1.0
        for _ in range(200):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if stat(mid)[0] > len(y) - 1 else (lo, mid)
        t2 = (lo + hi) / 2
    _, mu, se = stat(t2)
    return {"fixed_mean": mu0, "fixed_se": se0, "chi2_fixed": q0, "dof": len(y) - 1, "z_fixed": mu0 / se0,
            "tau_ln": math.sqrt(t2), "re_mean": mu, "re_se": se, "z_re": mu / se, "re_ratio": math.exp(mu)}


out = {"label": "POST-HOC DIAGNOSTIC; variances include pre-registered Birge inflation (B_m, B_Kpool)"}
for K in ("K3", "K4"):
    per = dd[K]["per_depth"]; ds = sorted(per, key=int)
    y = {d: per[d]["ln_ratio"] for d in ds}; v = {d: per[d]["se_infl"] ** 2 for d in ds}
    res = {}
    for drop in [None] + ds:
        keep = [d for d in ds if d != drop]
        m = re_model([y[d] for d in keep], [v[d] for d in keep])
        m["d36_z_with_tau"] = y["36"] / math.sqrt(v["36"] + m["tau_ln"] ** 2) if "36" in keep else None
        res["all" if drop is None else f"drop_d{drop}"] = m
    out[K] = res
(R / "posthoc_depth_scatter.json").write_text(json.dumps(out, indent=1))
for K in ("K3", "K4"):
    for k, m in out[K].items():
        print(K, f"{k:9s} fixed {m['fixed_mean']:+.3f}±{m['fixed_se']:.3f} chi2 {m['chi2_fixed']:.1f}/{m['dof']} "
              f"tau {m['tau_ln']:.3f} RE {m['re_mean']:+.3f}±{m['re_se']:.3f} z {m['z_re']:+.2f} ratio {m['re_ratio']:.3f} "
              f"d36z {m['d36_z_with_tau']}")
