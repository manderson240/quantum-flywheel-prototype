import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 20') if m < 20*2**20 else None
"""POST-HOC (not pre-registered, no verdict weight): M3's per-CZ constant c = ln(F4/F3)/(N3-N4) at each depth d20-40.
Pooled points + se from the authors' fidelity_vs_depth.json (shot se only); CZ means from manifest.json
(spot-checked 80/80 vs own counts in run_20260925_162129). Writes results/posthoc_<timestamp>/."""
import datetime, json, math, re, resource
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS, (1 << 30, 1 << 30))
ROOT = Path(__file__).resolve().parents[3]; META = ROOT / "refs/rcs-nighthawk-meta/data"
man = json.loads((META / "circuits/manifest.json").read_text())["circuits"]
cz = {}
for c in man:
    q = c.get("qasm3", c["file"]); mm = re.search(r"patched/(K[34])/d(\d+)/", q)
    if c["kind"] == "patched" and mm: cz.setdefault((mm.group(1), int(mm.group(2))), []).append(c["cz"])
pts = json.loads((META / "results/fidelity_vs_depth.json").read_text())["points"]
rows, w, cw = [], 0.0, 0.0
for d in (20, 24, 28, 32, 36, 40):
    p3, p4 = pts["3-patch"][str(d)], pts["4-patch"][str(d)]
    dn = sum(cz[("K3", d)]) / len(cz[("K3", d)]) - sum(cz[("K4", d)]) / len(cz[("K4", d)])
    c = math.log(p4["fidelity"] / p3["fidelity"]) / dn
    se = math.hypot(p3["se"] / p3["fidelity"], p4["se"] / p4["fidelity"]) / dn
    rows.append({"d": d, "ratio_F4_F3": p4["fidelity"] / p3["fidelity"], "dN": dn, "c": c, "se_c_shot": se}); w += 1 / se**2; cw += c / se**2
cbar = cw / w; chi2 = sum(((r["c"] - cbar) / r["se_c_shot"]) ** 2 for r in rows)
out = {"POST_HOC": True, "rows": rows, "c_weighted_mean": cbar, "chi2": chi2, "dof": len(rows) - 1,
       "c_min": min(r["c"] for r in rows), "c_max": max(r["c"] for r in rows),
       "c_sd_across_depth": (sum((r["c"] - sum(x["c"] for x in rows) / len(rows)) ** 2 for r in rows) / (len(rows) - 1)) ** 0.5,
       "mem_avail_gib": m / 2**20}
od = Path(__file__).resolve().parent / "results" / f"posthoc_{datetime.datetime.now():%Y%m%d_%H%M%S}"; od.mkdir(parents=True, exist_ok=False)
(od / "c_by_depth.json").write_text(json.dumps(out, indent=1))
for r in rows: print(r)
print({k: v for k, v in out.items() if k != "rows"}, od)
