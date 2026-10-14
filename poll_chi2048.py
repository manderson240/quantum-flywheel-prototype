import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 20') if m < 20*2**20 else None
"""Poll the two recorded χ=2048 jobs every 15 min (up to 5 days); on terminal state write mps_2048 into the result files."""
import json, time
import bluequbit
from kicked_ising_crosscheck import load_token, OUT
from cost_ledger import record_cost
JOBS = {"51qx30c": "et92IhnigBLGNytE", "74qx27c": "2U0iqV5pT3N0D5zZ"}
TERM = {"COMPLETED", "FAILED_VALIDATION", "NOT_ENOUGH_FUNDS", "CANCELED", "TERMINATED", "JOBS_LIMIT_EXCEEDED"}
bq = bluequbit.init(load_token()); done = {}; t0 = time.time()
while len(done) < len(JOBS) and time.time() - t0 < 5 * 86400:
    for tag, jid in JOBS.items():
        if tag in done: continue
        try: r = bq.get(jid)
        except Exception as e: print(tag, "get error", str(e)[:120], flush=True); continue
        if r.run_status in TERM:
            p = OUT / f"floquet_big_{tag}.json"; rows = json.loads(p.read_text()); row = rows[0]
            row["mps_2048_async_job"] = jid; row["mps_2048_async_status"] = r.run_status; row["mps_2048_async_billed"] = r.cost  # not *_cost: the journal (record_cost) counts it once
            if r.run_status == "COMPLETED":
                row["mps_2048"] = float(r.expectation_value); row.pop("mps_2048_err", None)
            else:
                row["mps_2048_async_err"] = (r.error_message or "")[:240]
            p.write_text(json.dumps(rows, indent=1)); record_cost(jid, r.cost, device="mps.cpu", tag=tag); done[tag] = r.run_status
            print(tag, r.run_status, row.get("mps_2048"), "cost", r.cost, flush=True)
    if len(done) < len(JOBS): time.sleep(900)
print("FINISHED", done)
