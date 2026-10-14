import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 20') if m < 20*2**20 else None
"""rcs wave 6 local own-MPS runner (PREREG §3 secondary + validation V2-local). Exact survival of own truncated MPS.
Resumable (skips cells whose json exists). Stops at the deadline in results/state.json (T0 + 9.5 h) if T0 is set.
Run: OMP_NUM_THREADS=4 nohup nice -n 10 python local_runner.py >> results/local.log 2>&1 &"""
import hashlib, json, resource, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
from mirror_lib import derived_ops, n_cz
from own_mps import run_ops, restrict, statevector_survival
import plan
OUT = HERE / "results" / "local"; OUT.mkdir(parents=True, exist_ok=True)
h = hashlib.sha256((HERE / "PREREG.md").read_bytes()).hexdigest()[:16]
assert h == (HERE / "PREREG.sha16").read_text().strip(), "PREREG hash mismatch"
STATE = HERE / "results" / "state.json"
RSS_CAP_MB = 1000


def deadline():
    try:
        t0 = json.loads(STATE.read_text()).get("T0")
        return t0 + 9.5 * 3600 if t0 else None
    except Exception:
        return None


# ---- validation (16q analogue, same input as V1/V2) ----
vf = OUT / "V_local_16q.json"
if not vf.exists():
    ops16 = restrict(derived_ops(0, 36), 16)
    sv, _ = statevector_survival(ops16, plan.INPUT16)
    rows = {"statevector_survival": sv, "n_cz": n_cz(ops16)}
    for x in (4, 8, 16, 256):
        rows[f"chi{x}"] = run_ops(ops16, plan.INPUT16, x)
    vf.write_text(json.dumps(rows, indent=1)); print("V_local", rows, flush=True)

for c in plan.local_cells():
    f = OUT / f"{c['id']}.json"
    if f.exists(): continue
    dl = deadline()
    if dl and time.time() > dl:
        print("deadline reached; remaining local cells NOT RUN", flush=True); break
    t = time.time()
    r = run_ops(derived_ops(c["inst"], c["d"]), c["bits"], c["chi"])
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    out = {**{k: c[k] for k in ("id", "inst", "d", "chi", "input_idx", "bits")}, **r, "wall_s": time.time() - t,
           "peak_rss_mb": rss, "n_cz": n_cz(derived_ops(c["inst"], c["d"]))}
    f.write_text(json.dumps(out, indent=1)); print(c["id"], r["survival"], f"{out['wall_s']:.1f}s rss {rss:.0f}MB", flush=True)
    if rss > RSS_CAP_MB:
        print("RSS cap exceeded; stopping", flush=True); break
