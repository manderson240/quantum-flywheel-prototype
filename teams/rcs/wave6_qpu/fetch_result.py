import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 20') if m < 20*2**20 else None
"""Re-fetch a recorded job by id and write the result file mirror_qpu.py would have written (no new job)."""
import json, sys
from mirror_qpu import HERE, build, survival, wilson, S
import bluequbit
from kicked_ising_crosscheck import load_token
job_id, depth = sys.argv[1], int(sys.argv[2])
bq = bluequbit.init(load_token()); r = bq.get(job_id); c = build(depth)
rec = {"job_id": job_id, "device": r.device, "depth": depth, "status": r.run_status, "cost": r.cost, "error": r.error_message,
       "device_options": str(r.device_options), "run_results": str(r.run_results)[:800], "cz": c.count_ops().get("cz"),
       "input_bits_q0_first": "".join(map(str, S)), "created_on": str(r.created_on), "run_start": str(r.run_start), "run_end": str(r.run_end)}
if r.run_status == "COMPLETED":
    counts = r.get_counts(); h, n = survival(counts)
    rec.update(hits=h, shots=n, survival=h / n, wilson95=wilson(h, n), distinct_outcomes=len(counts))
(HERE / "results" / f"quantum_d{depth}.json").write_text(json.dumps(rec, indent=1)); print(json.dumps(rec)[:1500])
