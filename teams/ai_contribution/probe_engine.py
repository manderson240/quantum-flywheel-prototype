"""Local quimb MPS engine for the 19-qubit tracker-family Floquet circuits, with PER-CYCLE truncation settings.

Circuit content identical to floquet_oracle19.py (imported read-only: lattice, three_colour, pairs_at):
per layer RX(tx/3), RZ(tz/3) on every qubit, then RZZ(pi/3) on one edge colour; 3 layers/cycle.
Qubit->site ordering: spectral (Fiedler vector of the lattice graph), fixed.
A schedule is a list of 16 (max_bond, cutoff) pairs, one per cycle, applied to every 2-qubit gate
(incl. swaps) of that cycle; cutoff_mode is fixed per run. Cost = sum over the 48 RZZ layers of
sum_b chi_b^3 measured after the layer (deterministic). After every layer the realised max bond is
asserted <= the scheduled max_bond (silent-ignore detector).
"""
from __future__ import annotations
import json, math, sys, time
from pathlib import Path
import numpy as np
import quimb.tensor as qtn

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from floquet_oracle19 import lattice, three_colour, pairs_at  # noqa: E402

TZZ = math.pi / 3
CHECK_CYCLES = (1, 2, 3, 4, 6, 8, 10, 13, 16)
REGIMES = {  # name -> (tx, tz, colour_seed, truth file)
    "dev_tracker": (1.56567, 0.33879, 0, "results/floquet_oracle19.json"),
    "ho_4.7_0.3": (4.7, 0.3, 5, "results/floquet_oracle19_tx4.7_tz0.3_c5.json"),
    "ho_2.4_0.9": (2.4, 0.9, 5, "results/floquet_oracle19_tx2.4_tz0.9_c5.json"),
}

def rx(t): return np.array([[math.cos(t/2), -1j*math.sin(t/2)], [-1j*math.sin(t/2), math.cos(t/2)]])
def rz(t): return np.diag([np.exp(-1j*t/2), np.exp(1j*t/2)])
RZZ = np.diag([np.exp(-1j*TZZ/2), np.exp(1j*TZZ/2), np.exp(1j*TZZ/2), np.exp(-1j*TZZ/2)])

def spectral_order(n, edges):
    L = np.zeros((n, n))
    for a, b in edges:
        L[a, b] -= 1; L[b, a] -= 1; L[a, a] += 1; L[b, b] += 1
    w, V = np.linalg.eigh(L)
    f = V[:, 1] * (1 if V[np.argmax(np.abs(V[:, 1])), 1] > 0 else -1)
    return [int(i) for i in np.lexsort((np.arange(n), f))]

N, EDGES = lattice()
ORDER = spectral_order(N, EDGES)            # site k holds qubit ORDER[k]
SITE = {q: k for k, q in enumerate(ORDER)}
PAIRS = {d: pairs_at(N, EDGES, d) for d in (2, 3)}

def _zsigns():
    idx = np.arange(2**N)
    z = np.empty((N, 2**N), dtype=np.int8)
    for q in range(N):
        bit = (idx >> (N - 1 - SITE[q])) & 1      # site 0 = most significant
        z[q] = 1 - 2*bit
    return z
ZS = _zsigns()

def observables(v):
    p = np.abs(v)**2; p /= p.sum()
    zq = ZS @ p
    out = {"mag": float(np.mean(zq))}
    for d, prs in PAIRS.items():
        out[f"zzd{d}"] = float(np.mean([p @ (ZS[a].astype(np.int32)*ZS[b]) for a, b in prs]))
    return out

def load_truth(regime):
    rows = json.loads((ROOT / REGIMES[regime][3]).read_text())
    return {(r["cycles"], r["obs"]): r["exact"] for r in rows}

def simulate(regime, schedule, cutoff_mode="rsum2"):
    """schedule: list of 16 (max_bond|None, cutoff) tuples. Returns values at CHECK_CYCLES, cost, wall, violations."""
    tx, tz, cseed, _ = REGIMES[regime]
    layers = three_colour(EDGES, cseed)
    c = qtn.CircuitMPS(N, max_bond=None, cutoff=1e-10)
    RX, RZ = rx(tx/3), rz(tz/3)
    cost, viol, vals, maxb = 0, 0, {}, []
    t0 = time.time()
    for cyc in range(1, 17):
        mb, cut = schedule[cyc-1]
        opts = dict(max_bond=mb, cutoff=cut, cutoff_mode=cutoff_mode)
        for lay in layers:
            for q in range(N):
                c.apply_gate_raw(RX, [SITE[q]]); c.apply_gate_raw(RZ, [SITE[q]])
            for a, b in lay:
                c.apply_gate_raw(RZZ, [SITE[a], SITE[b]], **opts)
            bonds = [c.psi.bond_size(k, k+1) for k in range(N-1)]
            cost += int(sum(x**3 for x in bonds))
            maxb.append(max(bonds))
            if mb is not None and max(bonds) > mb:
                viol += 1
        if cyc in CHECK_CYCLES:
            v = c.psi.to_dense().ravel()
            for ob, x in observables(v).items():
                vals[f"{cyc}|{ob}"] = x
    return {"vals": vals, "cost": cost, "wall_s": round(time.time()-t0, 3), "violations": viol, "maxbond": maxb}
