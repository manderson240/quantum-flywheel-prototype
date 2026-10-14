"""Exact oracle for the tracker's Floquet mixed-field Ising family, at a size where the truth is computable.

Same gate content as the 51-qubit tracker candidate (RX(θx/3), RZ(θz/3) on every qubit, then RZZ(π/3) on one of
three edge layers, 3 layers per cycle, θx=1.56567, θz=0.33879), on a 19-qubit heavy-hex patch (Qiskit
heavy-hex distance 3). The 3-layer edge partition is a proper 3-edge-colouring (heavy-hex is bipartite with max
degree 3, so one exists). Exact local statevector vs BlueQubit Pauli-path and MPS, cycles 1..16.
Run: python floquet_oracle19.py   (API token read inside the process, never printed)
"""

from __future__ import annotations

import json
import math
import random
import time
from collections import deque

from kicked_ising_crosscheck import OUT, exact_mean_z, load_token
from qiskit import QuantumCircuit
from qiskit.transpiler import CouplingMap


TX, TZ, TZZ = 1.56567, 0.33879, math.pi / 3  # defaults = tracker values; override via CLI


def lattice() -> tuple[int, list[tuple[int, int]]]:
    cm = CouplingMap.from_heavy_hex(3, bidirectional=False)
    return cm.size(), sorted({tuple(sorted(e)) for e in cm.get_edges()})


def three_colour(edges: list[tuple[int, int]], seed: int = 0) -> list[list[tuple[int, int]]]:
    rng = random.Random(seed)
    for _ in range(10_000):
        order = edges[:]
        rng.shuffle(order)
        col: dict[tuple[int, int], int] = {}
        ok = True
        for a, b in order:
            used = {c for e, c in col.items() if a in e or b in e}
            free = [c for c in range(3) if c not in used]
            if not free:
                ok = False
                break
            col[(a, b)] = free[0]
        if ok:
            return [[e for e in edges if col[e] == k] for k in range(3)]
    raise RuntimeError("no 3-edge-colouring found")


def pairs_at(n: int, edges: list[tuple[int, int]], d: int) -> list[tuple[int, int]]:
    adj = {i: [] for i in range(n)}
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    out = []
    for s in range(n):
        dist, dq = {s: 0}, deque([s])
        while dq:
            u = dq.popleft()
            for v in adj[u]:
                if v not in dist:
                    dist[v] = dist[u] + 1
                    dq.append(v)
        out += [(s, t) for t, dd in dist.items() if t > s and dd == d]
    return out


def circuit(n: int, layers, cycles: int, tx: float = TX, tz: float = TZ) -> QuantumCircuit:
    qc = QuantumCircuit(n)
    for _ in range(cycles):
        for lay in layers:
            for q in range(n):
                qc.rx(tx / 3, q)
                qc.rz(tz / 3, q)
            for a, b in lay:
                qc.rzz(TZZ, a, b)
    return qc


def zlabel(n: int, qs) -> str:
    s = ["I"] * n
    for q in qs:
        s[n - 1 - q] = "Z"
    return "".join(s)


def main() -> int:
    import argparse

    import bluequbit

    ap = argparse.ArgumentParser()
    ap.add_argument("--tx", type=float, default=TX)
    ap.add_argument("--tz", type=float, default=TZ)
    ap.add_argument("--colour-seed", type=int, default=0)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    n, edges = lattice()
    layers = three_colour(edges, a.colour_seed)
    assert sum(map(len, layers)) == len(edges)
    obs = {"mag": [(zlabel(n, (i,)), 1.0 / n) for i in range(n)]}
    for d in (2, 3):
        p = pairs_at(n, edges, d)
        obs[f"zzd{d}"] = [(zlabel(n, pr), 1.0 / len(p)) for pr in p]
    bq = bluequbit.init(load_token())
    out = OUT / f"floquet_oracle19{a.tag}.json"
    rows = []
    for cyc in (1, 2, 3, 4, 6, 8, 10, 13, 16):
        qc = circuit(n, layers, cyc, a.tx, a.tz)
        for ob, terms in obs.items():
            row = {"n": n, "cycles": cyc, "obs": ob, "tx": a.tx, "tz": a.tz, "colour_seed": a.colour_seed,
                   "exact": exact_mean_z(qc, terms)}
            for dev, key, vals in (
                ("pauli-path", "pauli_path_truncation_threshold", (1e-3, 1e-4)),
                ("mps.cpu", "mps_bond_dimension", (16, 64)),
            ):
                for v in vals:
                    t0 = time.time()
                    try:
                        r = bq.run(qc, device=dev, pauli_sum=terms, options={key: v})
                        row[f"{dev[:3]}_{v:g}"] = float(r.expectation_value)
                    except Exception as e:
                        row[f"{dev[:3]}_{v:g}"] = None
                        row[f"{dev[:3]}_{v:g}_err"] = str(e)[:160]
                    row[f"{dev[:3]}_{v:g}_s"] = round(time.time() - t0, 1)
            rows.append(row)
            out.write_text(json.dumps(rows, indent=1))
            print(
                json.dumps(
                    {k: (round(x, 4) if isinstance(x, float) else x) for k, x in row.items()}
                ),
                flush=True,
            )
    print("saved", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
