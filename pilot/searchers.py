"""Replay environment + all search arms for the pilot. Searchers see only values of strategies they query and
fixed per-strategy costs; ONLY score() reads the exact value.

Outcome of an episode: ("report", estimate) | ("abstain", None) | ("invalid", None) — plus compute spent.
"""

from __future__ import annotations

import json
import random
import re
import statistics
import urllib.request
from pathlib import Path


HERE = Path(__file__).parent
ORDER = [
    "pp_0.01",
    "mps_4",
    "pp_0.001",
    "mps_16",
    "mps_32",
    "pp_0.0003",
    "mps_64",
    "pp_0.0001",
    "mps_128",
]


def load_table() -> dict:
    return json.loads((HERE / "table.json").read_text())


def strategy_costs(table: dict) -> dict[str, float]:
    """Fixed cost per strategy = median BlueQubit wall-seconds over all instances (removes queue noise)."""
    ids = {k for e in table.values() for k in e["runs"]}
    return {
        k: statistics.median(e["runs"][k]["wall_s"] for e in table.values() if k in e["runs"])
        for k in ids
    }


class Episode:
    def __init__(self, entry: dict, costs: dict[str, float], budget: float):
        self._runs = entry["runs"]
        self.costs, self.budget, self.spent = costs, budget, 0.0
        self.history: list[tuple[str, float | None]] = []

    def affordable(self) -> list[str]:
        return [
            s
            for s in ORDER
            if s in self._runs
            and s not in dict(self.history)
            and self.spent + self.costs[s] <= self.budget
        ]

    def query(self, s: str) -> float | None:
        if s not in self.affordable():
            raise ValueError(f"invalid query {s}")
        self.spent += self.costs[s]
        v = self._runs[s]["value"]
        self.history.append((s, v))
        return v


def score(entry: dict, outcome: tuple, tol: float) -> str:
    kind, est = outcome
    if kind != "report":
        return "abstain" if kind == "abstain" else "invalid"
    return "success" if abs(est - entry["exact"]) < tol else "certified_wrong"


# ---------------- baselines ----------------
def _family(s: str) -> str:
    return s.split("_")[0]


def stop_rule_search(ep: Episode, order: list[str], tol: float) -> tuple:
    """Query in `order`; report when two successive queries of the SAME family agree within tol."""
    last: dict[str, float] = {}
    for s in order:
        if s not in ep.affordable():
            continue
        v = ep.query(s)
        if v is None:
            continue
        f = _family(s)
        if f in last and abs(last[f] - v) < tol:
            return ("report", v)
        last[f] = v
    return ("abstain", None)


def grid(ep: Episode, tol: float, **_) -> tuple:
    return stop_rule_search(ep, ORDER, tol)


def random_search(ep: Episode, tol: float, seed: int = 0, **_) -> tuple:
    order = ORDER[:]
    random.Random(seed).shuffle(order)
    return stop_rule_search(ep, order, tol)


def cross_family_rule(ep: Episode, tol: float, **_) -> tuple:
    """Hand-written rule: best affordable of each family (spend on the dearer one first); report the mean if the
    two families agree within tol, else abstain."""
    got = {}
    for fam in ("mps", "pp"):
        cands = [s for s in reversed(ORDER) if _family(s) == fam and s in ep.affordable()]
        if cands:
            v = ep.query(cands[0])
            if v is not None:
                got[fam] = v
    if len(got) == 2 and abs(got["mps"] - got["pp"]) < tol:
        return ("report", (got["mps"] + got["pp"]) / 2)
    return ("abstain", None)


# ---------------- LLM agent ----------------
PROMPT = (HERE / "agent_prompt.txt").read_text()
JSON_RE = re.compile(r"\{[^{}]*\}", re.S)


def _chat_lemonade(model: str, messages: list[dict], max_tokens: int = 4096) -> str:
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    req = urllib.request.Request(
        "http://localhost:13305/api/v1/chat/completions",
        json.dumps(body).encode(),
        {"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())["choices"][0]["message"].get("content") or ""


def _chat_ollama(model: str, messages: list[dict], max_tokens: int = 4096) -> str:
    body = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"temperature": 0.2, "num_predict": max_tokens},
    }
    req = urllib.request.Request(
        "http://localhost:11434/api/chat",
        json.dumps(body).encode(),
        {"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())["message"].get("content") or ""


def describe(entry: dict) -> str:
    ob = {
        "mag": "mean magnetization (1/N) sum_i <Z_i>",
        "zzd2": "average <Z_i Z_j> over qubit pairs at graph distance 2",
        "zzd3": "average <Z_i Z_j> over qubit pairs at graph distance 3",
    }[entry["obs"]]
    return (
        f"Circuit: 19-qubit heavy-hex Floquet mixed-field Ising, {entry['cycles']} Floquet cycles, from |0...0>.\n"
        f"Observable: {ob}."
    )


def llm_agent(
    ep: Episode,
    tol: float,
    entry: dict,
    backend: str,
    model: str,
    blind: bool = False,
    max_steps: int = 8,
    log: list | None = None,
    **_,
) -> tuple:
    chat = _chat_lemonade if backend == "lemonade" else _chat_ollama
    sys_msg = PROMPT.replace("TOL", f"{tol:g}")
    for _step in range(max_steps):
        menu = (
            ", ".join(f"{s} (cost {ep.costs[s]:.1f})" for s in ep.affordable()) or "none affordable"
        )
        hist = (
            "; ".join(
                f"{s} -> {'(hidden)' if blind else ('failed' if v is None else f'{v:.4f}')}"
                for s, v in ep.history
            )
            or "none yet"
        )
        user = (
            f"{describe(entry)}\nTolerance: +/-{tol:g}. Budget remaining: {ep.budget - ep.spent:.1f}.\n"
            f"Affordable strategies: {menu}.\nYour queries so far: {hist}.\nYour action:"
        )
        try:
            text = chat(
                model, [{"role": "system", "content": sys_msg}, {"role": "user", "content": user}]
            )
        except Exception as e:  # transport failure counts as a failure, never skipped
            if log is not None:
                log.append({"error": f"transport: {e}"[:200]})
            return ("invalid", None)
        m = JSON_RE.findall(text)
        if log is not None:
            log.append({"user": user[-300:], "reply": text[-400:]})
        if not m:
            return ("invalid", None)
        try:
            act = json.loads(m[-1])
        except json.JSONDecodeError:
            return ("invalid", None)
        a = act.get("action")
        if a == "abstain":
            return ("abstain", None)
        if a == "report":
            try:
                return ("report", float(act["estimate"]))
            except (KeyError, TypeError, ValueError):
                return ("invalid", None)
        if a == "query":
            s = act.get("strategy")
            if s not in ep.affordable():
                return ("invalid", None)
            ep.query(s)
            continue
        return ("invalid", None)
    return ("abstain", None)
