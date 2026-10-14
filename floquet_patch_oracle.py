"""Intermediate-size oracle for the tracker's 51-qubit Floquet candidate (referee request: validate the Pauli-path/MPS
bracket between 19 and 51 qubits).

Patches are connected induced subgraphs of the tracker's OWN 51-qubit heavy-hex lattice (BFS ball around a central
qubit), keeping the tracker's own three RZZ edge layers restricted to the patch, and the tracker angles. Truth = BlueQubit
statevector (device="cpu", <= 34 qubits; exact expectation of the Pauli sum, checked against a local statevector on the
19-qubit control). Compared with Pauli-path (delta 1e-3, 1e-4) and MPS (chi 64, 256). Remote compute only: at n=33 a
local statevector would need 128 GiB.
Run: python floquet_patch_oracle.py --n 27 [--control]   (token read in-process, never printed)
"""

from __future__ import annotations

import argparse
import json
import math
import time
from collections import deque

import floquet_tracker as ft
from floquet_oracle19 import (
    circuit as _unused,  # noqa: F401  (same gate content; re-implemented below for patches)
)
from kicked_ising_crosscheck import OUT, exact_mean_z, load_token
from qiskit import QuantumCircuit


TX, TZ, TZZ = 1.56567, 0.33879, math.pi / 3
CYCLES = (1, 2, 4, 8, 13, 16)


def patch(n: int) -> tuple[list[int], list[list[tuple[int, int]]]]:
    layers, _ = ft.readme_spec()
    edges = sorted(set().union(*layers))
    adj = {q: set() for q in range(ft.N)}
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)

    # centre = qubit minimising eccentricity; BFS order from it (deterministic: ties by index)
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
    keep = sorted(bfs(centre)[1][:n])
    idx = {q: i for i, q in enumerate(keep)}
    sub = [[(idx[a], idx[b]) for a, b in lay if a in idx and b in idx] for lay in layers]
    return keep, sub


def build(n_local: int, layers, cycles: int) -> QuantumCircuit:
    qc = QuantumCircuit(n_local)
    for _ in range(cycles):
        for lay in layers:
            for q in range(n_local):
                qc.rx(TX / 3, q)
                qc.rz(TZ / 3, q)
            for a, b in lay:
                qc.rzz(TZZ, a, b)
    return qc


def zlabel(n: int, qs) -> str:
    s = ["I"] * n
    for q in qs:
        s[n - 1 - q] = "Z"
    return "".join(s)


def pairs_at(n, layers, d):
    adj = {i: set() for i in range(n)}
    for lay in layers:
        for a, b in lay:
            adj[a].add(b)
            adj[b].add(a)
    out = []
    for s in range(n):
        dist, dq = {s: 0}, deque([s])
        while dq:
            u = dq.popleft()
            for v in adj[u]:
                if v not in dist:
                    dist[v] = dist[u] + 1
                    dq.append(v)
        out += [(s, t) for t, k in dist.items() if k == d and t > s]
    return out


def observables(n, layers):
    obs = {"mag": [(zlabel(n, (i,)), 1.0 / n) for i in range(n)]}
    for d in (2, 3):
        p = pairs_at(n, layers, d)
        obs[f"zzd{d}"] = [(zlabel(n, pr), 1.0 / len(p)) for pr in p]
    return obs


def main() -> int:
    import bluequbit

    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument(
        "--control", action="store_true", help="one 19q job: BlueQubit cpu vs local exact"
    )
    a = ap.parse_args()
    bq = bluequbit.init(load_token())
    keep, layers = patch(a.n)
    n = len(keep)
    obs = observables(n, layers)
    if a.control:
        qc = build(n, layers, 4)
        r = bq.run(qc, device="cpu", pauli_sum=obs["zzd2"])
        loc = exact_mean_z(qc, obs["zzd2"])
        print(
            json.dumps(
                {
                    "n": n,
                    "bq_cpu": float(r.expectation_value),
                    "local_exact": loc,
                    "abs_diff": abs(float(r.expectation_value) - loc),
                    "cost": getattr(r, "cost", None),
                }
            )
        )
        return 0
    out = OUT / f"floquet_patch{n}.json"
    rows = json.loads(out.read_text()) if out.exists() else []
    done = {(r["cycles"], r["obs"]) for r in rows}
    for cyc in CYCLES:
        qc = build(n, layers, cyc)
        for ob, terms in obs.items():
            if (cyc, ob) in done:
                continue
            row = {"n": n, "qubits": keep, "cycles": cyc, "obs": ob, "n_terms": len(terms)}
            for dev, key, v in (
                ("cpu", None, None),
                ("pauli-path", "pauli_path_truncation_threshold", 1e-3),
                ("pauli-path", "pauli_path_truncation_threshold", 1e-4),
                ("mps.cpu", "mps_bond_dimension", 64),
                ("mps.cpu", "mps_bond_dimension", 256),
            ):
                name = "exact" if dev == "cpu" else f"{dev[:3]}_{v:g}"
                t0 = time.time()
                try:
                    r = bq.run(
                        qc, device=dev, pauli_sum=terms, **({"options": {key: v}} if key else {})
                    )
                    row[name] = float(r.expectation_value)
                    row[name + "_cost"] = getattr(r, "cost", None)
                except Exception as e:
                    row[name] = None
                    row[name + "_err"] = str(e)[:200]
                row[name + "_s"] = round(time.time() - t0, 1)
            rows.append(row)
            out.write_text(json.dumps(rows, indent=1))
            print(
                json.dumps(
                    {
                        k: (round(x, 4) if isinstance(x, float) else x)
                        for k, x in row.items()
                        if k != "qubits"
                    }
                ),
                flush=True,
            )
    print("saved", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
