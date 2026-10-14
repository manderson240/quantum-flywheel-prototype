import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 20') if m < 20*2**20 else None
"""rcs wave 7 child: runs ONE cell and writes its JSON. Usage: cell.py '<spec json>' <out path>.
Exit codes: 0 done; 3 MemAvailable dropped < 12 GiB mid-cell (not an attempt); 4 RSS cap (NOT RUN); other = crash."""
import json, math, resource, time
import common as C
from common import HERE
import variant_mps as vm
import orderings as O
from mirror_lib import derived_ops, load_instance, n_cz
import own_mps as om

spec = json.loads(sys.argv[1]); out = sys.argv[2]
t0 = time.time()
try:
    v = spec["variant"]; order = O.order_of(v); sb = v.endswith("_SB")
    if spec["kind"] == "mirror":
        ops = derived_ops(spec["inst"], spec["d"]); bits = C.INPUTS[spec["inst"]][0]
        r = vm.survival(ops, bits, spec["chi"], order, sb)
        r["n_cz"] = n_cz(ops)
    elif spec["kind"] == "fwd16":   # C3 / M: 16q forward-only U of inst 0, amplitudes vs statevector
        fwd, _ = load_instance(0)
        ops = om.restrict([g for s in fwd for g in s], 16)
        o16 = [q for q in order if q < 16]
        mps = vm.evolve(ops, C.INPUT16, 256, o16, sb, _mutate=spec.get("mutate"))
        _, psi = om.statevector_survival(ops, C.INPUT16)
        errs = [abs(mps.amp(y) - psi[tuple(y)]) for y in C.Y16]
        r = {"max_abs_amp_err": max(errs), "max_bond": mps.max_bond, "n_cz": n_cz(ops)}
    elif spec["kind"] == "smoke":   # pre-freeze code test only: random 10q non-analysis circuit
        import numpy as np
        rg = np.random.default_rng(99); ops = []
        for layer in range(12):
            ops += [(("rx", "rz")[int(rg.integers(2))], float(rg.uniform(0, 6.3)), q) for q in range(10)]
            ops += [("cz", int(a), int(b)) for a, b in [tuple(sorted(rg.choice(10, 2, replace=False))) for _ in range(4)]]
        o10 = [q for q in order if q < 10]; bits = [1, 0, 1, 1, 0, 0, 1, 0, 1, 0]
        mps = vm.evolve(ops, bits, 32, o10, sb)
        _, psi = om.statevector_survival(ops, bits)
        r = {"max_abs_amp_err": max(abs(mps.amp(y) - psi[tuple(y)]) for y in C.Y16[:3] for y in [y[:10]])}
    else:
        raise ValueError(spec["kind"])
except vm.RSSCap as e:
    print("RSSCAP", e, flush=True); sys.exit(4)
except vm.MemLow as e:
    print("MEMLOW", e, flush=True); sys.exit(3)
r.update(spec); r["wall_s"] = time.time() - t0
r["peak_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
import os; r["threads"] = os.environ.get("OPENBLAS_NUM_THREADS")
open(out, "w").write(json.dumps(r, indent=1))
