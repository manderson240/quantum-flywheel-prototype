import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 8') if m < 8*2**20 else None
"""Independent ground truth for 'about 1,500 BlueQubit jobs': read the account's own job history (read-only, free).
Counts jobs by UTC day and device from 2026-09-01; writes results/bq_job_history.json. No token or job content is printed."""
import collections, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import bluequbit
from kicked_ising_crosscheck import load_token
bq = bluequbit.init(load_token())
js = bq.search(created_later_than="2026-09-01T00:00:00+00:00")
rows = [{"id": j.job_id, "day": str(j.created_on)[:10], "device": j.device, "status": j.run_status, "cost": j.cost} for j in js]
by_day = collections.Counter(r["day"] for r in rows); by_dev = collections.Counter(r["device"] for r in rows)
out = {"n_total_since_0901": len(rows), "by_day": dict(sorted(by_day.items())), "by_device": dict(by_dev),
       "by_status": dict(collections.Counter(r["status"] for r in rows)), "rows": rows}
(ROOT / "results" / "bq_job_history.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
