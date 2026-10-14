"""Instrument controls C1-C4 from PREREG.md (must pass before scoring)."""
import itertools, json, sys
import numpy as np
sys.path.insert(0, "/home/mike-anderson/cohezion-labs/bluequbit-flywheel")
sys.path.insert(0, "/home/mike-anderson/cohezion-labs/bluequbit-flywheel/teams/floquet/scripts")
import nlce
from floquet_patch_oracle import patch, build
from qiskit.quantum_info import Statevector, SparsePauliOp

L51 = nlce.lattice51()
res = {}
n33 = nlce.patch_nodes(33)
assert n33 == nlce.bfs_nodes(33) and nlce.patch_nodes(27) == nlce.bfs_nodes(27)
adj33 = nlce.adjacency(n33, nlce.induced(n33, L51))
# find a loop-containing connected subgraph <= 14 sites: grow BFS ball inside patch33 until edges >= nodes
ne = lambda ns: sum(len(l) for l in nlce.induced(ns, L51))
# find a cycle via BFS parent pointers (non-tree edge), then pad with neighbours up to 14 sites
par = {n33[0]: None}; dq=[n33[0]]; cyc_edge=None
for u in dq:
    for v in sorted(adj33[u]):
        if v not in par: par[v]=u; dq.append(v)
        elif par[u]!=v and cyc_edge is None: cyc_edge=(u,v)
def path(x):
    out=[]
    while x is not None: out.append(x); x=par[x]
    return out
pu, pv = path(cyc_edge[0]), path(cyc_edge[1])
lca = next(x for x in pu if x in pv)
ring = pu[:pu.index(lca)+1] + pv[:pv.index(lca)]
loopsub = list(dict.fromkeys(ring))
for u in list(loopsub):
    for v in sorted(adj33[u]):
        if len(loopsub) < 14 and v not in loopsub: loopsub.append(v)
loopsub = sorted(loopsub)
print("loop subgraph", len(loopsub), "edges", ne(loopsub))

# C4 enumeration: ESU vs brute force
sub_adj = nlce.adjacency(loopsub, nlce.induced(loopsub, L51))
def connected(s):
    s = set(s); st = [next(iter(s))]; seen = {st[0]}
    while st:
        u = st.pop()
        for v in sub_adj[u]:
            if v in s and v not in seen: seen.add(v); st.append(v)
    return len(seen) == len(s)
brute = {frozenset(c) for m in range(1, len(loopsub)+1) for c in itertools.combinations(loopsub, m) if connected(c)}
e = nlce.esu(loopsub, sub_adj, len(loopsub))
res["C4"] = dict(esu=len(e), esu_unique=len(set(e)), brute=len(brute), ok=(len(e) == len(set(e)) and set(e) == brute))
print("C4", res["C4"])

# C1 same constructor: qiskit Statevector on floquet_patch_oracle.build with induced local layers
def qiskit_z(cluster, cyc):
    qs = sorted(cluster); idx = {q: i for i, q in enumerate(qs)}
    lays = [[(idx[a], idx[b]) for a, b in lay] for lay in nlce.induced(qs, L51)]
    sv = Statevector.from_instruction(build(len(qs), lays, cyc))
    k = len(qs)
    return np.array([sv.expectation_value(SparsePauliOp("".join("Z" if k-1-j == i else "I" for j in range(k)))).real for i in range(k)])
clus = [loopsub[:1], sorted(e[5]), sorted(loopsub), sorted([c for c in e if len(c) == 7][0]), sorted([c for c in e if len(c) == 10][-1])]
maxd = 0
for c in clus:
    sim = nlce.simulate(c, L51, 5)
    for cyc in (1, 2, 5):
        maxd = max(maxd, float(np.max(np.abs(sim[cyc-1] - qiskit_z(c, cyc)))))
res["C1"] = dict(max_abs_diff=maxd, ok=maxd < 1e-8, sizes=[len(c) for c in clus])
print("C1", res["C1"])

# C2 full-order identity on loop subgraph
P = {c: nlce.simulate(c, L51).sum(axis=1) for c in e}
S, W = nlce.nlce_orders(loopsub, P, len(loopsub))
direct = P[frozenset(loopsub)]
d2 = float(np.max(np.abs(S[-1] - direct)))
res["C2"] = dict(n=len(loopsub), max_abs_diff=d2, ok=d2 < 1e-9)
print("C2", res["C2"])

# C3 oracle19 reproduction on its own lattice/colouring
import floquet_oracle19 as o19
n19, edges = o19.lattice(); cols = o19.three_colour(edges)
rows = json.load(open("results/floquet_oracle19.json"))
tgt = {r["cycles"]: r["exact"] for r in rows if r["obs"] == "mag"}
# generic simulator on arbitrary layers: reuse nlce.simulate by monkeypatching induced
qs = list(range(n19))
orig = nlce.induced
nlce.induced = lambda nodes, L: [[(a, b) for a, b in lay] for lay in cols]
z = nlce.simulate(qs, None, max(tgt))
nlce.induced = orig
d3 = max(abs(z[c-1].mean() - v) for c, v in tgt.items())
res["C3"] = dict(cycles=sorted(tgt), max_abs_diff=float(d3), ok=bool(d3 < 1e-6))
print("C3", res["C3"])
res["all_ok"] = all(res[k]["ok"] for k in ("C1", "C2", "C3", "C4"))
json.dump(res, open("teams/floquet/results/controls.json", "w"), indent=1)
print("ALL OK", res["all_ok"])
