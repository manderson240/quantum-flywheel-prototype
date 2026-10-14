"""rcs wave 7: own numpy MPS with a chosen chain ordering and SWAP routing. Built on own_mps.MPS (byte-identical
copy of wave 6's own_mps.py, incl. the D3 gesvd fallback): same 2-site SVD update, same truncation (chi, and
s <= 1e-10 s_max dropped), same renormalisation. Only the placement of logical qubits on chain sites and the
SWAP routing differ.
  order[site] = logical qubit initially at chain site `site`.
  swap_back=True  (SB):  move the qubit at the larger site down to (smaller site + 1), apply CZ, move it back.
                         With the identity order this is exactly wave 6's own_mps.MPS.cz op sequence.
  swap_back=False (NSB): same move, no move back; the logical->site permutation is tracked.
                         With the identity order this is exactly wave 6's posthoc Perm class.
Returns the EXACT survival |<x|psi_trunc>|^2 (no sampling)."""
from __future__ import annotations
import math
import numpy as np
import own_mps as om

RSS_CAP_MB = 3072
MEM_ABORT_KB = 12 * 2**20   # abort (not an attempt) if the box drops below 12 GiB available mid-cell


class RSSCap(RuntimeError):
    pass


class MemLow(RuntimeError):
    pass


def rss_mb():
    for ln in open("/proc/self/status"):
        if ln.startswith("VmRSS"):
            return int(ln.split()[1]) / 1024
    return 0.0


def mem_avail_kb():
    return int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1])


class VariantMPS(om.MPS):
    def __init__(self, n, chi, order, swap_back, _mutate=None):
        super().__init__([0] * n, chi)
        assert sorted(order) == list(range(n))
        self.at = list(order)
        self.pos = [0] * n
        for s, q in enumerate(order):
            self.pos[q] = s
        self.swap_back = swap_back
        self._mutate = _mutate          # CONTROL M only: corrupts permutation bookkeeping (must make C3 fail)
        self.n_updates = 0
        self.peak_rss = rss_mb()

    def g2adj(self, U4, i):
        super().g2adj(U4, i)
        self.n_updates += 1
        if self.n_updates % 50 == 0:
            r = rss_mb(); self.peak_rss = max(self.peak_rss, r)
            if r > RSS_CAP_MB:
                raise RSSCap(f"RSS {r:.0f} MB > {RSS_CAP_MB}")
            if mem_avail_kb() < MEM_ABORT_KB:
                raise MemLow("MemAvailable < 12 GiB mid-cell")

    def swap_sites(self, k):
        self.g2adj(om.SWAP, k)
        if self._mutate == "book":
            return
        qa, qb = self.at[k], self.at[k + 1]
        self.at[k], self.at[k + 1] = qb, qa
        self.pos[qa], self.pos[qb] = k + 1, k

    def gate1(self, U, q):
        self.g1(U, q if self._mutate == "g1raw" else self.pos[q])

    def cz(self, a, b):
        pa, pb = sorted((self.pos[a], self.pos[b]))
        for k in range(pb - 1, pa, -1):
            self.swap_sites(k)
        self.g2adj(om.CZ, pa)
        if self.swap_back:
            for k in range(pa + 1, pb):
                self.swap_sites(k)

    def amp(self, bits):
        v = np.ones((1,), complex)
        for s in range(self.n):
            v = v @ self.A[s][:, bits[self.at[s]], :]
        return complex(v[0])


def evolve(ops, bits, chi, order, swap_back, prep=True, _mutate=None):
    """Prepare |bits> by rx(pi) flips (as on the device), apply ops; return the MPS."""
    m = VariantMPS(len(bits), chi, order, swap_back, _mutate)
    if prep:
        for q, x in enumerate(bits):
            if x: m.gate1(om.rx(math.pi), q)
    for g in ops:
        if g[0] == "cz": m.cz(g[1], g[2])
        elif g[0] == "rx": m.gate1(om.rx(g[1]), g[2])
        else: m.gate1(om.rz(g[1]), g[2])
    return m


def survival(ops, bits, chi, order, swap_back):
    m = evolve(ops, bits, chi, order, swap_back)
    return {"survival": abs(m.amp(bits)) ** 2, "max_bond": m.max_bond, "sum_discarded": m.discarded,
            "svd_fallbacks": getattr(m, "svd_fallbacks", 0), "n_updates": m.n_updates,
            "peak_rss_mb_sampled": max(m.peak_rss, rss_mb())}
