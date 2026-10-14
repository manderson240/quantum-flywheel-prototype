"""Count connected induced subgraphs (by size) of the 27q/33q BFS patches of the tracker's 51q lattice."""
import sys, collections
sys.path.insert(0, "/home/mike-anderson/cohezion-labs/bluequbit-flywheel")
from floquet_patch_oracle import patch

def enum_connected(n, adj, kmax):
    # standard ESU-like enumeration: each connected set counted once (extend only with vertices > root)
    out = collections.Counter()
    sets = []
    def extend(sub, ext, root):
        out[len(sub)] += 1
        sets.append(frozenset(sub))
        if len(sub) == kmax: return
        ext = set(ext)
        while ext:
            w = ext.pop()
            new_ext = ext | {u for u in adj[w] if u > root and u not in sub and all(u not in adj[s] and u != s for s in sub)}
            extend(sub | {w}, new_ext, root)
    for v in range(n):
        extend({v}, {u for u in adj[v] if u > v}, v)
    return out, sets

for N in (27, 33):
    keep, layers = patch(N)
    adj = {i: set() for i in range(N)}
    for lay in layers:
        for a, b in lay: adj[a].add(b); adj[b].add(a)
    ne = sum(len(l) for l in layers)
    deg = collections.Counter(len(adj[i]) for i in range(N))
    c, _ = enum_connected(N, adj, int(sys.argv[1]) if len(sys.argv) > 1 else 14)
    print(N, "edges", ne, "loops", ne - N + 1, "deg", dict(deg), dict(sorted(c.items())), "total", sum(c.values()))
