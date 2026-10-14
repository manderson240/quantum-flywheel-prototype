"""Headroom probe runner (see PREREG.md). Phases: grid, random, hillclimb, heldout. Resumable (JSONL, keyed).
Run: OMP_NUM_THREADS=1 nice -n 10 python3 runner.py <phase>
"""
from __future__ import annotations
import json, math, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
CHI_GRID = [4, 5, 6, 7, 8, 10, 12, 14, 16, 20, 24, 28, 32, 40, 48, 56, 64]
EPS_GRID = [0.0, 1e-8, 1e-7, 1e-6, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2]
LEVELS = {"L8": (8, 331215), "L16": (16, 2227151), "L32": (32, 14240719)}  # chi_k, C_k (dev cost of const chi_k)
E_BUDGET = len(CHI_GRID) * len(EPS_GRID)  # 187 evaluations per searcher per level = size of the constant grid
SEEDS = (0, 1, 2)
MEM_FLOOR_KB = 20 * 1024 * 1024
WORKERS = 4
DEV_INST = [(c, o) for c in (4, 6, 8, 10, 13, 16) for o in ("mag", "zzd2", "zzd3")]

def mem_ok_wait():
    waited, delay = 0, 60
    while True:
        kb = int([l for l in open("/proc/meminfo") if l.startswith("MemAvailable")][0].split()[1])
        if kb >= MEM_FLOOR_KB:
            return waited
        if waited > 7200:
            raise RuntimeError(f"MemAvailable {kb} kB < 20 GiB for > 2 h: abort (INCONCLUSIVE)")
        time.sleep(delay); waited += delay; delay = min(delay * 2, 900)

def realise(s):
    """schedule spec -> (list of 16 (max_bond, cutoff), cutoff_mode)."""
    if s["kind"] == "const":
        if s["eps"] == 0.0:
            return [(s["chi"], 1e-10)] * 16, "rel"          # quimb library default cutoff & mode
        return [(s["chi"], s["eps"])] * 16, "rsum2"
    k = s["k"]; xs = [1, 6, 11, 16]
    return [(max(2, int(round(2 ** float(np.interp(c, xs, k))))), s["eps"]) for c in range(1, 17)], "rsum2"

def metrics(vals, truth):
    errs = [max(abs(vals[f"{c}|{o}"] - truth[(c, o)]), 1e-12) for (c, o) in DEV_INST]
    return {"med_log10_err": float(np.median(np.log10(errs))), "log10_mae": float(math.log10(np.mean(errs)))}

def job(args):
    import probe_engine as E
    phase, regime, spec = args
    waited = mem_ok_wait()
    sched, mode = realise(spec)
    rec = {"phase": phase, "regime": regime, "spec": spec, "sched": sched, "mode": mode, "mem_wait_s": waited}
    for attempt in (1, 2):
        try:
            r = E.simulate(regime, sched, cutoff_mode=mode)
            rec.update(cost=r["cost"], wall_s=r["wall_s"], violations=r["violations"], maxbond=r["maxbond"],
                       **metrics(r["vals"], E.load_truth(regime)), failed=False, attempts=attempt)
            return rec
        except Exception as e:  # pre-registered: retry once, then record as failed
            rec.update(failed=True, error=str(e)[:200], attempts=attempt)
    return rec

def key(regime, spec): return regime + "|" + json.dumps(spec, sort_keys=True)

def load(phase):
    p = RES / f"runs_{phase}.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

def run_batch(phase, items):
    p = RES / f"runs_{phase}.jsonl"
    done = {key(r["regime"], r["spec"]) for r in load(phase)}
    todo = [(phase, reg, s) for reg, s in items if key(reg, s) not in done]
    with Pool(WORKERS, maxtasksperchild=50) as pool, p.open("a") as f:
        for i, rec in enumerate(pool.imap_unordered(job, todo), 1):
            f.write(json.dumps(rec) + "\n"); f.flush()
            if i % 25 == 0: print(phase, i, "/", len(todo), flush=True)

def phase_grid():
    import probe_engine as E
    items = [(reg, {"kind": "const", "chi": c, "eps": e}) for reg in E.REGIMES for c in CHI_GRID for e in EPS_GRID]
    run_batch("grid", items)

MAX_DRAWS = 4 * E_BUDGET

def random_specs(level, seed, n=MAX_DRAWS):
    chi_k, _ = LEVELS[level]
    rng = np.random.default_rng(1000 * seed + chi_k)
    hi = math.log2(2 * chi_k)
    return [{"kind": "knots", "k": [round(float(x), 4) for x in rng.uniform(2, hi, 4)],
             "eps": float(10 ** rng.uniform(-9, -2)), "level": level, "seed": seed, "draw": i} for i in range(n)]

def qualifying_const(level):
    C = LEVELS[level][1]
    return sum(1 for r in load("grid") if r["regime"] == "dev_tracker" and not r["failed"] and r["cost"] <= C)

def phase_random():
    """Per (level, seed): evaluate the seeded draw stream in chunks of 40 until the number of in-budget
    (cost <= C_k) evaluations reaches Q_k = the constant grid's in-budget count at that level, or MAX_DRAWS."""
    for lv in LEVELS:
        Q, C = qualifying_const(lv), LEVELS[lv][1]
        for sd in SEEDS:
            stream = random_specs(lv, sd)
            while True:
                rs = [r for r in load("random") if r["spec"]["level"] == lv and r["spec"]["seed"] == sd]
                q = sum(1 for r in rs if not r["failed"] and r["cost"] <= C)
                if q >= Q or len(rs) >= MAX_DRAWS: break
                n = len(rs); run_batch("random", [("dev_tracker", s) for s in stream[n:n + 40]])
            print(lv, sd, "draws", len(rs), "qualifying", q, "Q_k", Q, flush=True)

def best_const(level, regime="dev_tracker", metric="med_log10_err", max_cost=None):
    C = LEVELS[level][1] if max_cost is None else max_cost
    ok = [r for r in load("grid") if r["regime"] == regime and not r["failed"] and r["cost"] <= C]
    return min(ok, key=lambda r: r[metric]) if ok else None

def hillclimb(level):
    """Deterministic greedy coordinate search over (4 knots, log10 eps) from the best constant setting at C_k."""
    import probe_engine as E
    chi_k, C = LEVELS[level]
    hi = math.log2(2 * chi_k)
    b = best_const(level)
    x = [math.log2(b["spec"]["chi"])] * 4 + [math.log10(b["spec"]["eps"]) if b["spec"]["eps"] > 0 else -9.0]
    truth = E.load_truth("dev_tracker")
    cache, log, n_eval = {}, [], 0
    def evaluate(x):
        nonlocal n_eval
        spec = {"kind": "knots", "k": [round(v, 4) for v in x[:4]], "eps": float(10 ** x[4]), "level": level, "seed": "hc"}
        sched, mode = realise(spec)
        ck = json.dumps(sched)
        if ck in cache: return cache[ck]
        mem_ok_wait()
        rec = job(("hillclimb", "dev_tracker", spec)); n_eval += 1
        log.append(rec)
        val = (rec["med_log10_err"] if (not rec["failed"] and rec["cost"] <= C) else math.inf)
        cache[ck] = val
        return val
    cur = evaluate(x); step = 0.5
    while n_eval < E_BUDGET and step >= 0.0625:
        improved = False
        moves = [(i, d) for i in range(4) for d in (step, -step)] + [("all", step), ("all", -step), (4, step), (4, -step)]
        for i, d in moves:
            if n_eval >= E_BUDGET: break
            y = list(x)
            if i == "all": y[:4] = [v + d for v in y[:4]]
            else: y[i] += d
            y[:4] = [min(max(v, 2.0), hi) for v in y[:4]]; y[4] = min(max(y[4], -9.0), -2.0)
            v = evaluate(y)
            if v < cur - 1e-12:
                x, cur, improved = y, v, True
        if not improved: step /= 2
    with (RES / "runs_hillclimb.jsonl").open("a") as f:
        for r in log: f.write(json.dumps(r) + "\n")
    return {"level": level, "n_eval": n_eval, "final_step": step, "best": cur, "x": x}

def phase_hillclimb():
    done = {r["spec"]["level"] for r in load("hillclimb")}
    todo = [lv for lv in LEVELS if lv not in done]
    with Pool(min(3, len(todo) or 1)) as pool:
        for s in pool.imap_unordered(hillclimb, todo): print(json.dumps(s), flush=True)

def dev_selected(level, rnd_scored=None):
    """Best dev schedule at level: over the scored random evaluations (first Q_k in-budget per seed) + hill-climb."""
    C = LEVELS[level][1]
    if rnd_scored is None:
        Q = qualifying_const(level)
        rnd_scored = []
        for sd in SEEDS:
            rnd_scored += sorted([r for r in load("random") if r["spec"]["level"] == level and r["spec"]["seed"] == sd
                                  and not r["failed"] and r["cost"] <= C], key=lambda r: r["spec"]["draw"])[:Q]
    cands = rnd_scored + [r for r in load("hillclimb") if not r["failed"] and r["spec"].get("level") == level and r["cost"] <= C]
    return min(cands, key=lambda r: r["med_log10_err"]) if cands else None

def phase_heldout():
    import probe_engine as E
    items = []
    for lv in LEVELS:
        s = dev_selected(lv)
        if s: items += [(reg, s["spec"]) for reg in E.REGIMES if reg != "dev_tracker"]
    run_batch("heldout", items)

if __name__ == "__main__":
    {"grid": phase_grid, "random": phase_random, "hillclimb": phase_hillclimb, "heldout": phase_heldout}[sys.argv[1]]()
