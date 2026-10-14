"""Spend ledger for the BlueQubit cap: $10 approved by Mike on 2026-09-24, raised to $25.00 on 2026-09-28 on Mike's
instruction to use the account's existing credits ($24.28, expiring 2026-10-05) and nothing beyond them. Sums (a) the `*_cost` BlueQubit reported in the
legacy result files and (b) every row of the append-only journal results/bq_jobs.jsonl, which every new runner writes the
moment a job id exists (record_job) and again when its cost is known (record_cost). Runners call ok_to_spend() before
every job that may be charged. Monthly GPU credits report real costs, so they count against the cap."""
import json
import time
from pathlib import Path
CAP = 25.0
FILES = ["floquet_patch27_27cyc.json", "floquet_patch33_27cyc.json", "floquet_big_74qx27c.json", "floquet_big_51qx30c.json"]
R = Path(__file__).parent / "results"
JOURNAL = R / "bq_jobs.jsonl"

def _legacy() -> float:
    tot = 0.0
    for f in FILES:
        p = R / f
        if p.exists():
            for r in json.loads(p.read_text()):
                tot += sum(float(v) for k, v in r.items() if k.endswith("_cost") and isinstance(v, (int, float)))
    return tot

def _journal() -> float:
    if not JOURNAL.exists():
        return 0.0
    tot = 0.0
    for line in JOURNAL.read_text().splitlines():
        if line.strip():
            c = json.loads(line).get("cost")
            if isinstance(c, (int, float)):
                tot += float(c)
    return tot

def spent() -> float:
    return _legacy() + _journal()

def ok_to_spend(next_estimate: float = 1.0) -> bool:
    return spent() + next_estimate <= CAP

def record_job(job_id: str, **meta) -> None:
    """Write the job id to disk the moment it exists, so a crashed or timed-out poller can re-fetch it."""
    with JOURNAL.open("a") as fh:
        fh.write(json.dumps({"t": time.time(), "job_id": job_id, "event": "submitted", **meta}) + "\n")

def record_cost(job_id: str, cost, **meta) -> None:
    with JOURNAL.open("a") as fh:
        fh.write(json.dumps({"t": time.time(), "job_id": job_id, "event": "done", "cost": cost, **meta}) + "\n")

if __name__ == "__main__":
    print(f"spent ${spent():.2f} of ${CAP:.2f} (legacy ${_legacy():.2f}, journal ${_journal():.2f})")
