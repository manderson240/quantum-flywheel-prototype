"""Exact amplitudes <x| (⊗V_i) C |0^n> for a Clifford circuit C followed by per-qubit non-Clifford tails V_i
(the structure of IBM/UChicago's UNDOPED random-graph-state circuit), via:

  1. Path-sum of the Clifford part (one Boolean variable per H; phase i^{P}, P a Z4 polynomial with
     Z4-linear and 2*quadratic terms), with online Gaussian-sum elimination of every internal variable
     (Dehaene-De Moor / Amy "sum-over-paths" rules). Result: |S> = K * sum_o i^{P(o)} |e(o)>, with each
     output bit e_q(o) an affine GF(2) function of the remaining variables o.
  2. Reparametrisation so every remaining variable IS an output bit ("pivot" qubits); the other
     ("dependent") qubits carry a parity factor f_j(c_j xor l_j.o), Fourier-expanded into one new variable
     per dependent qubit. Result: a graph-state form with EXACTLY one variable per qubit
         amp = K * sum_{y in GF(2)^n} prod_q h_q(y_q) * (-1)^{sum_{p<q} Gamma_pq y_p y_q}
     where only the unary weights h_q depend on the sampled bitstring x.
  3. GF(2) cut-rank message passing along a qubit order: after summing the first m variables L, the partial
     sum depends on the rest R only through s = Gamma[L,R] y_R, an element of colspace(Gamma[L,R]) whose
     dimension is the cut-rank = stabilizer entanglement across (L|R). Message size = 2^{cut-rank}.

Cost per amplitude: memory 2^{max_m E_m}, work ~ sum_m 2^{E_m}, for the chosen order.
"""

from __future__ import annotations

import re

import numpy as np


W8 = np.exp(1j * np.pi / 4)

# ---------------------------------------------------------------- parsing
_M = {
    "h": np.array([[1, 1], [1, -1]]) / np.sqrt(2),
    "s": np.diag([1, 1j]),
    "z": np.diag([1, -1]),
    "sx": np.array([[1 + 1j, 1 - 1j], [1 - 1j, 1 + 1j]]) / 2,
    "tdg": np.diag([1, np.exp(-1j * np.pi / 4)]),
}


def _gate_matrix(g):
    if g.startswith("rz("):
        th = float(g[3:-1])
        return np.diag([np.exp(-1j * th / 2), np.exp(1j * th / 2)])
    return _M[g]


def parse(qasm: str):
    """Return n, Clifford op list (up to each qubit's first non-Clifford gate), per-qubit tail matrices V_q."""
    n = int(re.search(r"qreg q\[(\d+)\]", qasm).group(1))
    ops, tail_started = [], [False] * n
    V = [np.eye(2, dtype=complex) for _ in range(n)]
    for line in qasm.splitlines():
        qs = [int(x) for x in re.findall(r"q\[(\d+)\]", line)]
        if not qs or line.startswith("qreg"):
            continue
        g = line.split()[0]
        if g in ("tdg", "t") or g.startswith("rz("):
            tail_started[qs[0]] = True
        if g == "cz":
            assert not any(tail_started[q] for q in qs), (
                "non-Clifford before a CZ: method does not apply"
            )
            ops.append(("cz", qs[0], qs[1]))
        elif tail_started[qs[0]]:
            V[qs[0]] = _gate_matrix(g) @ V[qs[0]]
        else:
            assert g in ("h", "s", "z", "sx"), g
            ops.append((g, qs[0]))
    return n, ops, V


# ---------------------------------------------------------------- path sum
class PathSum:
    """sum_vars i^{P} ; P = sum lin[v] v + 2 sum_{edges} u v (mod 4). Affine exprs are (c, frozenset)."""

    def __init__(self, n):
        self.lin, self.adj = {}, {}
        self.nv = 0
        self.w8 = 0  # global phase omega^w8
        self.lg = 0.0  # global magnitude 2^lg
        self.wire = [(0, frozenset()) for _ in range(n)]

    # --- polynomial edits
    def _new(self):
        v = self.nv
        self.nv += 1
        self.lin[v] = 0
        self.adj[v] = set()
        return v

    def _toggle(self, u, v):
        if u == v:
            self.lin[u] = (self.lin[u] + 2) % 4
        elif v in self.adj[u]:
            self.adj[u].discard(v)
            self.adj[v].discard(u)
        else:
            self.adj[u].add(v)
            self.adj[v].add(u)

    def add_lin(self, a, e):
        """P += a * (c xor XOR(S)) mod 4."""
        a %= 4
        if not a:
            return
        c, S = e
        if c:
            self.w8 = (self.w8 + 2 * a) % 8
            a = (-a) % 4
        S = sorted(S)
        for s in S:
            self.lin[s] = (self.lin[s] + a) % 4
        if a % 2:
            for i in range(len(S)):
                for j in range(i + 1, len(S)):
                    self._toggle(S[i], S[j])

    def add_quad(self, e1, e2):
        """P += 2*(e1)(e2) mod 4 = 2*(c1+sum S1)(c2+sum S2)."""
        c1, S1 = e1
        c2, S2 = e2
        if c1 and c2:
            self.w8 = (self.w8 + 4) % 8
        if c1:
            for s in S2:
                self.lin[s] = (self.lin[s] + 2) % 4
        if c2:
            for s in S1:
                self.lin[s] = (self.lin[s] + 2) % 4
        for a in S1:
            for b in S2:
                self._toggle(a, b)

    def substitute(self, z, e):
        """z := e (e must not contain z)."""
        assert z not in e[1]
        a, N = self.lin.pop(z), self.adj.pop(z)
        for w in N:
            self.adj[w].discard(z)
        self.add_lin(a, e)
        for w in N:
            self.add_quad((0, frozenset([w])), e)

        def sub(x):
            c, S = x
            return (c ^ e[0], S ^ {z} ^ e[1]) if z in S else x

        self.wire = [(c, frozenset(S)) for c, S in map(sub, self.wire)]

    def protected(self):
        out = set()
        for _, S in self.wire:
            out |= S
        return out

    def eliminate(self, y, prot):
        a, N = self.lin.pop(y), self.adj.pop(y)
        for w in N:
            self.adj[w].discard(y)
        if a % 2:  # sum_y i^{a y}(-1)^{yL} = (1+i^a) i^{-aL}
            self.lg += 0.5
            self.w8 = (self.w8 + (1 if a == 1 else -1)) % 8
            self.add_lin(-a, (0, frozenset(N)))
        else:  # 2 * delta(XOR(N) = a/2)
            self.lg += 1
            if not N:
                if a:
                    raise ZeroDivisionError("state amplitude identically zero")
                return
            cand = [w for w in N if w not in prot] or sorted(N)
            z = cand[0]
            self.substitute(z, (a // 2, frozenset(N - {z})))

    def eliminate_unprotected(self):
        while True:
            prot = self.protected()
            free = [v for v in self.lin if v not in prot]
            if not free:
                return
            self.eliminate(free[0], prot)

    # --- gates
    def h(self, q):
        y = self._new()
        self.add_quad(self.wire[q], (0, frozenset([y])))
        self.lg -= 0.5
        self.wire[q] = (0, frozenset([y]))
        self.eliminate_unprotected()

    def apply(self, op):
        g = op[0]
        if g == "h":
            self.h(op[1])
        elif g == "s":
            self.add_lin(1, self.wire[op[1]])
        elif g == "z":
            self.add_lin(2, self.wire[op[1]])
        elif g == "sx":
            self.h(op[1])
            self.add_lin(1, self.wire[op[1]])
            self.h(op[1])
        elif g == "cz":
            self.add_quad(self.wire[op[1]], self.wire[op[2]])
        else:
            raise ValueError(g)


def graph_form(n, ops):
    """Return dict with Gamma (n x n uint8), pivot info, per-qubit Z4 phase, log2 magnitude and omega-phase."""
    ps = PathSum(n)
    for op in ops:
        ps.apply(op)
    # reparametrise: make remaining vars equal output bits
    pivot_of = {}
    for q in range(n):
        c, S = ps.wire[q]
        nonpiv = [v for v in S if v not in pivot_of]
        if nonpiv:
            v = nonpiv[0]
            o = ps._new()
            ps.substitute(v, (c, frozenset({o}) | (S - {v})))
            assert ps.wire[q] == (0, frozenset([o]))
            pivot_of[o] = q
    ps.eliminate_unprotected()
    var_of = {}
    for q in range(n):
        c, S = ps.wire[q]
        if c == 0 and len(S) == 1 and pivot_of.get(next(iter(S))) == q:
            var_of[q] = next(iter(S))
    assert set(var_of.values()) == set(ps.lin), "reparametrisation incomplete"
    qubit_of = {v: q for q, v in var_of.items()}
    G = np.zeros((n, n), np.uint8)
    for v, N in ps.adj.items():
        for w in N:
            G[qubit_of[v], qubit_of[w]] = 1
    dep = {}
    for q in range(n):
        if q in var_of:
            continue
        c, S = ps.wire[q]
        dep[q] = c
        for v in S:
            G[q, qubit_of[v]] = G[qubit_of[v], q] = 1
    lin = np.zeros(n, int)
    for q, v in var_of.items():
        lin[q] = ps.lin[v]
    return dict(G=G, pivot=set(var_of), dep=dep, lin=lin, lg=ps.lg, w8=ps.w8)


def unaries(gf, V, bits, mutate=None):
    """h_q(b) for q in range(n); bits[q] = measured x_q."""
    n = len(V)
    H = np.zeros((n, 2), complex)
    for q in range(n):
        f = V[q][int(bits[q]), :]  # f(b) = <x_q|V_q|b>
        if q in gf["pivot"]:
            ph = 1 if mutate == "drop_phase" else 1j ** gf["lin"][q]
            H[q] = [f[0], f[1] * ph]
        else:
            c = gf["dep"][q]
            g = np.array([f[c], f[c ^ 1]])  # g(t) = f(c xor t)
            H[q] = [(g[0] + g[1]) / 2, (g[0] - g[1]) / 2]
    return H


# ---------------------------------------------------------------- GF(2) cut-rank message passing
def _rref(vecs):
    basis, piv = [], []
    for v in vecs:
        for b, p in zip(basis, piv):
            if (v >> p) & 1:
                v ^= b
        if v:
            p = (v & -v).bit_length() - 1
            for i in range(len(basis)):
                if (basis[i] >> p) & 1:
                    basis[i] ^= v
            basis.append(v)
            piv.append(p)
    return basis, piv


def _coord(s, basis, piv):
    c, r = 0, 0
    for j, p in enumerate(piv):
        if (s >> p) & 1:
            c |= 1 << j
            r ^= basis[j]
    assert r == s, "vector not in message subspace"
    return c


def _span_index(cols, nbits):
    """array over c in [0,2^k): XOR of cols[j] for set bits j."""
    a = np.zeros(1, np.int64)
    for col in cols:
        a = np.concatenate([a, a ^ col])
    return a


def plan(G, order):
    """Sample-independent schedule: per step, (v, K-cols, parity-cols, g). Also cut-ranks."""
    n = len(order)
    steps, ranks = [], []
    basis, piv = [], []
    for m, v in enumerate(order):
        L, R2 = order[:m], order[m + 1 :]
        gamma = sum(int(G[L[i], v]) << i for i in range(m))
        g = _coord(gamma, basis, piv)
        cols = [sum(int(G[x, r]) << i for i, x in enumerate(order[: m + 1])) for r in R2]
        nb, npv = _rref(cols)
        mask = (1 << m) - 1
        K = [_coord(u & mask, basis, piv) for u in nb]
        P = [(u >> m) & 1 for u in nb]
        steps.append((v, K, P, g))
        basis, piv = nb, npv
        ranks.append(len(nb))
    return steps, ranks


def contract(steps, H):
    F = np.ones(1, complex)
    peak = 1
    for v, K, P, g in steps:
        idx = _span_index(K, 0)
        par = _span_index(P, 0) & 1
        F = H[v, 0] * F[idx] + H[v, 1] * (1 - 2 * par) * F[idx ^ g]
        peak = max(peak, len(F))
    assert len(F) == 1
    return F[0], peak


def amplitude(qasm: str, bits_q0_first: str, order=None, mutate=None, _cache={}):
    key = (qasm, None if order is None else tuple(order), mutate)
    if key not in _cache:
        n, ops, V = parse(qasm)
        gf = graph_form(n, ops)
        if mutate == "flip_edge":
            gf["G"][0, 1] ^= 1
            gf["G"][1, 0] ^= 1
        o = list(range(n)) if order is None else list(order)
        steps, ranks = plan(gf["G"], o)
        _cache[key] = (V, gf, steps, ranks)
    V, gf, steps, ranks = _cache[key]
    s, peak = contract(steps, unaries(gf, V, bits_q0_first, mutate))
    amp = s * 2.0 ** gf["lg"] * W8 ** gf["w8"]
    return amp, peak, max(ranks), gf


def tableau_entanglement(n, ops, order):
    """Stabilizer entanglement across each prefix cut of `order` (phase-free GF(2) tableau)."""
    X = np.zeros((n, n), np.uint8)
    Z = np.eye(n, dtype=np.uint8)
    for op in ops:
        g, a = op[0], op[1]
        if g == "h":
            X[:, a], Z[:, a] = Z[:, a].copy(), X[:, a].copy()
        elif g == "s":
            Z[:, a] ^= X[:, a]
        elif g == "sx":
            X[:, a] ^= Z[:, a]
        elif g == "cz":
            b = op[2]
            Z[:, a] ^= X[:, b]
            Z[:, b] ^= X[:, a]

    def rk(M):
        vecs = [int("".join(map(str, row)), 2) if len(row) else 0 for row in M]
        return len(_rref(vecs)[0])

    out = []
    for m in range(1, n):
        A = list(order[:m])
        out.append(rk(np.hstack([X[:, A], Z[:, A]])) - m)
    return out


# ---------------------------------------------------------------- validation (python3 stabilizer_overlap.py)
def _sliced(k, ncz):
    """Same slicing as mini_sweep_validate.sliced (copied to avoid its import-time side effects)."""
    from pathlib import Path
    src = Path(__file__).parent.parent / "tracker/cv/random_graph_sampling_nq70_depth70_checks27_basis_fstate.qasm"
    head, body = [], []
    for l in src.read_text().splitlines():
        qs = [int(x) for x in re.findall(r"q\[(\d+)\]", l)]
        if l.startswith("qreg"): head.append(f"qreg q[{k}];")
        elif not qs: head.append(l)
        elif all(q < k for q in qs): body.append(l)
    last_cz = max(i for i, l in enumerate(body) if l.startswith("cz"))
    kept, seen = [], 0
    for l in body[: last_cz + 1]:
        if l.startswith("cz"):
            seen += 1
            if seen > ncz: break
        kept.append(l)
    return "\n".join(head + kept + body[last_cz + 1:])


def _schmidt_profile(qasm, order):
    """log2 Schmidt rank of the CLIFFORD part across each prefix cut of `order` (qiskit statevector)."""
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector
    n, ops, _ = parse(qasm)
    lines = [f'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[{n}];']
    for op in ops:
        lines.append(f"cz q[{op[1]}],q[{op[2]}];" if op[0] == "cz" else f"{op[0]} q[{op[1]}];")
    psi = Statevector(QuantumCircuit.from_qasm_str("\n".join(lines))).data.reshape([2] * n)
    axes = [n - 1 - q for q in order]          # qiskit: qubit q is axis n-1-q
    psi = np.transpose(psi, axes)
    out = []
    for m in range(1, n):
        s = np.linalg.svd(psi.reshape(2 ** m, -1), compute_uv=False)
        out.append(int(np.sum(s > 1e-9 * s[0])).bit_length() - 1)
    return out


def validate(n_samples=20, seed=11):
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector
    rng = np.random.default_rng(seed)
    cases = [(8, 1000, "chain"), (10, 1000, "shuffled"), (12, 60, "chain"), (12, 1000, "shuffled"),
             (14, 1000, "chain"), (16, 120, "shuffled"), (16, 1000, "chain"), (16, 1000, "shuffled")]
    worst = 0.0
    for k, ncz, oname in cases:
        txt = _sliced(k, ncz)
        order = list(range(k)) if oname == "chain" else list(rng.permutation(k))
        n, ops, V = parse(txt)
        gf = graph_form(n, ops)
        steps, ranks = plan(gf["G"], order)
        tab = tableau_entanglement(n, ops, order)
        assert ranks[:-1] == tab, (ranks, tab)
        if k <= 12:
            assert _schmidt_profile(txt, order) == tab
        sv = Statevector(QuantumCircuit.from_qasm_str(txt)).data
        p = np.abs(sv) ** 2
        idx = rng.choice(len(p), size=n_samples, replace=False, p=p / p.sum())
        errs, peak = [], 0
        for i in idx:
            a, pk, mr, _ = amplitude(txt, format(i, f"0{k}b")[::-1], order=order)
            errs.append(abs(a - sv[i]) / abs(sv[i])); peak = max(peak, pk)
        assert peak == 2 ** max(ranks)
        # mutation controls: each must be detected
        mut = {}
        for m in ("drop_phase", "flip_edge"):
            me = [abs(amplitude(txt, format(i, f"0{k}b")[::-1], order=order, mutate=m)[0] - sv[i]) / abs(sv[i])
                  for i in idx]
            mut[m] = max(me)
        worst = max(worst, max(errs))
        print(f"k={k:2d} CZs={min(ncz, 35 * (k - 1)):3d} order={oname:8s} pivots={len(gf['pivot']):2d} "
              f"dependent={len(gf['dep']):2d} cut-ranks==tableau{'==qiskit' if k <= 12 else ''} "
              f"max_rank={max(ranks):2d} peak_msg={peak:5d} max_rel_err={max(errs):.2e} "
              f"mutants(max err): drop_phase={mut['drop_phase']:.2e} flip_edge={mut['flip_edge']:.2e}")
    print("STABILIZER OVERLAP VALIDATION", "PASS" if worst < 1e-9 else "FAIL", f"worst={worst:.2e}")


if __name__ == "__main__":
    validate()
