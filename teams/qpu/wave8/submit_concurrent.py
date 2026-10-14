"""D2: submit J1-J9 concurrently (J0 already queued) and record ids; 'collect' polls all and applies the cost stop."""
import json, sys, time
from wave8 import jobs, RES, bq_client, TERM
from cost_ledger import ok_to_spend, record_job, record_cost
IDS = RES / "job_ids.json"
bq = bq_client()
if sys.argv[1] == "submit":
    ids = json.loads(IDS.read_text()) if IDS.exists() else {"J0": "057l763XcQOGI4c7"}
    for k, (kind, c, qc) in jobs().items():
        if k in ids or k in ("J10", "J11"): continue
        assert ok_to_spend(0.72)
        j = bq.run(qc, device="quantum", shots=1000, asynchronous=True)
        record_job(j.job_id, device="quantum", purpose=f"wave8_qpu {k} {kind} c{c} (D2 concurrent)", est_cost=0.72)
        ids[k] = j.job_id; IDS.write_text(json.dumps(ids, indent=1)); print("submitted", k, flush=True)
else:
    ids = json.loads(IDS.read_text()); J = jobs()
    while True:
        pending = 0
        for k, jid in ids.items():
            out = RES / f"{k}.json"
            if out.exists(): continue
            try: r = bq.get(jid)
            except Exception as e: print("get err", k, str(e)[:80], flush=True); pending += 1; continue
            if r.run_status not in TERM: pending += 1; continue
            kind, c, _ = J[k]
            rec = {"job": k, "kind": kind, "cycles": c, "job_id": jid, "status": r.run_status, "cost": r.cost, "est_cost": 0.72,
                   "error": r.error_message, "device_options": str(r.device_options), "queue_time_ms": r.queue_time_ms,
                   "run_time_ms": r.run_time_ms, "run_start": str(r.run_start), "run_end": str(r.run_end)}
            if r.run_status == "COMPLETED": rec["counts"] = r.get_counts()
            out.write_text(json.dumps(rec, indent=1)); record_cost(jid, r.cost, device="quantum")
            print(k, r.run_status, r.cost, r.queue_time_ms, r.run_time_ms, flush=True)
            if (r.cost or 0) > 1.08:
                print("STOP cost > 1.5x estimate: cancelling queued", flush=True)
                for k2, j2 in ids.items():
                    if not (RES / f"{k2}.json").exists():
                        try: bq.cancel(j2)
                        except Exception as e: print("cancel err", k2, str(e)[:80])
        if pending == 0: print("ALL_COLLECTED", flush=True); break
        time.sleep(60)
