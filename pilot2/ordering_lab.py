"""Strategy-invention pilot: qubit orderings for MPS simulation of heavy-hex Floquet Ising circuits.

Lattices
  dev  : 19-qubit heavy-hex patch (Qiskit heavy-hex distance 3)       -- the agent gets feedback here
  test : 24-qubit connected sub-patch of the tracker's 51-qubit lattice -- held out (never shown to the agent)
Baseline orderings: native, rcm (bandwidth), spectral (Fiedler vector), random, cutwidth-SA (annealing on the
graph cutwidth, no quantum compute). The MPS error of an ordering on an instance = |MPS(chi) - exact|, exact from a
local statevector; the MPS circuit AND observable are relabelled with the same permutation (checked).
"""

from __future__ import annotations

import json
import math
import random
import sys
import time
from collections import deque
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import reverse_cuthill_mckee


HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
import floquet_oracle19 as o19  # noqa: E402
import floquet_tracker as ft  # noqa: E402
from kicked_ising_crosscheck import exact_mean_z, load_token  # noqa: E402
from qiskit import QuantumCircuit  # noqa: E402


Edge = tuple[int, int]


# ---------------- lattices ----------------
def dev_lattice() -> tuple[int, list[Edge]]:
    return o19.lattice()


def test_lattice(size: int = 24, seed_qubit: int = 20) -> tuple[int, list[Edge]]:
    """Connected BFS ball of `size` qubits from the tracker's 51-qubit lattice, relabelled 0..size-1 in BFS order
    of a DIFFERENT root than the dev lattice's labelling (so native order is not accidentally good)."""
    layers, _ = ft.readme_spec()
    edges = sorted(set().union(*layers))
    adj = {i: [] for i in range(ft.N)}
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    seen, dq = [seed_qubit], deque([seed_qubit])
    while dq and len(seen) < size:
        u = dq.popleft()
        for v in sorted(adj[u]):
            if v not in seen and len(seen) < size:
                seen.append(v)
                dq.append(v)
    keep = sorted(seen)  # label by original index, not BFS order
    idx = {q: i for i, q in enumerate(keep)}
    sub = sorted((idx[a], idx[b]) for a, b in edges if a in idx and b in idx)
    return len(keep), sub


def square_lattice(rows: int = 5, cols: int = 5) -> tuple[int, list[Edge]]:
    """Square lattice (IBM Nighthawk connectivity class), row-major labels."""
    q = lambda r, c: r * cols + c  # noqa: E731
    e = [(q(r, c), q(r, c + 1)) for r in range(rows) for c in range(cols - 1)]
    e += [(q(r, c), q(r + 1, c)) for r in range(rows - 1) for c in range(cols)]
    return rows * cols, sorted(e)


def edge_colouring(edges: list[Edge], seed: int = 0) -> list[list[Edge]]:
    """Proper edge colouring with max-degree colours (exists for bipartite graphs: König); randomised greedy."""
    deg = {}
    for a, b in edges:
        deg[a] = deg.get(a, 0) + 1
        deg[b] = deg.get(b, 0) + 1
    k = max(deg.values())
    rng = random.Random(seed)
    for _ in range(20000):
        order = edges[:]
        rng.shuffle(order)
        col, ok = {}, True
        for a, b in order:
            used = {c for e, c in col.items() if a in e or b in e}
            free = [c for c in range(k) if c not in used]
            if not free:
                ok = False
                break
            col[(a, b)] = free[0]
        if ok:
            return [[e for e in edges if col[e] == c] for c in range(k)]
    raise RuntimeError("no proper colouring found")


def connected(n: int, edges: list[Edge]) -> bool:
    adj = {i: [] for i in range(n)}
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    seen, dq = {0}, deque([0])
    while dq:
        for v in adj[dq.popleft()]:
            if v not in seen:
                seen.add(v)
                dq.append(v)
    return len(seen) == n


# ---------------- orderings ----------------
def native(n, edges):
    return list(range(n))


def rcm(n, edges):
    r = [a for a, b in edges] + [b for a, b in edges]
    c = [b for a, b in edges] + [a for a, b in edges]
    return [
        int(i)
        for i in reverse_cuthill_mckee(
            csr_matrix((np.ones(len(r)), (r, c)), shape=(n, n)), symmetric_mode=True
        )
    ]


def spectral(n, edges):
    L = np.zeros((n, n))
    for a, b in edges:
        L[a, b] = L[b, a] = -1
    np.fill_diagonal(L, -L.sum(1))
    w, v = np.linalg.eigh(L)
    return [int(i) for i in np.argsort(v[:, 1])]


def random_order(n, edges, seed=0):
    p = list(range(n))
    random.Random(seed).shuffle(p)
    return p


def cutwidth(order, edges) -> int:
    pos = {q: i for i, q in enumerate(order)}
    return max(
        sum(1 for a, b in edges if min(pos[a], pos[b]) <= k < max(pos[a], pos[b]))
        for k in range(len(order) - 1)
    )


def cutwidth_sa(n, edges, iters=20000, seed=0):
    """Simulated annealing on (cutwidth, total cut size) — a purely graph-theoretic optimiser, no quantum compute."""
    rng = random.Random(seed)

    def cost(o):
        pos = {q: i for i, q in enumerate(o)}
        cuts = [
            sum(1 for a, b in edges if min(pos[a], pos[b]) <= k < max(pos[a], pos[b]))
            for k in range(n - 1)
        ]
        return max(cuts) * 1000 + sum(cuts)

    cur = spectral(n, edges)
    cc = cost(cur)
    best, bc = cur[:], cc
    for t in range(iters):
        i, j = rng.sample(range(n), 2)
        nxt = cur[:]
        nxt[i], nxt[j] = nxt[j], nxt[i]
        nc = cost(nxt)
        T = 50 * (1 - t / iters) + 1e-3
        if nc <= cc or rng.random() < math.exp((cc - nc) / T):
            cur, cc = nxt, nc
            if cc < bc:
                best, bc = cur[:], cc
    return best


# ---------------- circuits, observables, evaluation ----------------
def zlabel(n, qs):
    s = ["I"] * n
    for q in qs:
        s[n - 1 - q] = "Z"
    return "".join(s)


def pairs_at(n, edges, d):
    return o19.pairs_at(n, edges, d)


def observables(n, edges):
    obs = {"mag": [(zlabel(n, (i,)), 1.0 / n) for i in range(n)]}
    for d in (2, 3):
        p = pairs_at(n, edges, d)
        obs[f"zzd{d}"] = [(zlabel(n, pr), 1.0 / len(p)) for pr in p]
    return obs


def circuit(n, edges, colour_seed, cycles, tx, tz):
    """Floquet mixed-field Ising: per layer RX(tx/k), RZ(tz/k) on all qubits then RZZ(pi/3) on one colour class;
    k = number of colour classes (3 on heavy-hex, reproducing the tracker circuit; 4 on the square lattice)."""
    layers = edge_colouring(edges, colour_seed)
    k = len(layers)
    qc = QuantumCircuit(n)
    for _ in range(cycles):
        for lay in layers:
            for q in range(n):
                qc.rx(tx / k, q)
                qc.rz(tz / k, q)
            for a, b in lay:
                qc.rzz(math.pi / 3, a, b)
    return qc


def relabel(qc: QuantumCircuit, terms, order):
    n = qc.num_qubits
    pos = {old: new for new, old in enumerate(order)}
    out = QuantumCircuit(n)
    for ins in qc.data:
        out.append(ins.operation, [out.qubits[pos[qc.find_bit(q).index]] for q in ins.qubits])
    new = []
    for lab, c in terms:
        s = ["I"] * n
        for k, ch in enumerate(lab):
            if ch != "I":
                s[n - 1 - pos[n - 1 - k]] = ch
        new.append(("".join(s), c))
    return out, new


def is_perm(order, n) -> bool:
    return isinstance(order, list) and sorted(order) == list(range(n))


class Evaluator:
    """MPS error of an ordering on a fixed instance set; caches exact values; counts BlueQubit jobs."""

    def __init__(self, n, edges, instances, chi, cache_path: Path):
        self.n, self.edges, self.instances, self.chi = n, edges, instances, chi
        self.cache_path = cache_path
        self.cache = (
            json.loads(cache_path.read_text()) if cache_path.exists() else {"exact": {}, "mps": {}}
        )
        self.jobs = 0
        self._bq = None

    def _bqc(self):
        if self._bq is None:
            import bluequbit

            self._bq = bluequbit.init(load_token())
        return self._bq

    def _key(self, inst):
        return "|".join(str(x) for x in inst)

    def exact(self, inst):
        k = self._key(inst)
        if k not in self.cache["exact"]:
            cs, cyc, tx, tz, ob = inst
            qc = circuit(self.n, self.edges, cs, cyc, tx, tz)
            self.cache["exact"][k] = exact_mean_z(qc, observables(self.n, self.edges)[ob])
            self._save()
        return self.cache["exact"][k]

    def mps(self, inst, order):
        k = self._key(inst) + f"|chi{self.chi}|" + ",".join(map(str, order))
        if k not in self.cache["mps"]:
            cs, cyc, tx, tz, ob = inst
            qc = circuit(self.n, self.edges, cs, cyc, tx, tz)
            c2, t2 = relabel(qc, observables(self.n, self.edges)[ob], order)
            r = self._bqc().run(
                c2, device="mps.cpu", pauli_sum=t2, options={"mps_bond_dimension": self.chi}
            )
            self.cache["mps"][k] = float(r.expectation_value)
            self.jobs += 1
            self._save()
        return self.cache["mps"][k]

    def log_errors(self, order) -> list[float]:
        return [math.log10(abs(self.mps(i, order) - self.exact(i)) + 1e-4) for i in self.instances]

    def _save(self):
        self.cache_path.write_text(json.dumps(self.cache))


def check_relabel_invariance(n, edges, order, inst) -> float:
    cs, cyc, tx, tz, ob = inst
    qc = circuit(n, edges, cs, cyc, tx, tz)
    terms = observables(n, edges)[ob]
    c2, t2 = relabel(qc, terms, order)
    return abs(exact_mean_z(qc, terms) - exact_mean_z(c2, t2))


if __name__ == "__main__":  # calibration
    t0 = time.time()
    nd, ed = dev_lattice()
    nt, et = test_lattice()
    print(
        f"dev lattice n={nd} edges={len(ed)} | test lattice n={nt} edges={len(et)} connected={connected(nt, et)}"
    )
    for name, (n, e) in (("dev", (nd, ed)), ("test", (nt, et))):
        for fn in (native, rcm, spectral, lambda n_, e_: cutwidth_sa(n_, e_, 20000)):
            od = fn(n, e)
            print(
                f"  {name} {getattr(fn, '__name__', 'cutwidth_sa'):12s} cutwidth={cutwidth(od, e)}"
            )
    print(f"({time.time() - t0:.0f}s)")
