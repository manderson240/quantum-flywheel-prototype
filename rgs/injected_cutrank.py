"""Exact GF(2) cut-rank scorer for doped-Clifford circuits (T-gate injection), for the exactly scored design experiment.

Each T on qubit q becomes CNOT(q -> a_j) with ancilla a_j fed the magic state |A> = T|+> and projected on <0| at the end
(<0|_a CNOT |psi>|A> = T|psi>/sqrt2). The amplitude <x| C |0^n> is then sum_a Psi_x(a) prod_j <a_j|A>, where
Psi_x = (<0^n| (x) I) C'^dag |x, 0^m> is an m-qubit stabilizer state. Contracting over the ancillas in an order costs
2^(max cut-rank of Psi over that order); the cut-rank does not depend on x (Pauli frame). Phases are ignored (only the
GF(2) group structure matters for ranks). Anchors: #249 reports skeleton cut rank 31 and T-injected 36 for IBM's ring.
"""

from __future__ import annotations

import re

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Clifford


def parse_t_injected(qasm: str) -> tuple[QuantumCircuit, int, int, list[tuple[int, int]]]:
    ops = []
    n = int(re.search(r"qreg\s+q\[(\d+)\]", qasm)[1])
    for line in qasm.splitlines():
        s = line.strip()
        if not s or s.startswith(("OPENQASM", "include", "qreg", "creg", "barrier", "//")):
            continue
        g = re.match(r"([a-z]+)", s)[1]
        qs = [int(x) for x in re.findall(r"q\[(\d+)\]", s)]
        ops.append((g, qs))
    m = sum(1 for g, _ in ops if g == "t")
    qc = QuantumCircuit(n + m)
    j, tpos = 0, []
    for step, (g, qs) in enumerate(ops):
        if g == "t":
            qc.cx(qs[0], n + j)
            tpos.append((qs[0], step))
            j += 1
        elif g == "cz":
            qc.cz(*qs)
        elif g in ("h", "s", "sdg", "sx", "sxdg", "x", "z", "y"):
            getattr(qc, g)(qs[0])
        else:
            raise ValueError(f"unsupported gate {g}")
    return qc, n, m, tpos


def _rank(M: np.ndarray) -> int:
    M = M.copy()
    r = 0
    for c in range(M.shape[1]):
        pv = np.nonzero(M[r:, c])[0]
        if len(pv) == 0:
            continue
        p = r + pv[0]
        M[[r, p]] = M[[p, r]]
        rows = np.nonzero(M[:, c])[0]
        rows = rows[rows != r]
        M[rows] ^= M[r]
        r += 1
        if r == M.shape[0]:
            break
    return r


def ancilla_state(qc: QuantumCircuit, n: int, m: int) -> np.ndarray:
    """Stabilizer generators (m x 2m, [X|Z]) of Psi = (<0^n| x I) C'^dag |0^(n+m)>, phases dropped."""
    N = n + m
    cl = Clifford(qc.inverse())
    S = np.hstack([cl.stab_x, cl.stab_z]).astype(np.uint8)  # stabilizers of C'^dag|0> (no phase column)
    for i in range(n):  # post-select qubit i on |0>: Z_i joins the group; no generator keeps X on qubit i
        anti = np.nonzero(S[:, i])[0]
        if len(anti):
            g = anti[0]
            for r in anti[1:]:
                S[r] ^= S[g]
            S[g] = 0
            S[g, N + i] = 1
    # every row now has X_i = 0 (i < n) and Z_i is in the group, so clearing Z_i bits multiplies by group elements
    S[:, N:N + n] = 0
    T = np.concatenate([S[:, n:N], S[:, N + n:]], axis=1)
    T = T[np.any(T, 1)]
    rows = _independent_rows(T, m)
    assert len(rows) == m, f"ancilla state has {len(rows)} independent generators, expected {m}"
    return T[rows]


def _independent_rows(T, m):
    rows, M = [], np.zeros((0, T.shape[1]), np.uint8)
    for i in range(len(T)):
        if _rank(np.vstack([M, T[i]])) > len(rows):
            rows.append(i)
            M = np.vstack([M, T[i]])
        if len(rows) == m:
            break
    return rows


def max_cutrank(S: np.ndarray, order: list[int]) -> tuple[int, list[int]]:
    m = S.shape[1] // 2
    prof = []
    for c in range(1, m):
        A = order[:c]
        prof.append(_rank(S[:, list(A) + [m + a for a in A]]) - c)
    return max(prof), prof
