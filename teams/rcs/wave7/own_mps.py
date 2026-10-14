"""Own numpy MPS (independent of BlueQubit): chain order = logical qubit index, non-adjacent CZ routed by SWAPs
(move the right qubit down to a+1, apply, move back). Every 2-site update is an SVD truncated to chi (and singular
values <= 1e-10 * s_max dropped), then renormalised. Mixed-canonical form, so the norm is exact. Returns the
exact survival probability |<x|psi_trunc>|^2 of the truncated state (no sampling)."""
from __future__ import annotations
import math
import numpy as np

CZ = np.diag([1, 1, 1, -1]).astype(complex)
SWAP = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], complex)


def rx(t):
    c, s = math.cos(t / 2), math.sin(t / 2)
    return np.array([[c, -1j * s], [-1j * s, c]])


def rz(t):
    return np.array([[np.exp(-0.5j * t), 0], [0, np.exp(0.5j * t)]])


class MPS:
    def __init__(self, bits, chi):
        self.n, self.chi = len(bits), chi
        self.A = []
        for b in bits:
            t = np.zeros((1, 2, 1), complex); t[0, b, 0] = 1.0; self.A.append(t)
        self.c = 0
        self.discarded = 0.0  # sum over truncations of discarded weight (for the record)
        self.max_bond = 1

    def g1(self, U, q):
        self.A[q] = np.einsum("ab,ibj->iaj", U, self.A[q])

    def _move(self, target):
        while self.c < target:
            a = self.A[self.c]; l, p, r = a.shape
            Q, R = np.linalg.qr(a.reshape(l * p, r))
            self.A[self.c] = Q.reshape(l, p, -1)
            self.A[self.c + 1] = np.einsum("ab,bpj->apj", R, self.A[self.c + 1]); self.c += 1
        while self.c > target:
            a = self.A[self.c]; l, p, r = a.shape
            Q, R = np.linalg.qr(a.reshape(l, p * r).T)
            self.A[self.c] = Q.T.reshape(-1, p, r)
            self.A[self.c - 1] = np.einsum("ipb,ab->ipa", self.A[self.c - 1], R); self.c -= 1

    def g2adj(self, U4, i):
        """Apply 4x4 gate on sites (i, i+1), U4 indexed (out_i out_j, in_i in_j)."""
        self._move(i)
        a, b = self.A[i], self.A[i + 1]
        th = np.einsum("apb,bqc->apqc", a, b)
        l, _, _, r = th.shape
        th = np.einsum("xypq,apqc->axyc", U4.reshape(2, 2, 2, 2), th).reshape(l * 2, 2 * r)
        try:
            u, s, vh = np.linalg.svd(th, full_matrices=False)
        except np.linalg.LinAlgError:  # DEVIATIONS D3: gesdd non-convergence -> LAPACK gesvd (same decomposition)
            import scipy.linalg
            u, s, vh = scipy.linalg.svd(th, full_matrices=False, lapack_driver="gesvd")
            self.svd_fallbacks = getattr(self, "svd_fallbacks", 0) + 1
        keep = int(min(self.chi, np.count_nonzero(s > 1e-10 * s[0])))
        tot = float((s ** 2).sum())
        self.discarded += float((s[keep:] ** 2).sum()) / tot
        s = s[:keep] / math.sqrt(float((s[:keep] ** 2).sum()))
        self.A[i] = u[:, :keep].reshape(l, 2, keep)
        self.A[i + 1] = (s[:, None] * vh[:keep]).reshape(keep, 2, r)
        self.c = i + 1
        self.max_bond = max(self.max_bond, keep)

    def cz(self, a, b):
        a, b = min(a, b), max(a, b)
        for k in range(b - 1, a, -1):
            self.g2adj(SWAP, k)
        self.g2adj(CZ, a)
        for k in range(a + 1, b):
            self.g2adj(SWAP, k)

    def amplitude(self, bits):
        v = np.ones((1,), complex)
        for t, x in zip(self.A, bits):
            v = v @ t[:, x, :]
        return complex(v[0])


def run_ops(ops, bits, chi, n=None):
    """Prepare |bits> by rx(pi) flips (matching the device's input layer), apply ops, return exact survival."""
    n = n or len(bits)
    m = MPS([0] * n, chi)
    for q, x in enumerate(bits):
        if x: m.g1(rx(math.pi), q)
    for g in ops:
        if g[0] == "cz": m.cz(g[1], g[2])
        elif g[0] == "rx": m.g1(rx(g[1]), g[2])
        else: m.g1(rz(g[1]), g[2])
    amp = m.amplitude(bits)
    return {"survival": abs(amp) ** 2, "max_bond": m.max_bond, "sum_discarded": m.discarded,
            "svd_fallbacks": getattr(m, "svd_fallbacks", 0)}


def statevector_survival(ops, bits):
    n = len(bits)
    psi = np.zeros([2] * n, complex); psi[(0,) * n] = 1.0
    def ap1(U, q):
        nonlocal psi
        psi = np.moveaxis(np.tensordot(U, psi, axes=([1], [q])), 0, q)
    for q, x in enumerate(bits):
        if x: ap1(rx(math.pi), q)
    for g in ops:
        if g[0] == "cz":
            idx = [slice(None)] * n; idx[g[1]] = 1; idx[g[2]] = 1; psi[tuple(idx)] *= -1
        elif g[0] == "rx": ap1(rx(g[1]), g[2])
        else: ap1(rz(g[1]), g[2])
    return abs(psi[tuple(bits)]) ** 2, psi


def restrict(ops, n):
    """Keep only gates acting inside qubits [0, n). Restriction preserves the mirror (U U^dagger) structure."""
    return [g for g in ops if (g[0] == "cz" and g[1] < n and g[2] < n) or (g[0] != "cz" and g[2] < n)]
