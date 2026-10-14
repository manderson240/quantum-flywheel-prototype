import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 20') if m < 20*2**20 else None
"""Free estimate() only for the 'quantum' device: no job is submitted."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]; sys.path.insert(0, str(ROOT))
import bluequbit
from qiskit import QuantumCircuit
from kicked_ising_crosscheck import load_token
bq = bluequbit.init(load_token()); rec = {}
for n in (2, 20, 61):
    c = QuantumCircuit(n); c.h(0); [c.cx(0, i) for i in range(1, n)]; c.measure_all()
    try:
        e = bq.estimate(c, device="quantum"); rec[n] = {k: str(v)[:300] for k, v in vars(e).items()}
    except Exception as ex:
        rec[n] = "ERR " + str(ex)[:300]
    print(n, rec[n], flush=True)
(Path(__file__).parent / "probe_quantum.json").write_text(json.dumps(rec, indent=1))
