import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 20') if m < 20*2**20 else None
sys.path.insert(0, '/home/mike-anderson/cohezion-labs/bluequbit-flywheel/teams/rcs/wave7')
import common as C, orderings as O, variant_mps as vm
from mirror_lib import derived_ops
a, b = O.order_of("CRA_NSB"), O.order_of("CSN_NSB"); print("orders differ:", a != b, sum(x != y for x, y in zip(a, b)))
ops = derived_ops(0, 8)
first = None
for v in ("CRA_NSB", "CSN_NSB"):
    mm = vm.VariantMPS(61, 16, O.order_of(v), False)
    k = 0
    for g in ops:
        if g[0] == "cz": mm.cz(g[1], g[2]); k += 1
        else: mm.gate1((vm.om.rx if g[0] == "rx" else vm.om.rz)(g[1]), g[2])
        if k == 60 and first is None: pass
    print(v, "final at[:20]", mm.at[:20])
