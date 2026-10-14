import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 20') if m < 20*2**20 else None
"""POST-HOC, EXPLORATORY: routing sensitivity of own-MPS survival at 61q d36 chi=256 (and chi=128), inst 0-2, input
k=0. Variant 'no_swap_back_perm' (Perm class from posthoc_v2_routing.py) vs the pre-registered swap-back runs.
Writes results/posthoc_routing61.json incrementally."""
import json, math, resource, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import importlib.util
spec = importlib.util.spec_from_file_location("r16", HERE / "posthoc_v2_routing.py")
import own_mps as om
from mirror_lib import derived_ops
import plan
# re-declare Perm locally (importing posthoc_v2_routing would re-run its 16q loop)
src = (HERE / "posthoc_v2_routing.py").read_text()
ns = {"om": om, "np": __import__("numpy"), "math": math}
exec(src[src.index("class Perm"):src.index("class NoTruncSwap")], ns)
Perm = ns["Perm"]
out_f = HERE / "results" / "posthoc_routing61.json"
out = json.loads(out_f.read_text()) if out_f.exists() else {}
for chi in (128, 256):
    for i in (0, 1, 2):
        k = f"chi{chi}_i{i}"
        if k in out: continue
        bits = plan.INPUTS[i][0]; t = time.time()
        m = Perm([0] * 61, chi); m.setup()
        for q, x in enumerate(bits):
            if x: m.g1(om.rx(math.pi), q)
        for g in derived_ops(i, 36):
            if g[0] == "cz": m.cz(g[1], g[2])
            else: m.g1((om.rx if g[0] == "rx" else om.rz)(g[1]), g[2])
        out[k] = {"survival_no_swap_back_perm": abs(m.amp(bits)) ** 2, "wall_s": time.time() - t,
                  "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024}
        out_f.write_text(json.dumps(out, indent=1)); print(k, out[k], flush=True)
        if out[k]["peak_rss_mb"] > 1000: sys.exit("RSS cap")
