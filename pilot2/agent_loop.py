"""Strategy-invention loop: an LLM writes `order(n, edges)` heuristics, gets MPS-error feedback on DEV only.

The agent never sees the test lattice, test instances or any exact value. Each attempt's code runs out of process
(cohezion.compound.sandboxed_exec.run_untrusted: rlimits + wall-clock kill + import allow-list). A failed attempt
(no code, crash, timeout, non-permutation) is recorded and scored as the native ordering, never skipped.
Final heuristic = the attempt with the best DEV score (selection on dev only).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
import urllib.request
from pathlib import Path

import ordering_lab as L


REPO = Path(os.environ.get("COHEZION_SRC", Path.home() / "dev/cohezion/src"))  # provides cohezion.compound.sandboxed_exec
sys.path.insert(0, str(REPO))
from cohezion.compound.sandboxed_exec import run_untrusted  # noqa: E402


HERE = Path(__file__).parent
PROMPT = (HERE / "agent_prompt.txt").read_text() if (HERE / "agent_prompt.txt").exists() else ""
CODE_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.S)


def chat(backend: str, model: str, messages: list[dict]) -> str:
    if backend == "lemonade":
        body = {
            "model": model,
            "messages": messages,
            "max_tokens": 6000,
            "temperature": 0.7,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        url, pick = (
            "http://localhost:13305/api/v1/chat/completions",
            lambda d: d["choices"][0]["message"].get("content") or "",
        )
    else:
        body = {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {"temperature": 0.7, "num_predict": 6000},
        }
        url, pick = "http://localhost:11434/api/chat", lambda d: d["message"].get("content") or ""
    req = urllib.request.Request(
        url, json.dumps(body).encode(), {"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return pick(json.loads(r.read()))


def run_heuristic(code: str, n: int, edges) -> tuple[list[int] | None, str]:
    r = run_untrusted(
        code,
        call="order",
        args=[n, [list(e) for e in edges]],
        bindings={"np": "numpy"},
        timeout_s=20,
    )
    if not r.ok:
        return None, f"error: {r.error[:200]}"
    v = r.value
    if not (isinstance(v, list) and all(isinstance(x, int) for x in v) and L.is_perm(v, n)):
        return None, "error: return value is not a permutation of range(n)"
    return v, "ok"


def dev_setup(chi: int):
    n, e = L.dev_lattice()
    inst = [
        (cs, cyc, tx, tz, ob)
        for (tx, tz, cs) in ((1.56567, 0.33879, 0), (4.7, 0.3, 5))
        for cyc in (6, 12)
        for ob in ("mag", "zzd2")
    ]
    ev = L.Evaluator(n, e, inst, chi, HERE / "cache_dev_heavyhex19.json")
    return n, e, ev


def score_dev(ev, order) -> tuple[float, list[float]]:
    le = ev.log_errors(order)
    return statistics.mean(le), le


def loop(backend: str, model: str, run_id: int, chi: int, iters: int) -> dict:
    n, e, ev = dev_setup(chi)
    refs = {
        name: round(score_dev(ev, fn(n, e))[0], 3)
        for name, fn in (("native", L.native), ("rcm", L.rcm), ("spectral", L.spectral))
    }
    attempts: list[dict] = []
    for it in range(iters):
        hist = (
            "\n\n".join(
                f"### Attempt {a['iter']} — dev score {a['dev_score']:+.3f} ({a['status']})\n```python\n{a['code'][:3000]}\n```"
                for a in attempts
            )
            or "(no attempts yet)"
        )
        user = (
            f"Reference dev scores (mean log10 MPS error, lower is better): {json.dumps(refs)}.\n\n"
            f"Your previous attempts:\n{hist}\n\nWrite attempt {it}: ONE python code block defining order(n, edges)."
        )
        t0 = time.time()
        try:
            text = chat(
                backend,
                model,
                [
                    {"role": "system", "content": PROMPT.replace("CHI", str(chi))},
                    {"role": "user", "content": user},
                ],
            )
        except Exception as exc:  # transport failure recorded, never skipped
            text = f"(transport failure: {exc})"
        m = CODE_RE.findall(text)
        code = m[-1] if m else ""
        order, status = run_heuristic(code, n, e) if code else (None, "error: no code block")
        dev, per = score_dev(ev, order if order else L.native(n, e))
        attempts.append(
            {
                "iter": it,
                "code": code,
                "status": status,
                "dev_score": dev,
                "per_instance": per,
                "order_dev": order,
                "reply_tail": text[-600:],
                "llm_s": round(time.time() - t0, 1),
            }
        )
        print(
            f"[{model} run{run_id}] attempt {it}: {status[:60]} dev={dev:+.3f} (refs {refs})",
            flush=True,
        )
    valid = [a for a in attempts if a["status"] == "ok"]
    best = min(valid, key=lambda a: a["dev_score"]) if valid else None
    rec = {
        "backend": backend,
        "model": model,
        "run": run_id,
        "chi": chi,
        "refs_dev": refs,
        "attempts": attempts,
        "final_iter": best["iter"] if best else None,
        "final_code": best["code"] if best else None,
        "bluequbit_jobs": ev.jobs,
    }
    out = HERE / "runs" / f"{model.replace(':', '_')}_run{run_id}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rec, indent=1))
    return rec


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="ollama")
    ap.add_argument("--model", default="deepseek-v4-pro:cloud")
    ap.add_argument("--run", type=int, default=0)
    ap.add_argument("--chi", type=int, required=True)
    ap.add_argument("--iters", type=int, default=6)
    a = ap.parse_args()
    assert (HERE / "PILOT2_PREREG.md").exists(), "pre-registration must exist before any agent run"
    loop(a.backend, a.model, a.run, a.chi, a.iters)
