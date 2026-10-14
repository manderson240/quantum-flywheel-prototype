"""Pilot runner. Modes:
  calibrate                       -> solvability grid over (tolerance, budget) on non-trivial instances
  baselines --tol T --budget B    -> grid, random x50, cross-family rule, hindsight references
  agent --tol T --budget B --backend lemonade|ollama --model M [--blind] --repeat k
  score --tol T --budget B        -> tables per configuration + hierarchical bootstrap + pre-registered verdict
Results: pilot/results/*.jsonl (one line per episode). Resumable: finished (arm, repeat, instance) are skipped.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
from pathlib import Path

import searchers as S


HERE = Path(__file__).parent
RES = HERE / "results"


def nontrivial(table: dict, tol: float) -> dict:
    return {k: e for k, e in table.items() if abs(e["exact"]) >= tol}


def calibrate(table: dict) -> None:
    costs = S.strategy_costs(table)
    print("strategy costs (median wall-s):", {k: round(costs[k], 1) for k in S.ORDER})
    for tol in (0.01, 0.02, 0.03, 0.05):
        nt = nontrivial(table, tol)
        row = []
        for budget in (10, 20, 40, 80, 160, 320):
            ok = sum(
                any(
                    e["runs"][s]["value"] is not None
                    and costs[s] <= budget
                    and abs(e["runs"][s]["value"] - e["exact"]) < tol
                    for s in e["runs"]
                )
                for e in nt.values()
            )
            row.append(f"B={budget}: {ok}/{len(nt)} ({100 * ok / len(nt):.0f}%)")
        print(f"tol={tol}: n={len(nt)}  " + "  ".join(row))


def _append(path: Path, rec: dict) -> None:
    with path.open("a") as f:
        f.write(json.dumps(rec) + "\n")


def _done(path: Path) -> set:
    if not path.exists():
        return set()
    return {
        (r["arm"], r["repeat"], r["instance"])
        for r in map(json.loads, path.read_text().splitlines())
    }


def run_arm(table, costs, tol, budget, arm, fn, repeat, path, **kw):
    done = _done(path)
    for iid, e in nontrivial(table, tol).items():
        if (arm, repeat, iid) in done:
            continue
        ep = S.Episode(e, costs, budget)
        log: list = []
        out = fn(ep, tol, entry=e, log=log, **kw)
        _append(
            path,
            {
                "arm": arm,
                "repeat": repeat,
                "instance": iid,
                "config": e["config"],
                "outcome": list(out),
                "spent": ep.spent,
                "queries": [s for s, _ in ep.history],
                "log": log,
            },
        )


def baselines(table, tol, budget):
    costs = S.strategy_costs(table)
    path = RES / f"baselines_tol{tol}_B{budget}.jsonl"
    run_arm(table, costs, tol, budget, "grid", S.grid, 0, path)
    run_arm(table, costs, tol, budget, "rule", S.cross_family_rule, 0, path)
    for seed in range(50):
        run_arm(table, costs, tol, budget, "random", S.random_search, seed, path, seed=seed)
    # hindsight references (use the exact answer to CHOOSE the strategy -> not legitimate searchers)
    nt = nontrivial(table, tol)
    aff = [s for s in S.ORDER if costs[s] <= budget]
    best = max(
        aff,
        key=lambda s: sum(
            nt[i]["runs"][s]["value"] is not None
            and abs(nt[i]["runs"][s]["value"] - nt[i]["exact"]) < tol
            for i in nt
        ),
    )
    dear = max(aff, key=lambda s: costs[s])
    for name, s in (("ref_best_single", best), ("ref_most_expensive", dear)):
        run_arm(
            table,
            costs,
            tol,
            budget,
            name,
            lambda ep, tol, s=s, **_: ("report", ep.query(s)),
            0,
            path,
        )
    print("baselines written:", path, "| best single:", best, "| most expensive affordable:", dear)


def agent(table, tol, budget, backend, model, blind, repeat):
    costs = S.strategy_costs(table)
    arm = f"{'blind_' if blind else ''}agent_{backend}_{model}"
    path = RES / f"agents_{backend}_tol{tol}_B{budget}.jsonl"  # one file per back end (no concurrent appends)
    run_arm(
        table,
        costs,
        tol,
        budget,
        arm,
        S.llm_agent,
        repeat,
        path,
        backend=backend,
        model=model,
        blind=blind,
    )


def summarize(recs, table, tol):
    out = {"success": 0, "certified_wrong": 0, "abstain": 0, "invalid": 0}
    for r in recs:
        out[S.score(table[r["instance"]], tuple(r["outcome"]), tol)] += 1
    n = len(recs)
    out["n"] = n
    out["net"] = (out["success"] - out["certified_wrong"] - out["invalid"]) / n if n else float("nan")
    out["spent"] = statistics.mean(r["spent"] for r in recs) if n else float("nan")
    return out


def score(table, tol, budget):
    recs = []
    for p in [RES / f"baselines_tol{tol}_B{budget}.jsonl", *sorted(RES.glob(f"agents_*_tol{tol}_B{budget}.jsonl"))]:
        if p.exists():
            recs += [json.loads(line) for line in p.read_text().splitlines()]
    arms = sorted({r["arm"] for r in recs})
    configs = sorted({r["config"] for r in recs})
    report = {}
    for arm in arms:
        ar = [r for r in recs if r["arm"] == arm]
        reps = sorted({r["repeat"] for r in ar})
        per_rep = [summarize([r for r in ar if r["repeat"] == k], table, tol) for k in reps]
        pooled = summarize(ar, table, tol)
        per_cfg = {c: summarize([r for r in ar if r["config"] == c], table, tol) for c in configs}
        report[arm] = {
            "pooled": pooled,
            "per_config": per_cfg,
            "repeats": len(reps),
            "net_by_repeat": [round(p["net"], 3) for p in per_rep],
        }
        print(
            f"{arm:55s} reps={len(reps):2d} net={pooled['net']:+.3f} succ={pooled['success']:4d} "
            f"WRONG={pooled['certified_wrong']:4d} abst={pooled['abstain']:4d} inval={pooled['invalid']:3d} "
            f"spent={pooled['spent']:6.1f} | per-config net "
            + " ".join(f"{c}={per_cfg[c]['net']:+.2f}" for c in configs)
        )
    (RES / f"score_tol{tol}_B{budget}.json").write_text(json.dumps(report, indent=1))
    return report, recs


def boot_diff(recs, table, tol, arm_a, arm_b, n=2000, seed=0):
    """Hierarchical bootstrap: resample configs, then instances within each; diff of mean net (a - b)."""
    rng = random.Random(seed)

    def net_of(rs):
        s = [S.score(table[r["instance"]], tuple(r["outcome"]), tol) for r in rs]
        return sum((x == "success") - (x == "certified_wrong") - (x == "invalid") for x in s) / len(s)

    by = {}
    for r in recs:
        if r["arm"] in (arm_a, arm_b):
            by.setdefault(r["config"], {}).setdefault(r["instance"], {}).setdefault(
                r["arm"], []
            ).append(r)
    cfgs = list(by)
    diffs = []
    for _ in range(n):
        ra, rb = [], []
        for c in (rng.choice(cfgs) for _ in cfgs):
            inst = list(by[c])
            for i in (rng.choice(inst) for _ in inst):
                ra += by[c][i].get(arm_a, [])
                rb += by[c][i].get(arm_b, [])
        if ra and rb:
            diffs.append(net_of(ra) - net_of(rb))
    diffs.sort()
    return diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs))]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("calibrate", "baselines", "agent", "score"))
    ap.add_argument("--tol", type=float, default=0.02)
    ap.add_argument("--budget", type=float, default=40)
    ap.add_argument("--backend", default="lemonade")
    ap.add_argument("--model", default="Qwen3.6-35B-A3B-MTP-GGUF")
    ap.add_argument("--blind", action="store_true")
    ap.add_argument("--repeat", type=int, default=0)
    a = ap.parse_args()
    RES.mkdir(exist_ok=True)
    table = S.load_table()
    if a.mode == "calibrate":
        calibrate(table)
    elif a.mode == "baselines":
        baselines(table, a.tol, a.budget)
    elif a.mode == "agent":
        prereg = HERE / "PILOT_PREREG.md"
        assert prereg.exists(), "pre-registration must exist before any agent run"
        agent(table, a.tol, a.budget, a.backend, a.model, a.blind, a.repeat)
    else:
        score(table, a.tol, a.budget)
    for p in (HERE / "agent_prompt.txt", HERE / "PILOT_PREREG.md"):
        if p.exists():
            print(f"sha256 {p.name}: {hashlib.sha256(p.read_bytes()).hexdigest()[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
