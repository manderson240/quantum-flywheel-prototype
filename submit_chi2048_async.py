import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 20') if m < 20*2**20 else None
"""Submit the missing χ=2048 Floquet points asynchronously on free mps.cpu; ids go to the journal at once. Read by RESULT_BIG_INTERIM rules only."""
import bluequbit
from floquet_any import load, magnetization
from kicked_ising_crosscheck import load_token
from cost_ledger import ok_to_spend, record_job
bq = bluequbit.init(load_token())
for f, tag in [("floquet_mixed_field_ising_mag_51qx30c.qasm", "51qx30c"), ("floquet_mixed_field_ising_mag_74qx27c.qasm", "74qx27c")]:
    assert ok_to_spend(0.0)
    qc, n, cyc = load(f)
    j = bq.run(qc, device="mps.cpu", pauli_sum=magnetization(n), options={"mps_bond_dimension": 2048}, force_run=True, asynchronous=True)
    record_job(j.job_id, device="mps.cpu", purpose=f"floquet {tag} mps_2048 async", tag=tag); print(tag, j.job_id, flush=True)
