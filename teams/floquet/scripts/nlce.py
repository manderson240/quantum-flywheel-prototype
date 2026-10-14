"""Site-based NLCE for the tracker's Floquet mixed-field Ising patches (floquet team, wave 1; PREREG.md sha16 8cc7cc4f71c11fdc).

Clusters = connected induced subgraphs of patch(n) (global qubit ids of the tracker's 51q lattice), edge layers restricted
as floquet_patch_oracle.patch does. Gates identical to floquet_patch_oracle.build. Local numpy statevector, <= 16 sites.
"""

from __future__ import annotations

import math
import sys
from collections import deque

import numpy as np


sys.path.insert(0, "/home/mike-anderson/cohezion-labs/bluequbit-flywheel")
import floquet_tracker as ft


TX, TZ, TZZ = 1.56567, 0.33879, math.pi / 3
TMAX = 30


def lattice51():
    layers, _ = ft.readme_spec()
    return [sorted(l) for l in layers]


def patch_nodes(n: int) -> list[int]:
    """Same node set as floquet_patch_oracle.patch(n), in global ids (re-derived there; checked in controls)."""
    from floquet_patch_oracle import patch

    return patch(n)[0]


def induced(nodes, layers51):
    s = set(nodes)
    return [[(a, b) for a, b in lay if a in s and b in s] for lay in layers51]


def adjacency(nodes, layers):
    adj = {q: set() for q in nodes}
    for lay in layers:
        for a, b in lay:
            adj[a].add(b)
            adj[b].add(a)
    return adj


def esu(nodes, adj, kmax):
    """All connected induced subsets of size <= kmax, each exactly once (Wernicke ESU)."""
    order = {v: i for i, v in enumerate(sorted(nodes))}
    out = []

    def extend(sub, nbhd, ext, root):
        out.append(frozenset(sub))
        if len(sub) == kmax:
            return
        ext = list(ext)
        while ext:
            w = ext.pop()
            new = [u for u in adj[w] if order[u] > order[root] and u not in sub and u not in nbhd]
            extend(sub | {w}, nbhd | adj[w] | {w}, ext + new, root)

    for v in sorted(nodes):
        extend({v}, adj[v] | {v}, [u for u in adj[v] if order[u] > order[v]], v)
    return out


_U1 = None


def _u1():
    global _U1
    if _U1 is None:
        a, b = TX / 3 / 2, TZ / 3 / 2
        rx = np.array([[math.cos(a), -1j * math.sin(a)], [-1j * math.sin(a), math.cos(a)]])
        rz = np.diag([np.exp(-1j * b), np.exp(1j * b)])
        _U1 = rz @ rx  # RX first, then RZ
    return _U1


def simulate(cluster, layers51, tmax=TMAX):
    """Return array [tmax, k] of <Z_q>(t) for sorted cluster qubits, t = 1..tmax."""
    qs = sorted(cluster)
    k = len(qs)
    idx = {q: i for i, q in enumerate(qs)}
    lays = [[(idx[a], idx[b]) for a, b in lay] for lay in induced(qs, layers51)]
    bits = ((np.arange(2**k)[:, None] >> (k - 1 - np.arange(k))[None, :]) & 1).astype(np.int8)
    zval = 1 - 2 * bits  # axis i of the reshaped tensor = qubit i
    diags = []
    for lay in lays:
        ph = np.zeros(2**k)
        for a, b in lay:
            ph += zval[:, a] * zval[:, b]
        diags.append(np.exp(-1j * TZZ / 2 * ph))
    psi = np.zeros(2**k, complex)
    psi[0] = 1.0
    U = _u1()
    out = np.empty((tmax, k))
    for t in range(tmax):
        for d in diags:
            st = psi.reshape((2,) * k)
            for i in range(k):
                st = np.moveaxis(np.tensordot(U, st, axes=([1], [i])), 0, i)
            psi = st.reshape(-1) * d
        p = np.abs(psi) ** 2
        out[t] = p @ zval
    return out


def nlce_orders(nodes, P, kmax):
    """P: dict frozenset -> total sum_i <Z_i>(t) array [T]. Returns S_K (sum, not /n) for K = 1..kmax."""
    layers51 = lattice51()
    W = {}
    by_size = sorted(P, key=len)
    for c in by_size:
        if len(c) > kmax:
            continue
        sub_adj = adjacency(c, induced(c, layers51))
        w = P[c].copy()
        if len(c) > 1:
            for s in esu(c, sub_adj, len(c) - 1):
                w -= W[s]
        W[c] = w
    T = next(iter(P.values())).shape[0]
    S = np.zeros((kmax + 1, T))
    for c, w in W.items():
        S[len(c)] += w
    return np.cumsum(S, axis=0)[1:], W


def bfs_nodes(n: int) -> list[int]:
    """Independent re-derivation of patch(n) (used as a cross-check in controls)."""
    layers = lattice51()
    adj = {q: set() for q in range(ft.N)}
    for lay in layers:
        for a, b in lay:
            adj[a].add(b)
            adj[b].add(a)

    def bfs(s):
        dist, dq, order = {s: 0}, deque([s]), [s]
        while dq:
            u = dq.popleft()
            for v in sorted(adj[u]):
                if v not in dist:
                    dist[v] = dist[u] + 1
                    dq.append(v)
                    order.append(v)
        return dist, order

    centre = min(range(ft.N), key=lambda s: (max(bfs(s)[0].values()), s))
    return sorted(bfs(centre)[1][:n])
