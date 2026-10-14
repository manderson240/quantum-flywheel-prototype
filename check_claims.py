"""Recompute most numbers stated in report/report.html, SUBMISSION_KIT.md and FORM_ANSWERS.md from results/*.json, and assert
key phrases of those texts. It does not check meaning; text-to-number agreement rests on independent review.

Exit 0 only if every claim matches. Run after any edit to the report or the abstract.
"""

from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path


R = Path(__file__).parent / "results"
FAILS: list[str] = []


def check(name: str, cond: bool, val=None) -> None:
    print(("PASS " if cond else "FAIL ") + name + ("" if val is None else f"  -> {val}"))
    if not cond:
        FAILS.append(name)


def near(x: float, y: float, tol: float) -> bool:
    return abs(x - y) <= tol


# --- kicked Ising, 19q heavy-hex (§2) ---
ki = json.loads((R / "kicked_ising_hh3_s5.json").read_text())
e3 = max(abs(r["pp_0.001"] - r["exact_local"]) for r in ki)
e4 = max(abs(r["pp_0.0001"] - r["exact_local"]) for r in ki)
check("Pauli-path max err 5.8e-2 at δ=1e-3", near(e3, 0.058, 5e-4), e3)
check("Pauli-path max err 4.7e-3 at δ=1e-4", near(e4, 0.0047, 5e-5), e4)
check(
    "Pauli-path bias one-directional", all(r["pp_0.0001"] <= r["exact_local"] + 1e-12 for r in ki)
)
check(
    "θ=0 gives <M>=1 on every backend",
    all(
        near(ki[0][k], 1.0, 1e-9)
        for k in ki[0]
        if k.startswith(("pp_", "mps_", "exact")) and not k.endswith(("_s", "_cost"))
    ),
)

# --- ordering sweep (Fig. 1) ---
d = json.loads((R / "mps_ordering_hh3_s5.json").read_text())
runs = d["runs"]


def g(th: str, order: str, chi: int, key: str = "abs_err") -> float:
    return next(
        r[key] for r in runs if r["theta"] == th and r["order"] == order and r["chi"] == chi
    )


check(
    "bandwidth native 13 / rcm 3",
    d["bandwidth"]["native"] == 13 and d["bandwidth"]["rcm"] == 3,
    d["bandwidth"],
)
check("index-order χ=128 error 0.085 (π/4)", near(g("pi4", "native", 128), 0.085, 5e-4))
check("index-order χ=128 error 0.285 (3π/8)", near(g("3pi8", "native", 128), 0.285, 5e-4))
check("RCM χ=128 error 3.6e-4 (π/4)", near(g("pi4", "rcm", 128), 3.6e-4, 5e-6))
check("RCM χ=128 error 0.017 (3π/8)", near(g("3pi8", "rcm", 128), 0.017, 5e-4))
ratio = [g(t, "native", 128) / g(t, "rcm", 128) for t in ("pi4", "3pi8")]
check("improvement 235x and 17x", round(ratio[0]) == 235 and round(ratio[1]) == 17, ratio)
speed = [g(t, "native", 128, "wall_s") / g(t, "rcm", 128, "wall_s") for t in ("pi4", "3pi8")]
check("~4x faster (4-5x)", all(3.9 <= s <= 5.2 for s in speed), speed)
check(
    "wall 5 s vs 21 s (3π/8)",
    near(g("3pi8", "rcm", 128, "wall_s"), 5, 0.5)
    and near(g("3pi8", "native", 128, "wall_s"), 21, 0.5),
)
check(
    "RCM χ=16 beats index order χ=128",
    all(g(t, "rcm", 16) < g(t, "native", 128) for t in ("pi4", "3pi8")),
)
check(
    "random order no worse than index order at χ=128",
    all(g(t, "random", 128) <= g(t, "native", 128) for t in ("pi4", "3pi8")),
)

# --- OTOC(1) single seed (text) ---
o1 = json.loads((R / "otoc_echo_4x4_seed7.json").read_text())
c = {r["cycles"]: r for r in o1}
check("OTOC1 exactly 1 up to 6 cycles", all(near(c[k]["exact"], 1.0, 1e-9) for k in (2, 4, 6)))
check("OTOC1 ~0 at 8 cycles", near(c[8]["exact"], 0.0, 1e-3))
r10 = c[10]
check("OTOC1 c10 exact 0.302", near(r10["exact"], 0.302, 5e-4))
check(
    "OTOC1 c10 Pauli-path 0.000/0.195/0.304",
    [round(r10[k], 3) for k in ("pp_0.01", "pp_0.001", "pp_0.0001")] == [0.0, 0.195, 0.304],
)
check(
    "OTOC1 c10 MPS 0.038/0.714/0.302",
    [round(r10[k], 3) for k in ("mps_4", "mps_16", "mps_64")] == [0.038, 0.714, 0.302],
)

# --- OTOC^2, 3 seeds x 4 depths (§4, Result 2a/2b/2c) ---
o2 = json.loads((R / "otoc2_echo_4x4_seeds7-11-13.json").read_text())
check("12 OTOC2 instances", len(o2) == 12)
table = {
    "pp_0.01": (1, 0.345, 1.000),
    "pp_0.001": (2, 0.212, 1.000),
    "pp_0.0003": (5, 0.122, 1.000),
    "mps_4": (2, 0.158, 0.847),
    "mps_16": (3, 0.101, 0.399),
    "mps_64": (11, 0.004, 0.029),
}
for k, (within, mean, mx) in table.items():
    e = [abs(r[k] - r["exact"]) for r in o2]
    got = (sum(x < 0.01 for x in e), round(st.mean(e), 3), round(max(e), 3))
    check(f"table row {k}", got == (within, mean, mx), got)
z = sorted(round(r["exact"], 3) for r in o2 if r["pp_0.0003"] == 0.0)
check(
    "Pauli-path δ=3e-4 returns exactly 0 on 4/12; truths -1.000,-0.141,-0.130,-0.002",
    z == [-1.0, -0.141, -0.13, -0.002],
    z,
)
conv = [r for r in o2 if abs(r["pp_0.001"] - r["pp_0.0003"]) < 0.01]
wrong = [r for r in conv if abs(r["pp_0.0003"] - r["exact"]) >= 0.01]
check(
    "stopping rule: Pauli-path converged 7/12, 4 wrong",
    (len(conv), len(wrong)) == (7, 4),
    (len(conv), len(wrong)),
)
check(
    "one wrong case is 0.001 reported vs 0.045 true",
    any(near(r["pp_0.0003"], 0.001, 5e-4) and near(r["exact"], 0.045, 5e-4) for r in wrong),
)
mconv = [r for r in o2 if abs(r["mps_16"] - r["mps_64"]) < 0.01]
mwrong = [r for r in mconv if abs(r["mps_64"] - r["exact"]) >= 0.01]
check(
    "stopping rule: MPS converged 3/12, 0 wrong",
    (len(mconv), len(mwrong)) == (3, 0),
    (len(mconv), len(mwrong)),
)
s = next(r for r in o2 if r["seed"] == 11 and r["cycles"] == 9)
check(
    "seed 11 c9 MPS 0.001/0.566/0.438, exact 0.438",
    [round(s[k], 3) for k in ("mps_4", "mps_16", "mps_64", "exact")]
    == [0.001, 0.566, 0.438, 0.438],
)

# --- cost ---
costs = {
    r[k]
    for f in ("kicked_ising_hh3_s5.json",)
    for r in json.loads((R / f).read_text())
    for k in r
    if k.endswith("_cost")
}
costs |= {r["cost"] for r in runs} | {r[k] for r in o1 + o2 for k in r if k.endswith("_cost")}
check("every recorded job cost 0.0", costs == {0.0}, costs)

# --- IBM/Flatiron Quantum Advantage Tracker snapshot (2026-09-23) ---
ts = json.loads((R / "tracker_submissions_2026-09-23.json").read_text())
tm = json.loads((R / "tracker_models_2026-09-23.json").read_text())
ole = [x["observableValue"] for x in ts if x["circuit"] == "operator_loschmidt_echo_49x1296"]
check("OLE 49x1296 estimates span 0.62-0.94", round(min(ole), 2) == 0.62 and round(max(ole), 2) == 0.94, (min(ole), max(ole)))
zz = {x["method"][:5]: x for x in ts if x["circuit"] == "floquet_mixed_field_ising_zzd3_51qx16c"}
spp = next(x for x in zz.values() if x["method"].startswith("SPP"))
qes = next(x for x in zz.values() if x["method"].startswith("QESEM"))
check("Floquet ZZd3: SPP 0.183 on 65,536 Fugaku cores", round(spp["observableValue"], 3) == 0.183 and "65,536" in spp["computeResourcesClassical"])
check("Floquet ZZd3: QESEM 0.211 +/- 0.013, SPP outside", round(qes["observableValue"], 3) == 0.211
      and near(qes["errorBoundHigh"] - qes["observableValue"], 0.013, 5e-4) and spp["observableValue"] < qes["errorBoundLow"])
cnt = {}
for x in ts:
    cnt[x["circuit"]] = cnt.get(x["circuit"], 0) + 1
active = [i for g in (tm.values() if isinstance(tm, dict) else tm) for i in g["instances"] if i["category"] == "Active candidates"]
unch = [i["id"] for i in active if cnt.get(i["id"], 0) == 0]
check("six active candidates with no submission", len(unch) == 6, unch)
qrt = [x["runtimeQuantum"] / 60 for x in ts if x.get("runtimeQuantum", 0) > 1000]
check("tracker QPU runtimes 68.7-103.8 min per point", round(min(qrt), 1) == 68.7 and round(max(qrt), 1) == 103.8, (min(qrt), max(qrt)))
check("=> $6.6K-10K at $96/min", round(min(qrt) * 96 / 1000, 1) == 6.6 and round(max(qrt) * 96 / 1000) == 10)

# --- 19q exact oracle, tracker Floquet family ---
o19 = json.loads((R / "floquet_oracle19.json").read_text())
nz = [r for r in o19 if abs(r["exact"]) > 0.02]
for k, want_low in (("pau_0.001", 27), ("pau_0.0001", 25)):
    got = sum(1 for r in nz if r.get(k) is not None and abs(r[k]) < abs(r["exact"]) - 0.005)
    hi_ = sum(1 for r in nz if r.get(k) is not None and abs(r[k]) > abs(r["exact"]) + 0.005)
    check(f"19q {k}: magnitude too low {want_low}x, never too high", (got, hi_) == (want_low, 0), (got, hi_))
for k in ("mps_16", "mps_64"):
    hi_ = sum(1 for r in nz if r.get(k) is not None and abs(r[k]) > abs(r["exact"]) + 0.005)
    lo_ = sum(1 for r in nz if r.get(k) is not None and abs(r[k]) < abs(r["exact"]) - 0.005)
    check(f"19q {k}: magnitude never too low ({hi_} too high)", lo_ == 0 and hi_ == 26, (hi_, lo_))
inside = tot = 0
for pp, mp in (("pau_0.0001", "mps_64"), ("pau_0.001", "mps_16"), ("pau_0.001", "mps_64")):
    for r in o19:
        if r.get(pp) is None or r.get(mp) is None:
            continue
        tot += 1
        inside += min(r[pp], r[mp]) - 1e-9 <= r["exact"] <= max(r[pp], r[mp]) + 1e-9
check("19q setting-pair containments 80/80 (not quoted; distinct-point check below)", (inside, tot) == (80, 80), (inside, tot))
d27 = [min(r["pau_0.0001"], r["mps_64"]) <= r["exact"] <= max(r["pau_0.0001"], r["mps_64"]) for r in o19]
two = [r for r in o19 if r["pau_0.0001"] > 0.005]
check("19q exact inside bracket at 27/27 distinct points", sum(d27) == 27 == len(d27))
check("19q 21/21 two-sided points contained", len(two) == 21 and all(r["pau_0.0001"] <= r["exact"] <= r["mps_64"] for r in two))
check("19q one MPS job terminated by server", sum(1 for r in o19 if r.get("mps_16") is None) == 1)

n_mps = sum(1 for r in nz for k in ("mps_16", "mps_64") if r.get(k) is not None)
hi_mps = sum(1 for r in nz for k in ("mps_16", "mps_64") if r.get(k) is not None and abs(r[k]) > abs(r["exact"]) + 0.005)
check("19q MPS too high 52 of 53", (hi_mps, n_mps) == (52, 53), (hi_mps, n_mps))
n_pp = sum(1 for r in nz for k in ("pau_0.001", "pau_0.0001") if r.get(k) is not None)
check("19q Pauli-path non-trivial cases = 54", n_pp == 54, n_pp)

# --- 51q tracker circuit sweep ---
sw = json.loads((R / "tracker_floquet51_sweep.json").read_text())
check("51q sweep: 96 jobs, 0 failures, all $0", len(sw) == 96 and not any(r["error"] for r in sw) and {r["cost"] for r in sw} == {0.0})
V = {(r["obs"], r["cycles"], r["method"][:3], r["setting"]): r["value"] for r in sw}
check("51q cycle 1 mag: 0.4054 vs 0.4059", round(V[("mag", 1, "pau", 1e-4)], 4) == 0.4054 and round(V[("mag", 1, "mps", 256)], 4) == 0.4059)
pub = {("mag", 13): [0.396, 0.3891136, 0.40829123, 0.38356027], ("mag", 16): [0.3904, 0.4417984, 0.41110594, 0.38697176],
       ("zzd2", 13): [0.2916, 0.2798922, 0.255711], ("zzd2", 16): [0.2657, 0.30682474, 0.250253],
       ("zzd3", 13): [0.2278, 0.21647733, 0.1885839], ("zzd3", 16): [0.2111, 0.2519062, 0.18342936]}
readme = (Path(__file__).parent / "tracker" / "README.md").read_text()
check("published values transcribed from tracker README", all(repr(x) in readme or f"{x}" in readme for vals in pub.values() for x in vals))
inside = [V[(o, c, "pau", 1e-4)] <= x <= V[(o, c, "mps", 256)] for (o, c), vals in pub.items() for x in vals]
check("51q bracket consistent with all 20 published values", len(inside) == 20 and all(inside), (sum(inside), len(inside)))
one_sided = sum(len(vals) for (o, c), vals in pub.items() if V[(o, c, "pau", 1e-4)] < 0.005)
check("51q: 12 of 20 one-sided (zero lower edge), 8 two-sided", one_sided == 12, one_sided)
check("51q cycle 1 zzd2 0.1623-0.1685, zzd3 0.1549-0.1713",
      [round(V[(o, 1, m, s_)], 4) for o in ("zzd2", "zzd3") for m, s_ in (("pau", 1e-4), ("mps", 256))] == [0.1623, 0.1685, 0.1549, 0.1713])
check("51q Pauli-path negative value -0.0455 at cycle 2 (mag, δ=1e-3)", round(V[("mag", 2, "pau", 1e-3)], 4) == -0.0455)
w = [V[(o, c, "mps", 256)] - V[(o, c, "pau", 1e-4)] for (o, c) in pub]
check("51q bracket width 0.35-0.45", round(min(w), 2) == 0.35 and round(max(w), 2) == 0.45, (min(w), max(w)))
drop = [V[(o, 16, "mps", 64)] - V[(o, 16, "mps", 256)] for o in ("mag", "zzd2", "zzd3")]
check("chi 64->256 lowers upper edge 0.07-0.09 at cycle 16", all(0.065 <= d <= 0.09 for d in drop), drop)

# --- bracket stress tests (other regimes) ---
def _miss(tag):
    rr = json.loads((R / f"floquet_oracle19{tag}.json").read_text())
    ex = [max(0.0, min(r["pau_0.0001"], r["mps_64"]) - r["exact"], r["exact"] - max(r["pau_0.0001"], r["mps_64"])) for r in rr]
    med = sorted(abs(r["exact"]) for r in rr)[len(rr) // 2]
    return rr, ex, med
def _mag(tag):  # headline bracket rule on magnitudes (report §5): |pp| - 0.005 <= |exact| <= |mps64| + 0.005
    rr = json.loads((R / f"floquet_oracle19{tag}.json").read_text())
    miss = [max(abs(r["pau_0.0001"]) - 0.005 - abs(r["exact"]), abs(r["exact"]) - abs(r["mps_64"]) - 0.005) for r in rr]
    nt = [r for r in rr if abs(r["exact"]) > 0.02]
    return (sum(m <= 0 for m in miss), round(max(miss), 3), sum(abs(r["mps_64"]) < abs(r["exact"]) for r in nt), len(nt),
            round(sorted(abs(r["exact"]) for r in rr)[len(rr) // 2], 3))
check("(4.7,0.3): 26/27 in bracket (magnitude rule), one miss by 0.004, MPS never below truth (0/18)", _mag("_tx4.7_tz0.3_c5")[:4] == (26, 0.004, 0, 18), _mag("_tx4.7_tz0.3_c5"))
check("(2.4,0.9): 20/27 in bracket, misses up to 0.058, MPS below truth at 4/15, median |exact| 0.055", _mag("_tx2.4_tz0.9_c5") == (20, 0.058, 4, 15, 0.055), _mag("_tx2.4_tz0.9_c5"))
check("tracker params: 27/27 in bracket under the magnitude rule, MPS never below truth", _mag("")[0] == 27 and _mag("")[2] == 0, _mag(""))
check("tracker params median |exact| 0.289", round(_miss("")[2], 3) == 0.289)
check("stress-test colouring differs from default", json.loads((R / "floquet_oracle19_tx2.4_tz0.9_c5.json").read_text())[0]["colour_seed"] == 5)
check("stress tests: 216 jobs, 0 job errors", all(r.get(k_) is not None for tg in ("_tx4.7_tz0.3_c5", "_tx2.4_tz0.9_c5")
      for r in json.loads((R / f"floquet_oracle19{tg}.json").read_text()) for k_ in ("pau_0.001", "pau_0.0001", "mps_16", "mps_64")))

# --- pre-registered agent pilot (pilot/) ---
import hashlib, statistics as _st
sys.path.insert(0, str(Path(__file__).parent / "pilot"))
import run_pilot as _P, searchers as _S  # noqa: E402
_tab = _S.load_table()
check("pilot table 81 x 9, no failed runs", len(_tab) == 81 and all(len(e["runs"]) == 9 and all(r["value"] is not None for r in e["runs"].values()) for e in _tab.values()))
_pre = Path(__file__).parent / "pilot" / "PILOT_PREREG.md"
check("prereg + prompt hashes as frozen", hashlib.sha256(_pre.read_bytes()).hexdigest().startswith("c386183bbafd4c05")
      and hashlib.sha256((Path(__file__).parent / "pilot" / "agent_prompt.txt").read_bytes()).hexdigest().startswith("a975e23078dd79f9"))
_costs = _S.strategy_costs(_tab)
_nt = _P.nontrivial(_tab, 0.02)
_solv = sum(any(_costs[s] <= 40 and abs(e["runs"][s]["value"] - e["exact"]) < 0.02 for s in e["runs"]) for e in _nt.values())
check("pilot: 60 non-trivial, 48% solvable in budget", (len(_nt), _solv) == (60, 29), (len(_nt), _solv))
import contextlib, io
with contextlib.redirect_stdout(io.StringIO()):
    _rep, _recs = _P.score(_tab, 0.02, 40.0)
def _row(arm):
    p = _rep[arm]["pooled"]
    return (round(p["net"], 3), p["success"], p["certified_wrong"], p["abstain"])
check("pilot grid -0.500 12/42/6", _row("grid") == (-0.5, 12, 42, 6), _row("grid"))
check("pilot rule +0.117 8/1/51", _row("rule") == (0.117, 8, 1, 51), _row("rule"))
check("pilot local agent -0.039 0/5/173", _row("agent_lemonade_Qwen3.6-35B-A3B-MTP-GGUF") == (-0.039, 0, 5, 173))
check("pilot flash agent -0.167 42/61/66", _row("agent_ollama_deepseek-v4-flash:cloud") == (-0.167, 42, 61, 66))
check("pilot pro agent +0.039 15/3/157", _row("agent_ollama_deepseek-v4-pro:cloud") == (0.039, 15, 3, 157))
check("pilot hindsight best single -0.233 23/37/0", _row("ref_best_single") == (-0.233, 23, 37, 0))
_seeds = sorted(_P.summarize([r for r in _recs if r["arm"] == "random" and r["repeat"] == s_], _tab, 0.02)["net"] for s_ in range(50))
check("pilot random median seed -0.367", round(_st.median(_seeds), 3) == -0.367, _st.median(_seeds))
_ci = _P.boot_diff(_recs, _tab, 0.02, "agent_lemonade_Qwen3.6-35B-A3B-MTP-GGUF", "rule")
check("pilot CI local-rule [-0.281,-0.056]", (round(_ci[0], 3), round(_ci[1], 3)) == (-0.281, -0.056), _ci)
_ci = _P.boot_diff(_recs, _tab, 0.02, "agent_ollama_deepseek-v4-pro:cloud", "rule")
check("pilot CI pro-rule [-0.200,-0.005]", (round(_ci[0], 3), round(_ci[1], 3)) == (-0.2, -0.005), _ci)
_fl = [r for r in _recs if r["arm"] == "agent_ollama_deepseek-v4-flash:cloud" and r["outcome"][0] == "report"]
_both = [r for r in _fl if len({q.split("_")[0] for q in r["queries"]}) == 2]
def _dis(r):
    last = {}
    for s_ in r["queries"]:
        last[s_.split("_")[0]] = _tab[r["instance"]]["runs"][s_]["value"]
    return abs(last["pp"] - last["mps"]) >= 0.02
_d = [r for r in _both if _dis(r)]
_dr = sum(abs(r["outcome"][1] - _tab[r["instance"]]["exact"]) < 0.02 for r in _d)
check("flash: both families before 92/103 reports; 89 despite disagreement (38 right, 51 wrong)",
      (len(_both), len(_fl), len(_d), _dr, len(_d) - _dr) == (92, 103, 89, 38, 51), (len(_both), len(_fl), len(_d), _dr))

_cst = _S.strategy_costs(_tab)
def _gate(r):
    e = _tab[r["instance"]]; best = {}
    for s_ in r["queries"]:
        f_ = s_.split("_")[0]
        if f_ not in best or _cst[s_] > _cst[best[f_]]:
            best[f_] = s_
    if len(best) < 2:
        return 0
    a_, b_ = e["runs"][best["pp"]]["value"], e["runs"][best["mps"]]["value"]
    if abs(a_ - b_) >= 0.02:
        return 0
    return 1 if abs((a_ + b_) / 2 - e["exact"]) < 0.02 else -1
_g = []
for arm_ in ("agent_lemonade_Qwen3.6-35B-A3B-MTP-GGUF", "agent_ollama_deepseek-v4-flash:cloud", "agent_ollama_deepseek-v4-pro:cloud"):
    for rep_ in range(3):
        rs_ = [r for r in _recs if r["arm"] == arm_ and r["repeat"] == rep_]
        _g.append(sum(map(_gate, rs_)) / len(rs_))
check("post-hoc gated agents +0.050..+0.083, 9/9 positive, all below rule", len(_g) == 9 and round(min(_g), 3) == 0.05
      and round(max(_g), 3) == 0.083 and all(0 < x < 0.117 for x in _g), [round(x, 3) for x in _g])

# --- pilot 2 calibration (ordering headroom) ---
_cal = json.loads((Path(__file__).parent / "pilot2" / "calibration.json").read_text())
_gaps = []
for _lat in ("dev_heavyhex19", "test_square4x5"):
    for _chi in ("4", "8", "16"):
        o_ = _cal[_lat][_chi]
        vals = [o_["spectral"]["mean_log10_err"]] + [o_[f"cutwidthSA{i}"]["mean_log10_err"] for i in range(4)]
        _gaps.append(max(vals) - min(vals))
check("pilot2: best textbook orderings within 0.01-0.05 log10 at every chi, both lattices",
      all(g_ <= 0.05 for g_ in _gaps) and round(min(_gaps), 2) >= 0.01, [round(g_, 3) for g_ in _gaps])

# --- referee round 3 additions: tightening, extrapolation, job count ---
import math as _m, glob as _glob
_tr = [e for e in _tab.values() if e["config"] == "tracker" and abs(e["exact"]) >= 0.02]
_ex = {c_: _st.median(e["runs"][f"mps_{c_}"]["value"] - e["exact"] for e in _tr) for c_ in (16, 32, 64, 128)}
check("19q upper-edge excess 0.283/0.207/0.139/0.065 (chi 16..128)",
      [round(_ex[c_], 3) for c_ in (16, 32, 64, 128)] == [0.283, 0.207, 0.139, 0.065], _ex)
_xs = [_m.log2(c_) for c_ in (16, 32, 64, 128)]; _ys = [_m.log10(_ex[c_]) for c_ in (16, 32, 64, 128)]
_mx, _my = _st.mean(_xs), _st.mean(_ys)
_slope = sum((x - _mx) * (y - _my) for x, y in zip(_xs, _ys)) / sum((x - _mx) ** 2 for x in _xs)
check("x0.62 per doubling of chi", round(10 ** _slope, 2) == 0.62, 10 ** _slope)
_proj = []
for o_ in ("mag", "zzd2", "zzd3"):
    per = (V[(o_, 16, "mps", 64)] - V[(o_, 16, "mps", 256)]) / 2
    gap = V[(o_, 16, "mps", 256)] - {"mag": 0.3904, "zzd2": 0.2657, "zzd3": 0.2111}[o_]
    _proj.append(256 * 2 ** (gap / per))
check("naive extrapolation chi ~4,000-8,000 at cycle 16", all(3500 <= p_ <= 9000 for p_ in _proj), [round(p_) for p_ in _proj])
check("converged 51q mag at cycle 2 = +0.179 (chi 64 = chi 256)", round(V[("mag", 2, "mps", 256)], 3) == 0.179
      and abs(V[("mag", 2, "mps", 64)] - V[("mag", 2, "mps", 256)]) < 1e-3)
_jobs = (20 + 33 + 36 + 72 + len(sw) + sum(4 * len(json.loads((R / f_).read_text())) for f_ in
         ("floquet_oracle19.json", "floquet_oracle19_tx4.7_tz0.3_c5.json", "floquet_oracle19_tx2.4_tz0.9_c5.json"))
         + sum(1 for e in _tab.values() for r in e["runs"].values() if not r.get("reused"))
         + sum(len(json.loads(Path(f_).read_text())["mps"]) for f_ in _glob.glob(str(Path(__file__).parent / "pilot2" / "cache_*.json"))) + 6)
_patch_jobs = sum(sum(1 for k_ in ("exact", "pau_0.001", "pau_0.0001", "mps_64", "mps_256") if k_ + "_s" in r_)
                  for n_ in (27, 33) for r_ in json.loads((R / f"floquet_patch{n_}.json").read_text()))
_jobs += _patch_jobs + 8 + len(json.loads((R / "ole56.json").read_text())) + 1  # + 8 exact retries + OLE + 1 control
_hist = json.loads((R / "bq_job_history.json").read_text())  # account job history (tools/count_bq_jobs.py), independent of _jobs
_win = sum(v_ for d_, v_ in _hist["by_day"].items() if "2026-09-22" <= d_ <= "2026-09-27")
check("about 1,600 BlueQubit jobs (account history, Sep 22-27)", 1550 <= _win <= 1700
      and "about 1,600 BlueQubit jobs" in (Path(__file__).parent / "report" / "report.html").read_text(), (_win, "constructed", _jobs))

# --- arXiv:2607.24937 (the Floquet candidate's paper; BlueQubit co-authors): verbatim excerpt saved in refs/ ---
_HERE = Path(__file__).parent
_ref = (_HERE / "refs" / "arXiv2607.24937_excerpts.txt").read_text()
check("2607.24937 App K.4: MPS bond ladder up to chi=4096 at Nq=51 and 74",
      "χ ∈ { 512 , 1024 , 2048 , 4096 }" in _ref and "N q = 51" in _ref and "74" in _ref)
check("2607.24937 App K.4: device-index snake ordering", "physical-qubit index on the device, yielding a snake-like path" in _ref)
_rep = (_HERE / "report" / "report.html").read_text()
_frm = (_HERE / "FORM_ANSWERS.md").read_text()
check("report + form disclose BlueQubit co-authorship of the Floquet candidate",
      "co-authored by BlueQubit" in _rep and "co-authored by BlueQubit" in _frm)

# --- round-4 review fixes: ordering does not transfer to the target; angle convention; new prior art ---
import sys as _sys
_sys.path.insert(0, str(_HERE / "pilot2")); _sys.path.insert(0, str(_HERE))
import floquet_tracker as _ft, run_tracker as _rt, ordering_lab as _L
_lay, _ = _ft.readme_spec(); _E = sorted(set().union(*_lay))
check("tracker 51q labels already have RCM's cutwidth (4)",
      _L.cutwidth(list(range(_ft.N)), _E) == _L.cutwidth(_rt.rcm_perm(), _E) == 4)
_cal = json.loads((_HERE / "pilot2" / "calibration.json").read_text())["dev_heavyhex19"]
_gain = [10 ** (_cal[c_]["native"]["mean_log10_err"] - _cal[c_]["rcm"]["mean_log10_err"]) for c_ in ("4", "8", "16")]
check("Floquet 19q: RCM beats cutwidth-18 native by only 1.6-2.2x", all(1.55 <= g_ <= 2.25 for g_ in _gain)
      and _cal["4"]["native"]["cutwidth"] == 18, [round(g_, 2) for g_ in _gain])
import math as _m, re as _re
_qasm = (_HERE / "tracker" / "floquet_mixed_field_ising_mag_51qx16c.qasm").read_text()
_rx = float(_re.search(r"rx\(([0-9.]+)\)", _qasm)[1])
check("angle convention: tracker theta_x per cycle /3 = QASM rx = ~pi/6 (paper, per layer)",
      abs(_rx - 1.56567 / 3) < 1e-4 and abs(_rx - _m.pi / 6) / (_m.pi / 6) < 0.005, _rx)
check("abstract ~350 words", 330 <= len(_frm[_frm.find("## Project abstract"):_frm.find("## Related")].split()) - 12 <= 360)

# --- classically-verifiable tracker (snapshot 2026-09-23): RGS structure + candidate status ---
import collections as _co
def _rgs_census(fname):
    ls = [l.strip() for l in (_HERE / "tracker" / "cv" / fname).read_text().splitlines()
          if _re.match(r"^[a-z]", l.strip()) and not l.strip().startswith(("include", "qreg", "OPENQASM"))]
    last = _co.defaultdict(lambda: -1); ncl = []
    for i_, l_ in enumerate(ls):
        g_ = l_.split("(")[0].split()[0]; q_ = [int(x) for x in _re.findall(r"q\[(\d+)\]", l_)]
        if g_ == "cz":
            for q in q_: last[q] = i_
        if g_ in ("tdg", "t") or (g_ == "rz" and "pi/2" not in l_):
            ncl += [(q, i_) for q in q_]
    return sum(i_ > last[q] for q, i_ in ncl), sum(i_ <= last[q] for q, i_ in ncl)
check("RGS plain: all 140 non-Clifford ops after each qubit's last CZ (Clifford state, non-Clifford product basis)",
      _rgs_census("random_graph_sampling_nq70_depth70_checks27_basis_fstate.qasm") == (140, 0))
check("RGS doped: 468 T-type rotations, 406 in the bulk", _rgs_census("doped_random_graph_sampling_nq70_depth70_checks27_doped.qasm") == (62, 406))
_cvm = json.loads((R / "tracker_cv_models_2026-09-23.json").read_text())
_act = sorted(i["id"] for v in _cvm.values() for i in v["instances"] if i["category"] == "Active candidates")
check("CV tracker: 4 active (P11, P12, RGS, doped RGS)", len(_act) == 4 and any("P11" in a for a in _act) and any("doped" in a for a in _act), _act)

_man = (_HERE / "refs" / "arXiv2608.13110_abstract.txt").read_text()
check("2608.13110: 70q/468 T, width ceil(d/2), cost independent of one-qubit gates and T placement",
      "468" in _man and "independent of their values and of the number and placement of $T$ gates" in _man)
check("2608.13110: ~160 H100-hours = 37.3 min x 32 nodes x 8 GPUs", "37.3 minutes" in _man and "32 nodes" in _man
      and 150 <= 37.3 / 60 * 32 * 8 <= 165, round(37.3 / 60 * 256, 1))

_i151 = (_HERE / "refs" / "tracker_issue151_excerpt.txt").read_text()
check("issue #151: 1,726 published samples of the undoped instance; XEB criterion 0.092",
      "1726 bitstrings" in _i151 and "0.092" in _i151)

def _czseq(p):
    return [tuple(sorted(map(int, m.groups()))) for m in _re.finditer(r"^\s*cz\s+q\[(\d+)\],\s*q\[(\d+)\]", Path(p).read_text(), _re.M)]
_und = _czseq(_HERE / "tracker/cv/random_graph_sampling_nq70_depth70_checks27_basis_fstate.qasm")
_dop = _czseq(_HERE / "refs/zenodo21912448/data-for-doped-clifford-tn-simulation/circuit/nq70_depth70_checks27_doped.qasm")
check("undoped RGS has the identical ordered 2,415-CZ sequence as the doped circuit Manabe et al. contracted",
      _und == _dop and len(_und) == 2415)
_per = 37.3 * 60 * 256 / 2051
check("undoped cost estimate ~134 H100-h = 1,726 samples x measured ~280 GPU-s per amplitude batch",
      130 <= 1726 * _per / 3600 <= 138, round(1726 * _per / 3600, 1))

# --- RGS prototype: reproduce Manabe et al.'s log-XEB; validate our sweep reimplementation on circuit slices ---
import numpy as _np, math as _mt
_zb = _np.load(_HERE / "refs/zenodo21912448/data-for-doped-clifford-tn-simulation/data/amplitude_batches.npz", allow_pickle=False)
_p = _np.abs(_zb["raw_vectors"][_np.arange(len(_zb["selected_vector_indices"])), _zb["selected_vector_indices"]] * float(_zb["recovery_factor"])) ** 2
_lx = _np.euler_gamma + 70 * _mt.log(2) + _np.mean(_np.log(_p))
check("reproduced Manabe et al. log-XEB 0.3503 from their released amplitudes", abs(_lx - 0.3503365) < 1e-5, round(_lx, 6))
_sys.path.insert(0, str(_HERE / "rgs"))
from sweep import amplitude as _amp
from qiskit import QuantumCircuit as _QC
from qiskit.quantum_info import Statevector as _SV
import importlib.util as _iu
_spec = _iu.spec_from_file_location("_msv", _HERE / "rgs" / "mini_sweep_validate.py")
_src = (_HERE / "rgs" / "mini_sweep_validate.py").read_text().split("worst = 0.0")[0]
_ns = {"__file__": str(_HERE / "rgs" / "mini_sweep_validate.py")}; exec(_src, _ns)
_txt = _ns["sliced"](8, 28); _sv = _SV(_QC.from_qasm_str(_txt)).data; _i = int(_np.argmax(_np.abs(_sv)))
check("our spatial-sweep reimplementation matches exact statevector on an 8-qubit slice of IBM's undoped circuit",
      abs(_amp(_txt, format(_i, "08b")[::-1])[0] - _sv[_i]) / abs(_sv[_i]) < 1e-9)

# --- chi = 512 on the 51q Floquet circuit (collected 2026-09-24): the naive extrapolation does not hold ---
_c512 = {(r_["obs"], r_["cycles"]): r_["value"] for r_ in json.loads((R / "tracker_floquet51_chi512.json").read_text())}
check("chi=512: all six jobs completed", len(_c512) == 6 and all(v_ is not None for v_ in _c512.values()))
_fr, _cx = [], []
for (o_, cy_), v512 in _c512.items():
    v64, v256 = V[(o_, cy_, "mps", 64)], V[(o_, cy_, "mps", 256)]
    q_ = {("mag", 13): 0.396, ("mag", 16): 0.3904, ("zzd2", 13): 0.2916, ("zzd2", 16): 0.2657,
          ("zzd3", 13): 0.2278, ("zzd3", 16): 0.2111}[(o_, cy_)]
    _fr.append((v256 - v512) / ((v64 - v256) / 2))
    if cy_ == 16:
        _cx.append(512 * 2 ** ((v512 - q_) / (v256 - v512)))
check("chi 256->512 lowered the edge by only 71-76% of the per-doubling prediction", all(0.70 <= f_ <= 0.77 for f_ in _fr), [round(f_, 2) for f_ in _fr])
check("chi 256->512 drops are 0.025-0.030", all(0.024 <= V[(o_, cy_, "mps", 256)] - v_ <= 0.031 for (o_, cy_), v_ in _c512.items()))
check("re-extrapolation from the last doubling: chi ~14,000-24,000 at cycle 16", all(13000 <= x_ <= 25000 for x_ in _cx), [round(x_) for x_ in _cx])

# --- 2026-09-24: graph-state method for the undoped RGS instance (independent checks) ---
from qiskit.quantum_info import Clifford as _Cl
_lines = (_HERE / "tracker/cv/random_graph_sampling_nq70_depth70_checks27_basis_fstate.qasm").read_text().splitlines()
_cl = _Cl(_QC.from_qasm_str("\n".join(l for l in _lines if not (l.strip().startswith("tdg") or _re.match(r"\s*rz\(0\.955", l)))))
def _r2(M):
    M = M.copy().astype(_np.uint8); r = 0
    for c_ in range(M.shape[1]):
        pv = [i for i in range(r, M.shape[0]) if M[i, c_]]
        if not pv: continue
        M[[r, pv[0]]] = M[[pv[0], r]]
        for i in range(M.shape[0]):
            if i != r and M[i, c_]: M[i] ^= M[r]
        r += 1
    return r
_ent = [_r2(_cl.stab[:, list(range(c_)) + [70 + a for a in range(c_)]]) - c_ for c_ in range(1, 70)]
check("undoped RGS: max stabilizer entanglement across chain cuts = 32 bits (message 2^32 in chain order)", max(_ent) == 32, max(_ent))
from stabilizer_overlap import amplitude as _stab
_t9 = _ns["sliced"](9, 33); _s9 = _SV(_QC.from_qasm_str(_t9)).data; _j = int(_np.argmax(_np.abs(_s9)))
check("graph-state method matches exact statevector on a 9-qubit slice", abs(complex(_stab(_t9, format(_j, "09b")[::-1])[0]) - _s9[_j]) / abs(_s9[_j]) < 1e-9)

# --- 2026-09-24 pass: OLE 56x1488 pending dispute, ring runtimes (verbatim issue excerpts saved in refs/) ---
_iss = (_HERE / "refs" / "tracker_issues_20260924.txt").read_text()
check("OLE 56x1488 pending values 0.236 / 0.459 / 0.1867 (#199/#203/#204)", all(s_ in _iss for s_ in ("#199 0.236", "#203 0.459", "#204 0.1867")))
check("ring #245 quantum runtime 870 s vs #249 classical 66,325 s makespan", "#245 870" in _iss and "#249 66325" in _iss)

_ole = json.loads((R / "ole56.json").read_text())
_a0 = {r_["delta"]: r_ for r_ in _ole if r_["alpha"] == "0.00"}
check("OLE 56q alpha=0 echo: Pauli-path returns exactly 0 at delta 1e-3 and 1e-4, refuses 1e-5",
      _a0[1e-3].get("f_z") == 0.0 and _a0[1e-4].get("f_z") == 0.0 and "too small" in _a0[1e-5].get("err", ""))

# --- exactly scored T-placement scorer: anchors on IBM's ring circuits (Zenodo 22233383) ---
from injected_cutrank import parse_t_injected as _pti, ancilla_state as _anc, max_cutrank as _mcr
def _cr(path):
    qc_, n_, m_, tp_ = _pti(Path(path).read_text()); S_ = _anc(qc_, n_, m_)
    return min(_mcr(S_, o_)[0] for o_ in (sorted(range(m_), key=lambda j: (tp_[j][0], tp_[j][1])), list(range(m_))))
_ringcr = {t_: _cr(_HERE / f"refs/zenodo22233383/loop64_{t_}t.qasm") for t_ in (5, 75, 314)}
check("ring T-injected cut rank (fixed attacker): 5/75/314 T -> 2/29/38", _ringcr == {5: 2, 75: 29, 314: 38}, _ringcr)
_rl = (_HERE / "tracker/ring/dcs_nq64_depth73_checks12_t314.qasm").read_text().splitlines()
_rcl = _Cl(_QC.from_qasm_str("\n".join(l for l in _rl if not l.strip().startswith("t "))))
check("ring Clifford skeleton max cut rank = 31 (matches tracker #249)",
      max(_r2(_rcl.stab[:, list(range(c_)) + [64 + a for a in range(c_)]]) - c_ for c_ in range(1, 64)) == 31)

# --- pre-registered bracket check at 27/33 qubits (PATCH_PREREG.md, sha256 prefix ad33761e) ---
import hashlib as _hl
check("patch pre-registration hash-frozen", _hl.sha256((_HERE / "PATCH_PREREG.md").read_bytes()).hexdigest()[:16] == "ad33761e66880b43")
def _pb(nq):
    rs = json.loads((R / f"floquet_patch{nq}.json").read_text()); tot = inb = two = twin = 0; miss = 0
    for r_ in rs:
        e_, lo_, hi_ = r_.get("exact"), r_.get("pau_0.0001"), r_.get("mps_64")
        if None in (e_, lo_, hi_): miss += 1; continue
        tot += 1; ok_ = lo_ - 0.005 <= e_ <= hi_ + 0.005; inb += ok_
        if lo_ > 0.005: two += 1; twin += ok_
    return tot, inb, two, twin, miss
check("27q patch: 18/18 in bracket, two-sided 15/15", _pb(27) == (18, 18, 15, 15, 0), _pb(27))
check("33q patch: 15/15 in bracket, two-sided 10/10, 3 missing (server terminations)", _pb(33) == (15, 15, 10, 10, 3), _pb(33))
check("19+27+33q: all 60 tested points in the bracket", 27 + _pb(27)[1] + _pb(33)[1] == 60)

# --- pre-registered 27-cycle addendum (PATCH_PREREG_27CYC.md, sha256 prefix 037116030b0d9dc4) ---
check("27-cycle addendum hash-frozen", _hl.sha256((_HERE / "PATCH_PREREG_27CYC.md").read_bytes()).hexdigest()[:16] == "037116030b0d9dc4")
def _pb27(nq):
    rs = json.loads((R / f"floquet_patch{nq}_27cyc.json").read_text()); tot = inb = two = twin = miss = 0
    for r_ in rs:
        e_, lo_, hi_ = r_.get("exact"), r_.get("pau_0.0001"), r_.get("mps_64")
        if None in (e_, lo_, hi_): miss += 1; continue
        tot += 1; ok_ = lo_ - 0.005 <= e_ <= hi_ + 0.005; inb += ok_
        if lo_ > 0.005: two += 1; twin += ok_
    return tot, inb, two, twin, miss
check("27q x {20,27} cycles: 6/6 in bracket, two-sided 4/4", _pb27(27) == (6, 6, 4, 4, 0), _pb27(27))
check("33q x {20,27} cycles: 6/6 in bracket, two-sided 2/2", _pb27(33) == (6, 6, 2, 2, 0), _pb27(33))
check("27-cycle addendum supported (>=95% at each n)", all(_pb27(q)[1] / _pb27(q)[0] >= 0.95 for q in (27, 33)))
check("patch MPS chi=64 strictly above exact in every point with an exact value (heuristic upper edge, 45/45)",
      sum(r_["mps_64"] > r_["exact"] for f_ in ("floquet_patch27.json", "floquet_patch33.json", "floquet_patch27_27cyc.json",
          "floquet_patch33_27cyc.json") for r_ in json.loads((R / f_).read_text()) if r_.get("exact") is not None) == 45)
# --- large tracker instances (bracket = [pp_1e-4 - 0.005, mps_64 + 0.005], as pre-registered) ---
def _big(tag):
    return json.loads((R / f"floquet_big_{tag}.json").read_text())[0]
_b74, _b51 = _big("74qx27c"), _big("51qx30c")
check("74qx27c bracket values (pp 0.0858, mps64 0.6098, mps512 0.5436)",
      near(_b74["pau_0.0001"], 0.0858, 5e-4) and near(_b74["mps_64"], 0.6098, 5e-4) and near(_b74["mps_512"], 0.5436, 5e-4))
check("74qx27c bracket contains QESEM 0.365 -> 'consistent with'", _b74["pau_0.0001"] - 0.005 <= 0.365 <= _b74["mps_64"] + 0.005)
check("51qx30c bracket values (pp 0.1040, mps64 0.6355, mps512 0.5583)",
      near(_b51["pau_0.0001"], 0.1040, 5e-4) and near(_b51["mps_64"], 0.6355, 5e-4) and near(_b51["mps_512"], 0.5583, 5e-4))
check("51qx30c interval contains QESEM 0.366, SPP 0.350/0.385, M_th 0.410, PEPS-BP 0.541 (descriptive; 30c beyond pre-registered depth)",
      all(_b51["pau_0.0001"] - 0.005 <= v_ <= _b51["mps_64"] + 0.005 for v_ in (0.366, 0.350, 0.385, 0.410, 0.541)))
check("MPS upper edge decreases monotonically with chi (64>256>512) on both large instances",
      all(b_["mps_64"] > b_["mps_256"] > b_["mps_512"] for b_ in (_b74, _b51)))
_xc = json.loads((R / "xcheck_local27.json").read_text())
check("independent local simulator reproduces BlueQubit exact at all 24 27q points to 2e-5", len(_xc["points"]) == 24 and _xc["max_abs_diff"] < 2e-5, _xc["max_abs_diff"])
def _agent_counts():  # pilot table incl. invalid actions (scored -1), non-trivial instances only
    import collections as _co
    T_ = json.loads((_HERE / "pilot" / "table.json").read_text()); out = {}
    for f_ in ("agents_lemonade_tol0.02_B40.0.jsonl", "agents_ollama_tol0.02_B40.0.jsonl"):
        for l_ in (_HERE / "pilot" / "results" / f_).read_text().splitlines():
            r_ = json.loads(l_); ex_ = T_[r_["instance"]]["exact"]
            if not l_.strip() or r_["arm"].startswith("blind") or abs(ex_) < 0.02: continue
            o_ = r_["outcome"]; k_ = o_[0] if isinstance(o_, list) else o_
            k_ = ("right" if abs(o_[1] - ex_) <= 0.02 else "wrong") if k_ == "report" else k_
            out.setdefault(r_["arm"].split("_")[-1], _co.Counter())[k_] += 1
    return {a: (c_["right"], c_["wrong"], c_["abstain"], c_["invalid"]) for a, c_ in out.items()}
check("pilot table rows incl. invalid actions: Qwen 0/5/173/2, Flash 42/61/66/11, Pro 15/3/157/5",
      _agent_counts() == {"Qwen3.6-35B-A3B-MTP-GGUF": (0, 5, 173, 2), "deepseek-v4-flash:cloud": (42, 61, 66, 11), "deepseek-v4-pro:cloud": (15, 3, 157, 5)}, _agent_counts())
def _tight(f_):
    import statistics as _st
    rs_ = [r for r in json.loads((R / f_).read_text()) if r.get("exact") is not None and r.get("mps_256") is not None]
    return round(1 - _st.median(r["mps_256"] - r["exact"] for r in rs_) / _st.median(r["mps_64"] - r["exact"] for r in rs_), 2), sum(r["mps_256"] > r["exact"] for r in rs_), len(rs_)
check("chi 64->256 removes 83% of median MPS excess at 27q<=16c, 39% at 33q 20-27c; chi256 above truth 45/45",
      _tight("floquet_patch27.json")[0] == 0.83 and _tight("floquet_patch33.json")[0] == 0.67 and _tight("floquet_patch33_27cyc.json")[0] == 0.39
      and sum(_tight(f_)[1] for f_ in ("floquet_patch27.json", "floquet_patch33.json", "floquet_patch27_27cyc.json", "floquet_patch33_27cyc.json")) == 45,
      [_tight(f_) for f_ in ("floquet_patch27.json", "floquet_patch33_27cyc.json")])
check("51qx30c chi=1024 upper edge 0.5384; step 0.0212 -> 0.0200; 0.0026 below PEPS-BP 0.541 (gap not interpreted)",
      near(_b51["mps_1024"], 0.5384, 5e-4) and round(_b51["mps_512"] - _b51["mps_1024"], 3) == 0.020
      and round(0.541 - _b51["mps_1024"], 4) == 0.0026, _b51.get("mps_1024"))
_p33 = json.loads((R / "floquet_patch33.json").read_text())
_two33 = [r_ for r_ in _p33 if (r_.get("pau_0.0001") or 0) > 0.005]
check("33q <=16c conservative (missing = failures): 15/18, two-sided 10/13 -> below 95%, hypothesis not supported",
      sum(r_.get("exact") is not None and r_["pau_0.0001"] - 0.005 <= r_["exact"] <= r_["mps_64"] + 0.005 for r_ in _p33) == 15 and len(_p33) == 18
      and len(_two33) == 13 and sum(r_.get("exact") is not None and r_["pau_0.0001"] - 0.005 <= r_["exact"] <= r_["mps_64"] + 0.005 for r_ in _two33) == 10)
_lg = json.loads((_HERE / "graph" / "lessons.json").read_text())
_D44 = [x_ for x_ in _lg["defects"] if int(x_["id"][1:]) <= 45]  # pinned to the set the application cites (D01-D45)
check("AI verification: 45 defects (34 application + 11 team), 41 caught by AI verifiers (35 verifier agents + 6 only review panel), author checker caught 0 (missed 4), 7 fix-introduced, 3 refuted FPs",
      len(_D44) == 45 and sum(int(x_["id"][1:]) > 34 for x_ in _D44) == 11
      and sum(any(c_.startswith(("verifier", "council")) for c_ in x_["caught_by"]) for x_ in _D44) == 41
      and sum(any(c_.startswith("verifier") for c_ in x_["caught_by"]) for x_ in _D44) == 35
      and sum("check_claims" in x_["caught_by"] for x_ in _D44) == 0 and sum("check_claims" in x_["missed_by"] for x_ in _D44) == 4
      and sum(x_["class"] == "fix_introduced_defect" for x_ in _D44) == 7 and sum(x_["check"] in ("council6", "verifier_r4") for x_ in _lg["reviewer_false_positives"]) == 3)  # A9: pinned to the D01-D45 window (council_6 + round 4)
check("wave 1: 11 verified defects over 3 deliverables = 3.7 per deliverable",
      sum(v_["verified_defects"] for k_, v_ in _lg["wave_metrics"]["wave1"].items() if isinstance(v_, dict)) == 11
      and round(11 / 3, 1) == 3.7)
_rcs = json.loads((_HERE / "teams" / "rcs" / "wave2" / "results" / "comparison.json").read_text())["summary"]
check("RCS: BlueQubit d36 patch-XEB reproduced 32/32 exact, max relative error <= 5e-14 (prereg 9102a014cee43c2c)",
      _rcs["verdict"] == "REPRODUCED" and _rcs["tally"]["EXACT"] == 32 and _rcs["prereg_sha16"] == "9102a014cee43c2c"
      and max(_rcs["max_rho"]["fidelity"], _rcs["max_rho"]["se"], _rcs["max_rho_patch_fidelity"]) <= 5e-14)
_g36 = json.loads((_HERE / "teams" / "rcs" / "wave3" / "results" / "gap_d36.json").read_text())["mirror_vs_3patch"]
_rep3 = json.loads((_HERE / "teams" / "rcs" / "wave3" / "results" / "reproduction.json").read_text())
check("RCS mirror reproduced; d36 mirror 2.24e-3 vs 3-patch 1.84e-3 differ by 4.3 sigma with both errors inflated",
      _rep3["verdict"] == "REPRODUCED" and round(_g36["F_mirror"], 5) == 0.00224 and round(_g36["F_patch"], 5) == 0.00184
      and round(_g36["z"]["c_both_inflated"], 1) == 4.3
      and round(json.loads((_HERE / "teams" / "rcs" / "wave3" / "results" / "gap_d36.json").read_text())["mirror_vs_4patch"]["z"]["c_both_inflated"], 1) == 2.8)
check("large-instance mps.cpu/Pauli-path legacy result files: spend $0.00 (mps.gpu spend is checked separately)", sum(v_ or 0 for b_ in (_b74, _b51) for k_, v_ in b_.items() if k_.endswith("_cost")) == 0)


# --- instrument check (iii), rerun 2026-09-27 (results/instrument_chi512.json) ---
_ic = json.loads((R / "instrument_chi512.json").read_text())
check("chi=512 MPS matches 19q statevector within 5e-8 at 3 angles, repeats bit-identical",
      len(_ic["rows"]) == 3 and _ic["max_abs_diff"] < 5e-8 and _ic["all_repeats_identical"]
      and "within 5×10<sup>−8</sup> at three angles" in _rep, _ic["max_abs_diff"])

# --- planted-defect benchmark (teams/ai_contribution/wave2/score.json, PREREG 04570ab6a4efeb79) ---
_pb = json.loads((_HERE / "teams" / "ai_contribution" / "wave2" / "score.json").read_text())["summary"]
_rep = (_HERE / "report" / "report.html").read_text(); _frm = (_HERE / "FORM_ANSWERS.md").read_text()
check("benchmark: verifiers 51/72 (CI 52-91%), 19/22 distinct, checker 3/36, qualifiers 0/12, placebo FP 11-14/run",
      _pb["A_hits"] == 51 and _pb["A_plant_runs"] == 72 and _pb["A_recall_cluster_bootstrap95"] == [0.524, 0.912]
      and _pb["A_unique_plants_caught_any_run"] == "19/22" and _pb["B_hits"] == 3 and _pb["B_plants"] == 36
      and _pb["A_by_cls"]["dropped_qualifier"] == "0/12"
      and _pb["placebo_FP_per_run_lower"] == 11.0 and _pb["placebo_FP_per_run_upper"] == 14.0
      and "caught 51 of 72 (95% CI 52–91%; 19 of 22 distinct defects)" in _rep and "caught 51 of 72 detection chances (36 defects planted in copies of this application × 2 runs; 95% CI 52–91%)" in _frm and "11–14 false findings per run" in _frm)

# --- qualifier-procedure follow-up (teams/ai_contribution/wave3/score.json, PREREG b20ba288605a1338) ---
_q3 = json.loads((_HERE / "teams" / "ai_contribution" / "wave3" / "score.json").read_text())["summary"]
check("wave-3 qualifier follow-up: G 8/18, Q 9/18, verdict NO_IMPROVEMENT",
      _q3["qual_counts"] == {"G": "8/18", "Q": "9/18"} and _q3["verdict"] == "NO_IMPROVEMENT"
      and "qualifier-focused brief caught 9 of 18 vs our generic brief's 8" in (_HERE / "report" / "report.html").read_text())

# --- mps.gpu validation and cost (results/mpsgpu.json, PREREG_MPSGPU.md + ADDENDUM1) ---
_mg = json.loads((_HERE / "results" / "mpsgpu.json").read_text())
_big = json.loads((_HERE / "results" / "floquet_big_51qx30c.json").read_text())[0]
_frm = (_HERE / "FORM_ANSWERS.md").read_text()
_jobs = [_mg[k] for k in ("V_51qx30c_chi512", "A_74qx27c_chi512", "B_51qx30c_chi1024")]
_ref = {"V_51qx30c_chi512": _big["mps_512"], "B_51qx30c_chi1024": _big["mps_1024"],
        "A_74qx27c_chi512": json.loads((_HERE / "results" / "floquet_big_74qx27c.json").read_text())[0]["mps_512"]}
check("mps.gpu: 3 jobs COMPLETED, each within 4e-10 of mps.cpu; chi=1024 51q 1.75 h / $6.95; credit spend $11.66; CPU chi=1024 13.4 h, chi=2048 terminated 7.7 h",
      all(j["status"] == "COMPLETED" for j in _jobs)
      and all(abs(_mg[k]["value"] - v) <= 4e-10 for k, v in _ref.items())
      and round(_mg["B_51qx30c_chi1024"]["wall_h"], 2) == 1.75 and _mg["B_51qx30c_chi1024"]["cost"] == 6.95
      and round(sum(j["cost"] for j in _jobs), 2) == 11.66
      and round(_big["mps_1024_s"] / 3600, 1) == 13.4 and round(_big["mps_2048_s"] / 3600, 1) == 7.7
      and "TERMINATED" in str(_big.get("mps_2048_err", ""))
      and "matched mps.cpu to ≤ 4×10⁻¹⁰ on three jobs" in _frm and "took 1.75 h for $6.95" in _frm and "CPU tier's χ = 2,048 job was terminated by the server after 7.7 h" in _frm
      and "and $11.66 for three validated mps.gpu jobs (2026-09-28)" in _frm and "$22.46 of BlueQubit account credits" in _frm)
check("D120 wording: form compares with tracker QESEM filings of total magnetization; tracker mag = (1/N) sum Z_i",
      "its tracker QESEM filings (total magnetization" in _frm and "their tracker QESEM filings (total magnetization)" in _frm
      and "its QESEM values" not in _frm and "their QESEM values" not in _frm
      and r"M = \frac{1}{N}\sum_{i} Z_i" in (_HERE / "tracker" / "README.md").read_text())

import cost_ledger as _cl
_kit = (_HERE / "SUBMISSION_KIT.md").read_text(); _rpt = (_HERE / "report" / "report.html").read_text()
_qj = [json.loads(l) for l in (_HERE / "results" / "bq_jobs.jsonl").read_text().splitlines() if l.strip()]
_qdone = [j for j in _qj if j.get("event") == "done" and j.get("device") == "quantum"]
check("QPU: 15 'quantum' jobs billed (1 on 2026-09-26, 14 on 2026-10-05), $0.72 each, $10.80 total",
      len(_qdone) == 15 and len({j["job_id"] for j in _qdone}) == 15 and all(j["cost"] == 0.72 for j in _qdone)
      and round(sum(j["cost"] for j in _qdone), 2) == 10.80)
check("total prototype spend $22.46 = ledger = $10.80 QPU + $11.66 mps.gpu; form, kit, report state it; no stale $12.38",
      round(_cl.spent(), 2) == 22.46 and round(10.80 + 11.66, 2) == 22.46
      and "The prototype used $22.46 of BlueQubit account credits ($10.80 for 15 QPU jobs; $11.66 for three GPU MPS jobs" in _rpt
      and "has used $22.46 of BlueQubit account credits so far ($10.80 for 15 QPU jobs: one approved on 2026-09-26 and 14 pre-registered on 2026-10-05; $11.66" in _kit
      and "except $22.46 of BlueQubit account credits: $10.80 for 15 QPU jobs (one approved on 2026-09-26, 14 pre-registered on 2026-10-05) and $11.66 for three validated mps.gpu jobs" in _frm
      and all("12.38" not in d_ for d_ in (_rpt, _kit, _frm)))

# --- wave 7 confirmatory verdict + post-deadline addendum (results_post/merged_analysis.json; deviation W4) ---
_w7 = json.loads((_HERE / "teams" / "rcs" / "wave7" / "results" / "analysis.json").read_text())
_w7m = json.loads((_HERE / "teams" / "rcs" / "wave7" / "results_post" / "merged_analysis.json").read_text())
check("wave 7: EXCEED, chi_max 256, factor 2418, BlueQubit 224.08 leads; addendum: chi<=256 ladders identical, all 5 variants at 512, factor 312.6; form states it",
      _w7["verdict"] == "EXCEED" and _w7["d36"]["headline"]["chi_max"] == 256 and round(_w7["d36"]["headline"]["margin"]) == 2418
      and _w7["wording"]["lead"] == "bq" and "gives a ratio of 224.08 (Poisson 95% 88–822)" in _w7["wording"]["bq"]
      and _w7m["d36"]["headline"] == _w7["d36"]["headline"] and _w7m["verdict"] == _w7["verdict"]
      and _w7m["d28"] == _w7["d28"] and all(_w7m["d36"]["ladder"][x] == _w7["d36"]["ladder"][x] for x in ("128", "256"))
      and sorted(_w7m["d36"]["above_chi_max"]["512"]["variants_complete"]) == ["CRA_NSB", "LOG_NSB", "LOG_SB", "RCM_NSB", "TWR_NSB"]
      and round(_w7m["d36"]["above_chi_max"]["512"]["margin"], 1) == 312.6
      and "at χ ≤ 256 by factor 2418 at 36 cycles. Completed after the pre-registered deadline (deviation W4" in _frm
      and "at χ ≤ 512 the factor is 312.6." in _frm and "plus 2 of them" not in _frm and "being run under" not in _frm
      and "(5 distinct; chain orderings × SWAP routings)\n  at χ ≤ 256 by factor 2418 at 36 cycles." in _frm
      and "the 9 missing χ = 512 cells of the 5 distinct\n  variants ran under a separately frozen addendum): at χ ≤ 512 the factor is 312.6. Mirror survival" in _frm)

check("kit (paste-ready) carries wave 7: BlueQubit 224.08 first, 2418 at chi<=256, 312.6 at chi<=512, all scope sentences; release line",
      _kit.index("gives a ratio of 224.08 (Poisson 95% 88–822)") < _kit.index("at χ ≤ 256 by factor 2418 at 36 cycles")
      < _kit.index("at χ ≤ 512 the factor is 312.6.")
      and "(5 distinct; chain orderings × SWAP routings)\nat χ ≤ 256 by factor 2418 at 36 cycles. Completed after the pre-registered deadline (deviation W4" in _kit
      and "ran under a separately frozen\naddendum): at χ ≤ 512 the factor is 312.6. Mirror survival" in _kit
      and "Mirror survival of U·U† is a proxy; it is not the fidelity of sampling the 36-cycle RCS circuit." in _kit
      and "the shallower mirrors are truncations of the same instances, not the paper's separate\ndepth-d draws." in _kit
      and "We make no claim about the RCS advantage itself, and the best of our variants is not a bound\nover all classical methods." in _kit
      and "Our code (Apache-2.0) and our derived data will\nbe released publicly with the first Stage-1 results (Stage 1: weeks 1–3); third-party data keeps its own licence." in _kit
      and "Stage 1 (weeks 1–3)" in _rpt)

_n = lambda t: " ".join(t.split())
check("D142 guard: paste-ready kit abstract == FORM_ANSWERS abstract (no silent drift between the two copies)",
      _n(_frm[_frm.index("**Title:"):_frm.index("## Related work")]) == _n(_kit[_kit.index("**Title:"):_kit.index("## 4.")]))

check("kit resources paragraph matches the report §7 budget table and the form bands (batch h)",
      "2 IBM QPU\ncandidate data points, ~100 H100-hours (≈ 5 costed: scoring and ~50 cross-check amplitudes; the rest an allowance for generating classical samples for tracker #151, calibration and reruns), ~100M AI output tokens" in _kit
      and "The form's bands request this core\ntier. The PDF's §7 table also lists an optional stretch tier (6–8 hardware points, Nighthawk if available; ~1,000\nH100-hours; 1B+ tokens)." in _kit
      and "<td>2 candidate data points</td>" in _rpt and "<td>6–8 points (Nighthawk if available)</td>" in _rpt
      and "<td>~100 H100-h (≈ 5 costed: scoring + ~50 cross-check amplitudes; rest an allowance for classical samples for #151, calibration, reruns)</td>" in _rpt and "<td>~100M</td><td>1B+</td>" in _rpt
      and "QPU (IBM shots) — select:** the band that covers 2 hardware points" in _kit and "GPU hours — select:** 100–1000" in _kit and "AI tokens (output) — select:** the lowest band that covers ~100M" in _kit)

check("batch m (full audit #2): scoped bracket, deleted-qualifier limit, co-author attribution",
      "At all 72 exact 19–33-qubit tracker-parameter points with a result (BlueQubit statevector above 19), truncated Pauli paths underestimated magnitudes and truncated MPS never did" in _kit and "stress tests break the pattern" in _kit
      and "but missed all 12 deleted-qualifier chances" in _kit and "AI verification held up" not in _kit
      and "candidates with BlueQubit authors, then others" in _kit and "BlueQubit's candidates, then" not in _kit
      and "twin and candidates with BlueQubit authors (the 51- and 74-qubit Floquet circuits BlueQubit co-authored and, as a bounded case, its own new 61-qubit" in _rpt
      and "BlueQubit's own candidates" not in _rpt and _pb["A_by_cls"]["dropped_qualifier"] == "0/12")

check("batch o: PhysVEC cited as prior art in kit field 4",
      "(Li et al., arXiv:2601.10194; with physics verifiers, Deng et al., arXiv:2604.00149)" in _kit)

check("batch p: V2 post-hoc diagnostic and verifier-first 'What is new here' (Fable consult, Mike 2026-10-09)",
      "found two contributors: our wave-6 baseline MPS was the weaker" in _kit and "outliers (2 of 8 runs). Separately, in 7 of 11 plain 61-qubit 36-cycle mirror runs BlueQubit's service" in _kit and "returned exactly the ideal survival of 1, consistent with simplifying U·U† before simulating (an inference)" in _kit and "cancels the mirror" not in _kit
      and "reproducible in three runs" not in _kit
      and "**What is new here:** an external verifier that holds the decision over agent-driven strategy search" in _kit
      and "Two concurrent AI-assisted tracker filings" not in _kit and "headline claims revised" not in _kit)

# --- batch q (final multiperspective review, 2026-10-11): direction recomputed from raw (closes a text-only pin) ---
_pts = [r for f_ in ("floquet_oracle19", "floquet_patch27", "floquet_patch33", "floquet_patch27_27cyc", "floquet_patch33_27cyc")
        for r in json.loads((R / f"{f_}.json").read_text()) if isinstance(r.get("exact"), (int, float))]
_pv = lambda r, p: [v for k, v in r.items() if k.startswith(p) and k[len(p):].replace(".", "").isdigit() and isinstance(v, (int, float))]  # noqa: E731
_ties = sum(1 for r in _pts if min((abs(v) - abs(r["exact"]) for v in _pv(r, "mps_")), default=1) < 2e-5)
check("72 exact points: every Pauli-path value strictly below |exact|, no MPS value below |exact| (raw files)",
      len(_pts) == 72 and all(abs(v) < abs(r["exact"]) for r in _pts for v in _pv(r, "pau_"))
      and all(abs(v) >= abs(r["exact"]) for r in _pts for v in _pv(r, "mps_")), (len(_pts), _ties))
check("batch q: per-point QPU cost, δ qualifier, 16-cycle, same-family, thinking off, neutral #251-#258 sentence with fallback",
      "merged tracker runs &gt;1,000 s: 68.7–103.8 min/point (Floquet QESEM filings 20–144 min) → $6.6K–10K/point at $96/min" in _rpt and "BlueQubit Pauli-path at δ = 10<sup>−3</sup>, 10<sup>−4</sup> gives 0, not 1" in _rpt and "δ ≥" not in _rpt
      and "their own 16-cycle Pauli-path distance-3 ⟨ZZ⟩ (0.183)" in _kit and "its own 16-cycle Pauli-path ZZ<sub>d=3</sub> run" in _rpt
      and "same-family AI verifiers caught 51 of 72" in _kit and "fresh-context same-family AI verifiers caught 51 of 72" in _rpt
      and "agent, local Qwen3.6-35B, thinking off (3 repeats)" in _rpt and "the verifiers raised a mean of 11–14 false findings per run (11 confirmed, 14 incl. unresolved; 2 runs)" in _rpt and "averaging 11–14 false findings per run" in _kit
      and "Between 2026-10-05 and 2026-10-08 one AI-assisted group filed seven tracker solutions (#251–#258\nexcept #254)" in _kit and "verifier gates our own entries before filing" in _kit and "(our graph-state method differs from #258's chain sweep)" in _kit and "by a different method" not in _kit and "arriving fast" not in _kit
      and "exact oracles at 19–33 qubits (BlueQubit statevector above 19)" in _kit and "blind AI verifiers" not in _kit)

check("batch r (deliverability, 2026-10-13): conditional verdicts, exploratory pre-registered Heron points, countable deliverables; tracker 'requires' claim gone",
      "Stage 2 files estimates, verdicts only where verified, whichever way each falls" in _kit and "Stage 3 adds two pre-registered IBM Heron points, exploratory." in _kit
      and "**Deliverables (core tier):** at least two tracker filings, each with its convergence or cross-check data" in _kit and "not a tracker candidate as of 2026-10-13" in _kit and "barrier-protected" in _kit
      and "two IBM Heron hardware points from the program's allocation, pre-registered with barrier-protected mirror calibrations; exploratory: the prototype has no attributed hardware result yet" in _rpt
      and "at least two tracker filings (undoped twin, 51-qubit Floquet consistency check) with convergence or cross-check data, a published 61-qubit bounded-MPS result, code and derived data at week 3" in _rpt and "A stretch target of the proposal" not in _rpt and "three tracker filings" not in _kit
      and "cross-hardware consistency the tracker requires" not in _rpt and "Nighthawk if the program confirms access" not in _rpt)

# --- wave 8 / 8b QPU (report-only; not in the form) ---
_w8 = json.loads((_HERE / "teams" / "qpu" / "wave8" / "results" / "analysis.json").read_text())
_w8b = json.loads((_HERE / "teams" / "qpu" / "wave8b" / "results" / "analysis.json").read_text())
_r8 = (_HERE / "teams" / "qpu" / "wave8" / "RESULT.md").read_text(); _r8b = (_HERE / "teams" / "qpu" / "wave8b" / "RESULT.md").read_text()
check("wave 8: M_hw 0.321+-0.008 vs exact 0.463 (c=1), 0.085 vs 0.411 (c=4); 0/4 agree; ρ 0.892; wave 8b H SUPPORTED, r 0.297/0.019/-0.028/-0.013, 0/4",
      [round(r["M"], 3) for r in _w8["floquet"]] == [0.321, 0.151, 0.131, 0.085]
      and [round(r["M_exact"], 3) for r in _w8["floquet"]] == [0.463, 0.201, 0.273, 0.411]
      and all(round(r["M_se"], 3) == 0.008 for r in _w8["floquet"]) and not any(r["agree_3sigma"] for r in _w8["floquet"])
      and round(_w8["readout"]["rho"], 3) == 0.892 and _w8["attribution_hints"] == [] and _w8["repeat_identical_counts"] is False
      and _w8b["H"] == "SUPPORTED" and _w8b["recalibration"]["k_of_4"] == 0
      and [round(_w8b["per_c"][c]["r_barrier"], 3) for c in ("1", "2", "3", "4")] == [0.297, 0.019, -0.028, -0.013]
      and "0.321 ± 0.008 against exact 0.463 at 1 cycles" in _r8 and "compiled away): **SUPPORTED** by the pre-registered rule" in _r8b
      and "backend not reported" in _r8 and "Rehearsed on BlueQubit" not in _rpt and "wave 8" not in _frm.lower())

# Verdict LAST: every check above must run before it (a check placed after sys.exit never runs; D121).
print(f"\n{'ALL CLAIMS VERIFIED' if not FAILS else f'{len(FAILS)} FAILED: {FAILS}'}")
sys.exit(1 if FAILS else 0)
