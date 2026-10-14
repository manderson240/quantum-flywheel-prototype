"""Geometry only (no dynamics, no truth data): backward causal-cone size of each Z_i in the BFS patches, per cycle.
Used to state the cone-based expectation in PREREG.md before any NLCE data exist."""
import sys, json
sys.path.insert(0, "/home/mike-anderson/cohezion-labs/bluequbit-flywheel")
from floquet_patch_oracle import patch
res = {}
for N in (27, 33, 51):
    keep, layers = patch(N)
    rows = {}
    for c in range(1, 11):
        sizes = []
        for i in range(N):
            S = {i}
            for _ in range(c):
                for lay in reversed(layers):
                    add = set()
                    for a, b in lay:
                        if a in S or b in S: add |= {a, b}
                    S |= add
            sizes.append(len(S))
        rows[c] = (min(sizes), round(sum(sizes)/N, 1), max(sizes))
    res[N] = rows
    print(N, rows)
json.dump(res, open("/home/mike-anderson/cohezion-labs/bluequbit-flywheel/teams/floquet/results/cone_geometry.json", "w"), indent=1)
