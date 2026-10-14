import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 20') if m < 20*2**20 else None
"""POST-HOC, EXPLORATORY (not pre-registered): does V2's BlueQubit-vs-own mismatch at small chi depend on SWAP
routing choices? Own-MPS variants on the V2 16q analogue. Writes results/posthoc_v2_routing.json."""
import json, math, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import numpy as np
import own_mps as om
from mirror_lib import derived_ops
import plan

ops = om.restrict(derived_ops(0, 36), 16); bits = plan.INPUT16


class Perm(om.MPS):
    """Variant: move the right qubit down to a+1 and do NOT move it back (track a logical->site permutation)."""
    def setup(self): self.pos = list(range(self.n)); self.at = list(range(self.n))
    def swap_sites(self, k):
        self.g2adj(om.SWAP, k); qa, qb = self.at[k], self.at[k + 1]
        self.at[k], self.at[k + 1] = qb, qa; self.pos[qa], self.pos[qb] = k + 1, k
    def cz(self, a, b):
        pa, pb = sorted((self.pos[a], self.pos[b]))
        for k in range(pb - 1, pa, -1): self.swap_sites(k)
        self.g2adj(om.CZ, pa)
    def g1(self, U, q):
        super().g1(U, self.pos[q] if hasattr(self, "pos") else q)
    def amp(self, bits):
        v = np.ones((1,), complex)
        for s in range(self.n): v = v @ self.A[s][:, bits[self.at[s]], :]
        return complex(v[0])


class NoTruncSwap(om.MPS):
    """Variant: truncate only at the CZ update; SWAP updates keep all singular values."""
    def cz(self, a, b):
        a, b = min(a, b), max(a, b); chi = self.chi
        self.chi = 10**9
        for k in range(b - 1, a, -1): self.g2adj(om.SWAP, k)
        self.chi = chi; self.g2adj(om.CZ, a); self.chi = 10**9
        for k in range(a + 1, b): self.g2adj(om.SWAP, k)
        self.chi = chi


def run(cls, chi):
    m = cls([0] * 16, chi)
    if hasattr(m, "setup"): m.setup()
    for q, x in enumerate(bits):
        if x: m.g1(om.rx(math.pi), q)
    for g in ops:
        if g[0] == "cz": m.cz(g[1], g[2])
        else: m.g1((om.rx if g[0] == "rx" else om.rz)(g[1]), g[2])
    a = m.amp(bits) if isinstance(m, Perm) else m.amplitude(bits)
    return abs(a) ** 2


out = {}
for chi in (4, 8, 16):
    out[chi] = {"swap_back": run(om.MPS, chi), "no_swap_back_perm": run(Perm, chi), "truncate_only_at_cz": run(NoTruncSwap, chi)}
    print(chi, out[chi], flush=True)
(HERE / "results" / "posthoc_v2_routing.json").write_text(json.dumps(out, indent=1))
