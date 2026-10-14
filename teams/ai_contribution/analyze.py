"""Scores the headroom probe exactly as PREREG.md fixes it. Writes results/verdict.json."""
from __future__ import annotations
import json, statistics
from pathlib import Path
import runner as R

DEV_T, HO_T_MEAN, HO_T_EACH = 0.10, 0.05, 0.0
HO = ["ho_4.7_0.3", "ho_2.4_0.9"]
out = {"levels": {}, "instrument": {}}
allruns = {ph: R.load(ph) for ph in ("grid", "random", "hillclimb", "heldout")}
nfail = {ph: sum(r["failed"] for r in rs) for ph, rs in allruns.items()}
nviol = {ph: sum(r.get("violations", 0) > 0 for r in rs if not r["failed"]) for ph, rs in allruns.items()}
out["instrument"] = {"n_runs": {ph: len(rs) for ph, rs in allruns.items()}, "failed": nfail, "bond_violations": nviol}
# item-9 cutoff check: eps>=1e-4 at chi=64 must end with a smaller max bond than eps=0 at chi=64 (same regime)
cut_ok = True
for reg in ("dev_tracker", *HO):
    g = {(r["spec"]["chi"], r["spec"]["eps"]): r for r in allruns["grid"] if r["regime"] == reg and not r["failed"]}
    base = g.get((64, 0.0))
    for e in (1e-4, 3e-4, 1e-3, 3e-3, 1e-2):
        if base and (64, e) in g and not g[(64, e)]["maxbond"][-1] < base["maxbond"][-1]:
            cut_ok = False
out["instrument"]["cutoff_honoured"] = cut_ok
inst_fail = (not cut_ok) or any(nviol.values()) or any(
    nfail[ph] > 0.05 * max(1, len(allruns[ph])) for ph in nfail)

def ho_frontier(reg, cost, metric="med_log10_err"):
    ok = [r for r in allruns["grid"] if r["regime"] == reg and not r["failed"] and r["cost"] <= cost]
    return min(ok, key=lambda r: r[metric]) if ok else None

scored = passes_dev = passes_both = 0
for lv, (chi_k, C) in R.LEVELS.items():
    L = {}
    base_q = [r for r in allruns["grid"] if r["regime"] == "dev_tracker" and not r["failed"] and r["cost"] <= C]
    B = min(base_q, key=lambda r: r["med_log10_err"])
    L["baseline_qualifying"] = len(base_q)
    L["B_star"] = {"spec": B["spec"], "cost": B["cost"], "med_log10_err": B["med_log10_err"], "log10_mae": B["log10_mae"]}
    libdef = min([r for r in base_q if r["spec"]["eps"] == 0.0], key=lambda r: r["med_log10_err"])
    adapt = [r for r in base_q if r["spec"]["chi"] == 64 and r["spec"]["eps"] > 0]
    L["library_default_best"] = {"chi": libdef["spec"]["chi"], "med_log10_err": libdef["med_log10_err"]}
    L["adaptive_cap64_best"] = (min(adapt, key=lambda r: r["med_log10_err"])["med_log10_err"] if adapt else None)
    # equal budget: each seed's first Q_k in-budget evaluations (draw order) are scored
    rnd = {sd: sorted([r for r in allruns["random"] if r["spec"]["level"] == lv and r["spec"]["seed"] == sd
                and not r["failed"] and r["cost"] <= C], key=lambda r: r["spec"]["draw"])[:len(base_q)] for sd in R.SEEDS}
    L["random_qualifying"] = {sd: len(v) for sd, v in rnd.items()}
    L["random_best_per_seed"] = {sd: (min(r["med_log10_err"] for r in v) if v else None) for sd, v in rnd.items()}
    hc = [r for r in allruns["hillclimb"] if r["spec"]["level"] == lv and not r["failed"] and r["cost"] <= C]
    L["hillclimb_evals"] = sum(r["spec"]["level"] == lv for r in allruns["hillclimb"])
    L["hillclimb_best"] = min((r["med_log10_err"] for r in hc), default=None)
    # scored iff every random seed reached the baseline's qualifying count (hill-climb counts as its own arm)
    L["scored"] = all(n >= len(base_q) for n in L["random_qualifying"].values())
    S = R.dev_selected(lv, rnd_scored=[r for v in rnd.values() for r in v])
    L["S_star"] = {"spec": S["spec"], "cost": S["cost"], "med_log10_err": S["med_log10_err"], "log10_mae": S["log10_mae"],
                   "sched_chi": [c for c, _ in S["sched"]]}
    L["delta_dev"] = B["med_log10_err"] - S["med_log10_err"]
    L["delta_dev_log10_mae"] = B["log10_mae"] - S["log10_mae"]
    L["delta_dev_random_median_seed"] = B["med_log10_err"] - statistics.median(
        v for v in L["random_best_per_seed"].values() if v is not None)
    # held-out: primary = hindsight held-out constant frontier at the schedule's held-out cost
    ho = {}
    for reg in HO:
        sr = [r for r in allruns["heldout"] if r["regime"] == reg and r["spec"] == S["spec"] and not r["failed"]]
        if not sr: continue
        sr = sr[0]
        fr = ho_frontier(reg, sr["cost"])
        bt = [r for r in allruns["grid"] if r["regime"] == reg and r["spec"] == B["spec"]][0]
        ho[reg] = {"S_cost": sr["cost"], "S_med": sr["med_log10_err"],
                   "frontier_spec": fr["spec"] if fr else None, "frontier_med": fr["med_log10_err"] if fr else None,
                   "delta_primary": (fr["med_log10_err"] - sr["med_log10_err"]) if fr else None,
                   "B_transfer_cost": bt["cost"], "B_transfer_med": bt["med_log10_err"],
                   "delta_transfer_secondary": bt["med_log10_err"] - sr["med_log10_err"]}
    L["heldout"] = ho
    dp = [v["delta_primary"] for v in ho.values() if v["delta_primary"] is not None]
    L["dev_pass"] = L["delta_dev"] >= DEV_T
    L["ho_pass"] = len(dp) == 2 and statistics.mean(dp) >= HO_T_MEAN and min(dp) > HO_T_EACH
    if L["scored"]:
        scored += 1; passes_dev += L["dev_pass"]; passes_both += (L["dev_pass"] and L["ho_pass"])
    out["levels"][lv] = L

if inst_fail or scored < 2:
    verdict = "INCONCLUSIVE"
elif passes_both >= 2:
    verdict = "HEADROOM"
elif passes_dev >= 2:
    verdict = "DEV-ONLY (headroom does not transfer)"
else:
    verdict = "NO HEADROOM"
out.update(scored_levels=scored, dev_passes=passes_dev, both_passes=passes_both, instrument_fail=inst_fail, verdict=verdict)
(R.RES / "verdict.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: out[k] for k in ("scored_levels", "dev_passes", "both_passes", "instrument_fail", "verdict")}))
for lv, L in out["levels"].items():
    print(lv, "scored", L["scored"], "B*", L["B_star"]["spec"], round(L["B_star"]["med_log10_err"], 3),
          "S*", round(L["S_star"]["med_log10_err"], 3), "delta_dev", round(L["delta_dev"], 3),
          "ho", {k: (round(v["delta_primary"], 3) if v["delta_primary"] is not None else None) for k, v in L["heldout"].items()})
