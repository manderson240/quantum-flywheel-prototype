"""Control queries for the research sources — run BEFORE recording any negative result.

`~/.claude/rules/systematic-debugging.md` Phase 0 mandates this and nothing implemented it:
"An empty result and a broken instrument are indistinguishable. Before recording ANY negative
-- 'no such paper', 'not published', 'no hits' -- run a control query that MUST return results."

The cost of not having it is documented, not hypothetical. In one session an HTTP 429 was read as
"no such book", an arXiv 301 as "no preprint", an unauthenticated GitHub code search as "no hits",
and a broken search endpoint as "phrase absent" — four capability conclusions drawn from four
broken instruments, none detectable from inside the result.

Each source below is probed with a query whose answer CANNOT legitimately be empty (a paper that
certainly exists, a repo that certainly exists). So:

    control returns results  -> the instrument works; a later empty result is a REAL negative
    control returns nothing  -> the instrument is broken; a later empty result is UNKNOWN

The distinction this exists to preserve is ABSENT vs UNKNOWN. Reporting UNKNOWN as ABSENT is how
a throttle becomes "this does not exist", and it is not recoverable downstream — nothing in the
empty response records that it was empty for the wrong reason.

HTTP status is mapped to a CAUSE rather than a boolean, because the causes have different
remedies and each has burned us at least once:
    429 -> throttled; retry later, do NOT conclude absence  (arxiv API, per memory)
    3xx -> redirect not followed; the endpoint moved       (arxiv abs pages)
    401/403 -> auth required; the query was never run      (GitHub code search)
    5xx -> upstream broken

Usage:
    python scripts/ops/research_source_control.py            # all sources
    python scripts/ops/research_source_control.py --json     # machine-readable
Exit code is 0 only when EVERY source is verified live, so this can gate a research run.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


UA = {"User-Agent": "cohezion-research-control/1.0"}
TIMEOUT = 20


def _cause(status: int) -> str:
    """Map an HTTP status to the reason a result would be empty. Never returns 'absent'."""
    if status == 429:
        return "THROTTLED — retry later; an empty result here means UNKNOWN, not absent"
    if 300 <= status < 400:
        return "REDIRECT not followed — the endpoint moved; the query never ran"
    if status in (401, 403):
        return "AUTH REQUIRED — the query never ran; add credentials before concluding anything"
    if status >= 500:
        return f"UPSTREAM ERROR {status} — the source is broken, not empty"
    return f"HTTP {status}"


def probe(name: str, url: str, extract, *, headers: dict | None = None) -> dict:
    """Run one control query. `extract(payload) -> int` returns the number of results found."""
    req = urllib.request.Request(  # noqa: S310 (fixed https research endpoints)
        url, headers={**UA, **(headers or {})}
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # noqa: S310 (fixed https URLs)
            body = r.read()
            status = r.status
    except urllib.error.HTTPError as e:
        return {"source": name, "live": False, "n": 0, "cause": _cause(e.code), "status": e.code}
    except Exception as exc:
        return {
            "source": name,
            "live": False,
            "n": 0,
            "cause": f"UNREACHABLE ({type(exc).__name__}) — network or DNS, not absence",
            "status": None,
        }
    try:
        n = extract(body)
    except Exception as exc:
        # A 200 that cannot be parsed is a broken instrument, not an empty result. SurrealDB
        # taught this the expensive way: HTTP 200 carrying a statement error.
        return {
            "source": name,
            "live": False,
            "n": 0,
            "cause": f"UNPARSEABLE 200 ({type(exc).__name__}) — shape changed; treat as broken",
            "status": status,
        }
    live = n > 0
    return {
        "source": name,
        "live": live,
        "n": n,
        "status": status,
        "cause": "OK"
        if live
        else "CONTROL RETURNED ZERO — instrument broken, negatives are UNKNOWN",
    }


def _arxiv(body: bytes) -> int:
    return body.decode("utf-8", "replace").count("<entry>")


def _json_len(key: str | None):
    def f(body: bytes) -> int:
        d = json.loads(body)
        if key is None:
            return len(d) if isinstance(d, list) else 1
        v = d.get(key, [])
        return len(v) if isinstance(v, list) else 0

    return f


# Control queries chosen so that ZERO results is impossible if the source works: "attention is
# all you need" is on arXiv, transformers is on GitHub, and the HF endpoints are list endpoints
# that are only empty when broken.
SOURCES = [
    (
        "arxiv",
        "https://export.arxiv.org/api/query?search_query=all:%22attention+is+all+you+need%22&max_results=3",
        _arxiv,
        None,
    ),
    (
        "huggingface-models",
        "https://huggingface.co/api/models?limit=3",
        _json_len(None),
        None,
    ),
    (
        "huggingface-daily-papers",
        "https://huggingface.co/api/daily_papers?limit=3",
        _json_len(None),
        None,
    ),
    (
        "github-api",
        "https://api.github.com/search/repositories?q=transformers+org:huggingface&per_page=3",
        _json_len("items"),
        {"Accept": "application/vnd.github+json"},
    ),
]


def self_test() -> int:
    """Prove the control can REPORT A BREAK. Without this it is unvalidated.

    A control whose every observed run says OK has never demonstrated it can say anything else,
    and "it always passes" is indistinguishable from "it cannot fail". Each case below plants a
    specific failure and requires the matching verdict — a probe that returned a blanket OK, or
    that collapsed every failure into one cause, goes RED here.
    """
    checks: list[tuple[str, bool, str]] = []

    for status, want in ((429, "THROTTLED"), (403, "AUTH"), (301, "REDIRECT"), (503, "UPSTREAM")):
        got = _cause(status)
        checks.append((f"status {status} -> {want}", want in got, got))

    # Nothing listens on port 1; deterministic and needs no external network.
    r = probe("unreachable", "http://127.0.0.1:1/", _json_len(None))
    checks.append(("unreachable host reported dead", not r["live"], r["cause"]))
    checks.append(("unreachable cause names the reason", "UNREACHABLE" in r["cause"], r["cause"]))

    live_url = "https://huggingface.co/api/models?limit=3"

    def _raises(_body: bytes) -> int:
        raise ValueError("planted shape change")

    r = probe("bad-shape", live_url, _raises)
    checks.append(("200 with unparseable body is DEAD", not r["live"], r["cause"]))
    checks.append(("unparseable names the reason", "UNPARSEABLE" in r["cause"], r["cause"]))

    r = probe("zero-results", live_url, lambda _b: 0)
    checks.append(("live source with 0 results is DEAD", not r["live"], r["cause"]))
    checks.append(("zero-result cause says UNKNOWN", "UNKNOWN" in r["cause"], r["cause"]))

    print("=== self-test: can this control detect a broken instrument? ===")
    bad = 0
    for label, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:<44} {detail[:60]}")
        bad += 0 if ok else 1
    print(f"\n  {len(checks) - bad}/{len(checks)} passed")
    if bad:
        print("  The control cannot reliably report a break — do NOT trust its OK verdicts.")
    return 0 if bad == 0 else 1


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    as_json = "--json" in sys.argv
    results = [probe(n, u, e, headers=h) for n, u, e, h in SOURCES]
    if as_json:
        print(json.dumps(results, indent=2))
    else:
        print("=== research source control (a negative is only trustworthy if these are live) ===")
        for r in results:
            mark = "OK  " if r["live"] else "DEAD"
            print(f"  [{mark}] {r['source']:<26} n={r['n']:<4} {r['cause']}")
        dead = [r["source"] for r in results if not r["live"]]
        if dead:
            print(f"\n  {len(dead)} source(s) NOT verified: {', '.join(dead)}")
            print("  Any empty result from these is UNKNOWN, not ABSENT. Do not record absence.")
        else:
            print("\n  All sources verified live — an empty result from them is a real negative.")
    return 0 if all(r["live"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
