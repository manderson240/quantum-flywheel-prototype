"""POST-HOC (not pre-registered): diagnose the two instrument flags that made the frozen verdict INCONCLUSIVE.
(a) bond 'violations': are they explained by per-gate semantics (a chi DECREASE only truncates bonds a gate touches)?
(b) cutoff check: at chi=64, is eps honoured (bond profile differs from eps=0) even when the final max bond is capped?"""
import json
import runner as R
out = {}
viol_explained, viol_total, unexplained = 0, 0, []
for ph in ("random", "hillclimb", "heldout"):
    for r in R.load(ph):
        if r["failed"] or r["violations"] == 0: continue
        chis = [c for c, _ in r["sched"]]
        viol_total += 1
        bad = []
        for li, mb in enumerate(r["maxbond"]):
            cyc = li // 3
            if mb > chis[cyc]:
                # explained iff the bond exceeds the current chi but not the running max of chi up to this cycle,
                # and the current chi is lower than an earlier cycle's (a decrease)
                if not (max(chis[:cyc + 1]) >= mb and chis[cyc] < max(chis[:cyc])):
                    bad.append((li, mb, chis[cyc]))
        # also: after the first full cycle following the last decrease, bonds must be <= chi
        if bad: unexplained.append({"phase": ph, "spec": r["spec"], "bad": bad[:5]})
        else: viol_explained += 1
out["violation_runs"] = viol_total
out["violation_runs_explained_by_chi_decrease"] = viol_explained
out["unexplained_examples"] = unexplained[:10]
# persistence: how many layers does an excess last after a decrease?
lags = []
for r in R.load("random"):
    chis = [c for c, _ in r["sched"]]
    run = 0
    for li, mb in enumerate(r["maxbond"]):
        if mb > chis[li // 3]: run += 1
        elif run: lags.append(run); run = 0
    if run: lags.append(run)
out["excess_run_lengths_layers"] = {k: lags.count(k) for k in sorted(set(lags))}
cut = {}
for reg in ("dev_tracker", "ho_4.7_0.3", "ho_2.4_0.9"):
    g = {(r["spec"]["chi"], r["spec"]["eps"]): r for r in R.load("grid") if r["regime"] == reg}
    base = g[(64, 0.0)]
    cut[reg] = {str(e): {"final_maxbond": g[(64, e)]["maxbond"][-1], "profile_differs": g[(64, e)]["maxbond"] != base["maxbond"],
                         "cost": g[(64, e)]["cost"], "cost_eps0": base["cost"]} for e in (1e-4, 3e-4, 1e-3, 3e-3, 1e-2)}
out["cutoff_at_chi64"] = cut
json.dump(out, open("results/diagnose_posthoc.json", "w"), indent=1)
print(json.dumps(out, indent=1))
