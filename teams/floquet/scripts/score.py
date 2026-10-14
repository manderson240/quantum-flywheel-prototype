"""Score nlce_run.json by the frozen rules of PREREG.md (sha16 checked first)."""
import hashlib, json
R = "/home/mike-anderson/cohezion-labs/bluequbit-flywheel/"
T = R + "teams/floquet/"
h = hashlib.sha256(open(T + "PREREG.md", "rb").read()).hexdigest()[:16]
assert h == open(T + "PREREG.sha16").read().strip() == "8cc7cc4f71c11fdc", h
run = json.load(open(T + "results/nlce_run.json"))
CYC = [1, 2, 4, 8, 13, 16, 20, 27]
exact = {}
for n in (27, 33):
    for f in (f"floquet_patch{n}.json", f"floquet_patch{n}_27cyc.json"):
        for r in json.load(open(R + "results/" + f)):
            if r["obs"] == "mag" and r.get("exact") is not None: exact[(n, r["cycles"])] = r["exact"]
base = run["baseline_patch16_mag"]
pts, lines = [], []
for n in (27, 33):
    o = run["orders"][str(n)]; S = o["S_over_n"]; K = o["kmax"]
    for c in CYC:
        ex = exact.get((n, c))
        s16, s15 = S[K - 1][c - 1], S[K - 2][c - 1]
        e = None if ex is None else abs(s16 - ex)
        be = None if ex is None else abs(base[c - 1] - ex)
        d = abs(s16 - s15)
        pts.append(dict(n=n, c=c, exact=ex, nlce=s16, err=e, delta=d, base=base[c - 1], base_err=be,
                        series=[S[k][c - 1] for k in range(K)]))
late = [p for p in pts if p["c"] >= 16]
g1 = all(p["err"] is not None and p["err"] <= 0.02 for p in late)
mn = sum(p["err"] for p in late) / len(late); mb = sum(p["base_err"] for p in late) / len(late)
g2 = mn < mb
horizon = {}
for n in (27, 33):
    h_ = 0
    for c in CYC:
        p = next(q for q in pts if q["n"] == n and q["c"] == c)
        if p["err"] is not None and p["err"] <= 0.02: h_ = c
        else: break
    horizon[n] = h_
frac = sum(p["err"] is not None and p["err"] <= 0.02 for p in pts) / len(pts)
falseconf = [(p["n"], p["c"]) for p in pts if p["delta"] <= 0.01 and p["err"] is not None and p["err"] > 0.02]
calibrated = not any(c >= 4 for _, c in falseconf)
verdict = "PASS" if (g1 and g2) else "FAIL"
res = dict(prereg_sha16=h, kmax={n: run["orders"][str(n)]["kmax"] for n in (27, 33)}, failed_clusters=len(run["failed"]),
           gate_i_all_late_within_002=g1, gate_ii_mean_late_err=mn, baseline_mean_late_err=mb, gate_ii=g2,
           verdict=verdict, horizon_Cstar=horizon, frac_within_002=frac, frac_ge_90pct=frac >= 0.9,
           false_confidence_points=falseconf, diagnostic_calibrated=calibrated, points=pts)
json.dump(res, open(T + "results/nlce_score.json", "w"), indent=1)
for p in pts:
    print(f"n={p['n']} c={p['c']:2d} exact={p['exact']:.4f} nlce16={p['nlce']:+.4f} err={p['err']:.4f} "
          f"delta={p['delta']:.4f} base16={p['base']:.4f} base_err={p['base_err']:.4f}")
print({k: v for k, v in res.items() if k != "points"})
