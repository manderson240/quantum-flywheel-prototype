import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 20') if m < 20*2**20 else None
"""rcs wave 7 analysis: implements PREREG.md §7-§9 literally. Reads results/state.json + results/cells/*.json,
writes results/analysis.json. No simulation, no network."""
import hashlib, json, math
from pathlib import Path
import numpy as np
import common as C

HERE = C.HERE; RES = HERE / "results"
assert hashlib.sha256((HERE / "PREREG.md").read_bytes()).hexdigest()[:16] == (HERE / "PREREG.sha16").read_text().strip()
sys.path.insert(0, str(C.ROOT / "teams/rcs/wave3"))
from mirror_analysis import instance_survival, ivw  # noqa: E402  (main() not run)

BQ_RATIO, BQ_LO, BQ_HI = 224.08, 88, 822     # verifier-corrected BlueQubit mps.cpu value (wave 6, O1)
mir = json.loads((C.ROOT / "refs/rcs-nighthawk-data/data/counts/mirror_survival.json").read_text())["depths"]
hw = {}
for d in (28, 36):
    p, se, _ = instance_survival(mir[str(d)]["hits"], mir[str(d)]["shots"])
    F, s, c2 = ivw(p, se)
    hw[d] = {"F": F, "se": s, "B": max(1.0, math.sqrt(c2 / 2))}

st = json.loads((RES / "state.json").read_text())
cells = {f.stem: json.loads(f.read_text()) for f in (RES / "cells").glob("*.json")}
sel = st.get("selected", [])
H = {k: r for k, r in cells.items() if k.startswith("H_") and st["cells"].get(k, {}).get("status") == "done"}


def surv(v, chi, d, i):
    r = H.get(f"H_{v}_c{chi}_d{d}_i{i}")
    return None if r is None else r["survival"]


def complete(v, chi, d):
    return all(surv(v, chi, d, i) is not None for i in range(3))


def best_of(d, cells_ok):
    """Per instance: max survival over all done H cells at depth d accepted by cells_ok(v, chi). Returns
    (list of 3 values or None, argmax list)."""
    B, arg = [], []
    for i in range(3):
        c = [(r["survival"], r["variant"], r["chi"]) for r in H.values()
             if r["d"] == d and r["inst"] == i and cells_ok(r["variant"], r["chi"])]
        if not c: return None, None
        b = max(c); B.append(b[0]); arg.append({"variant": b[1], "chi": b[2]})
    return B, arg


def margin_z(d, B):
    Fm = float(np.mean(B)); sm = float(np.std(B, ddof=1) / math.sqrt(3))
    h = hw[d]
    return {"F_mps_bestof_mean": Fm, "sigma_mps": sm, "per_instance_best": B, "margin": h["F"] / Fm,
            "z": (h["F"] - Fm) / math.sqrt((h["se"] * h["B"]) ** 2 + sm ** 2),
            "per_instance_margin": [hp / b for hp, b in zip([h["F"]] * 3, B)]}


out = {"prereg_sha16": (HERE / "PREREG.sha16").read_text().strip(), "hardware": hw,
       "controls": {k: st.get(k) for k in ("C3M_pass", "C12_pass", "C12_threads")},
       "control_cells": {k: {x: cells[k].get(x) for x in ("survival", "max_abs_amp_err", "wall_s", "peak_rss_mb")}
                         for k in cells if k[:2] in ("C1", "C2", "C3", "M_")},
       "pilot_score_mean_log10": st.get("pilot_score"), "selected": sel, "c1024_decision": st.get("c1024"),
       "cell_status": {k: c["status"] for k, c in st["cells"].items()},
       "table": {k: {x: r.get(x) for x in ("variant", "chi", "d", "inst", "survival", "wall_s", "peak_rss_mb",
                                             "max_bond", "n_updates", "sum_discarded", "svd_fallbacks", "threads")}
                 for k, r in sorted(H.items())}}

for d in (36, 28):
    res = {"ladder": {}}
    chi_max = None
    for X in C.LADDER:
        if sel and all(complete(v, x, d) for v in sel for x in C.LADDER if x <= X):
            chi_max = X
    for X in list(C.LADDER) + [1024]:
        B, arg = best_of(d, lambda v, c, X=X: c <= X)
        if B is None: continue
        e = margin_z(d, B); e["argmax"] = arg
        e["variants_complete_at_X"] = [v for v in sel if complete(v, X, d)]
        e["n_cells_used"] = sum(1 for r in H.values() if r["d"] == d and r["chi"] <= X)
        e["per_variant_mean_at_X"] = {v: (float(np.mean([surv(v, X, d, i) for i in range(3)]))
                                          if complete(v, X, d) else None) for v in sel}
        res["ladder"][X] = e
    res["chi_max"] = chi_max
    if chi_max:
        e = res["ladder"][chi_max]
        means = {v: m for v, m in e["per_variant_mean_at_X"].items() if m is not None}
        vb = max(means, key=means.get)
        res["headline"] = {"chi_max": chi_max, "N": len(sel), "margin": e["margin"], "z": e["z"],
                           "single_best_variant": vb, "single_best_variant_margin": hw[d]["F"] / means[vb]}
    # partial set above chi_max and the single-variant chi=1024 point
    res["above_chi_max"] = {X: {"margin": res["ladder"][X]["margin"], "z": res["ladder"][X]["z"],
                                "variants_complete": res["ladder"][X]["variants_complete_at_X"]}
                            for X in res["ladder"] if chi_max and X > chi_max}
    # exploratory power law (PREREG §9): log10 mean_i B_i(X) vs log10 X over completed ladder points
    pts = [(X, res["ladder"][X]["F_mps_bestof_mean"]) for X in C.LADDER if chi_max and X <= chi_max]
    if len(pts) >= 2:
        x = np.log10([p[0] for p in pts]); y = np.log10([p[1] for p in pts])
        b, a = np.polyfit(x, y, 1)
        res["exploratory_powerlaw"] = {"label": "EXPLORATORY, model-dependent extrapolation", "fit_range_chi":
                                       [pts[0][0], pts[-1][0]], "n_points": len(pts), "slope": float(b),
                                       "chi_star_match_device": float(10 ** ((math.log10(hw[d]["F"]) - a) / b))
                                       if b > 0 else None}
    out[f"d{d}"] = res

h36 = out["d36"]
zs = [e["z"] for e in h36["ladder"].values()]
if not zs:
    verdict = "NO_DATA"
elif any(z <= 3 for z in zs):
    verdict = "MATCH"
else:
    verdict = "EXCEED"
out["verdict"] = verdict
S1 = "Mirror survival of U·U† is a proxy; it is not the fidelity of sampling the 36-cycle RCS circuit."
S2 = ("The mirrors are derived from the released d36 instances; the shallower mirrors are truncations of the same "
      "instances, not the paper's separate depth-d draws.")
S3 = "We make no claim about the RCS advantage itself."
BQ = (f"BlueQubit mps.cpu at χ = 256 (instrument validation failed (V2); post-hoc build-time filter; 2 of 3 "
      f"instances) gives a ratio of {BQ_RATIO} (Poisson 95% {BQ_LO}–{BQ_HI})")
if "headline" in h36:
    hd = h36["headline"]
    ours = (f"the device exceeds the best of {hd['N']} own-implementation MPS variants (chain orderings × SWAP "
            f"routings) at χ ≤ {hd['chi_max']} by factor {hd['margin']:.4g} at 36 cycles"
            if verdict == "EXCEED" else
            f"an own-implementation MPS variant at χ ≤ {max(h36['ladder'])} reaches the device survival within "
            f"3σ at 36 cycles")
    extra = [f"plus {len(v['variants_complete'])} of them at χ = {X}: factor {v['margin']:.4g}"
             for X, v in h36["above_chi_max"].items()]
    lead_bq = verdict == "EXCEED" and hd["margin"] > BQ_RATIO
    out["wording"] = {"ours": ours, "above_chi_max": extra, "bq": BQ, "lead": "bq" if lead_bq else "ours",
                      "scope": [S1, S2, S3]}
(RES / "analysis.json").write_text(json.dumps(out, indent=1, default=str))
print("verdict", verdict, "headline", h36.get("headline"))
