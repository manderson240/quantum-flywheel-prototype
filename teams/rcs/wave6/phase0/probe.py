import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 20') if m < 20*2**20 else None
"""Phase-0 instrument probe (free): estimate() for d36 on every device; one small truncated MPS job to inspect result metadata."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]; sys.path.insert(0, str(ROOT))
import bluequbit, numpy as np
from qiskit import QuantumCircuit
import re
from qasm_angle import angle
from kicked_ising_crosscheck import load_token
from cost_ledger import record_job, record_cost, spent
out = Path(__file__).parent / "probe.json"; rec = {}
bq = bluequbit.init(load_token())
def load_d36(path):
    """rx/rz/cz/barrier/measure only (verified by grep); measurement lines dropped, barriers dropped."""
    c = QuantumCircuit(61)
    for ln in path.read_text().splitlines():
        m = re.match(r"(rx|rz)\((.+)\) q\[(\d+)\];", ln)
        if m: getattr(c, m[1])(angle(m[2]), int(m[3])); continue
        m = re.match(r"cz q\[(\d+)\], ?q\[(\d+)\];", ln)
        if m: c.cz(int(m[1]), int(m[2]))
    return c
qc = load_d36(ROOT / "refs/rcs-nighthawk-meta/data/circuits/full/d36_logical.qasm")
ops = qc.count_ops(); assert ops.get("cz") == 918 and ops.get("rx") == 2196 and ops.get("rz") == 4392, ops
for dev in ["mps.cpu", "mps.gpu", "tensor-network", "quantum", "gpu", "pauli-path"]:
    try:
        e = bq.estimate(qc, device=dev); rec[f"est_{dev}"] = {k: str(v)[:200] for k, v in vars(e).items()}
    except Exception as ex:
        rec[f"est_{dev}"] = "ERR " + str(ex)[:300]
    print(dev, rec[f"est_{dev}"], flush=True)
# small truncated MPS job: 12q brickwork, chi=4, shots=2000
rng = np.random.default_rng(7); s = QuantumCircuit(12)
for layer in range(8):
    for q in range(12): s.rx(rng.uniform(0, 3.14), q); s.rz(rng.uniform(0, 3.14), q)
    for q in range(layer % 2, 11, 2): s.cz(q, q + 1)
s.measure_all()
j = bq.run(s, device="mps.cpu", shots=2000, options={"mps_bond_dimension": 4}, asynchronous=True)
record_job(j.job_id, device="mps.cpu", purpose="wave6 phase0 metadata probe"); j = bq.wait(j.job_id, timeout=900)
record_cost(j.job_id, getattr(j, "cost", None), device="mps.cpu")
d = {}
for k in dir(j):
    if k.startswith("__"): continue
    try:
        v = getattr(j, k)
        if not callable(v): d[k] = str(v)[:300]
    except Exception as ex:
        d[k] = "ERR " + str(ex)[:100]
rec["small_mps_job"] = d
out.write_text(json.dumps(rec, indent=1)); print("spent", spent())
