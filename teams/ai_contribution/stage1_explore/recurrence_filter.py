"""EXPLORATORY (not pre-registered; reuses wave-2 data): would a 'keep a finding only if the other blind run of the
same copy flags the same place' filter cut false findings without losing plant hits? Lead 1 of
research/20261007-ai-verification-leads.md. Writes recurrence_filter.json."""
import json, re
from pathlib import Path
W2 = Path(__file__).resolve().parents[1] / "wave2"
s = json.load(open(W2 / "score.json"))
def locs(run):
    out = {}
    for ln in (W2 / "runs" / f"{run}.md").read_text().splitlines():
        m = re.match(r"\|\s*(\d+)\s*\|\s*([^|:]+):(\d+)", ln)
        if m: out[f"{run}#{m[1]}"] = (m[2].strip(), int(m[3]))
    return out
runs = {r["run"]: r for r in s["A"]}
res = {}
for tol in (0, 3, 10):
    tally = {"hit": [0, 0], "FP": [0, 0], "PREEXISTING": [0, 0], "UNRESOLVED": [0, 0], "miss": [0, 0]}
    placebo_fp = {}
    for name, r in runs.items():
        other = name[:-1] + ("2" if name.endswith("1") else "1")
        L, O = locs(name), locs(other)
        olocs = list(O.values())
        np_lab = {x[0]: x[1] for x in r.get("non_plant", [])}
        for fid, kind, _ in r["findings"]:
            if fid not in L: continue
            f, line = L[fid]
            rec = any(f == of and abs(line - ol) <= tol for of, ol in olocs)
            lab = "hit" if kind in ("AUTO_HIT", "ADJ_HIT") else "miss" if kind == "ADJ_MISS" else np_lab.get(fid, "UNRESOLVED")
            if lab == "DUPLICATE": continue
            tally.setdefault(lab, [0, 0]); tally[lab][0] += 1; tally[lab][1] += rec
            if name.startswith("C") and lab == "FP":
                placebo_fp.setdefault(name, [0, 0]); placebo_fp[name][0] += 1; placebo_fp[name][1] += rec
    res[f"tol{tol}"] = {"by_label_[total,kept]": tally, "placebo_FP_per_run_[total,kept]": placebo_fp}
(Path(__file__).parent / "recurrence_filter.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
