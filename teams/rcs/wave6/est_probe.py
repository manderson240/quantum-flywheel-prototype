import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 20') if m < 20*2**20 else None
"""Instrument probe (free, estimate-only, no job runs): mps.cpu runtime estimates for derived mirrors."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[2]))
import bluequbit
from kicked_ising_crosscheck import load_token
from mirror_lib import derived_ops, to_qiskit
bq = bluequbit.init(load_token()); out = {}
for d in (8, 16, 24, 36):
    c = to_qiskit(derived_ops(0, d), [0]*61, measure=False)
    e = bq.estimate(c, device="mps.cpu")
    out[d] = {"runtime_ms": e.estimated_runtime, "cost": e.estimated_cost, "err": e.error_message}
    print(d, out[d], flush=True)
(HERE / "results" / "est_probe.json").write_text(json.dumps(out, indent=1))
