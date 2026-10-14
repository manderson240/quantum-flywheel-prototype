"""Does qubit ORDERING alone close the MPS gap on heavy-hex kicked Ising?

Mean magnetization is invariant under qubit relabelling, so the only thing that changes between
orderings is the 1D chain the MPS runs along. Orderings compared:
  native  - Qiskit heavy-hex index order (the ordering behind results/mps_chi_sweep_3pi8.json)
  rcm     - reverse Cuthill-McKee (bandwidth-minimising) on the coupling graph
  random  - a fixed-seed random permutation (control: ordering can also HURT)
Ground truth: local exact statevector (independent of BlueQubit).

Run: python mps_ordering_sweep.py [--thetas 3pi8,pi4]
The API token is read from .env inside the process and never printed.
"""

from __future__ import annotations

import argparse
import json
import math
import time

import numpy as np
from kicked_ising_crosscheck import (
    OUT,
    exact_mean_z,
    heavy_hex_edges,
    kicked_ising,
    load_token,
    mean_z_terms,
)
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import reverse_cuthill_mckee


THETAS = {"pi8": math.pi / 8, "pi4": math.pi / 4, "3pi8": 3 * math.pi / 8}


def orderings(n: int, edges: list[tuple[int, int]]) -> dict[str, list[int]]:
    rows = [a for a, b in edges] + [b for a, b in edges]
    cols = [b for a, b in edges] + [a for a, b in edges]
    adj = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
    rcm = [int(i) for i in reverse_cuthill_mckee(adj, symmetric_mode=True)]
    rnd = [int(i) for i in np.random.default_rng(0).permutation(n)]
    return {"native": list(range(n)), "rcm": rcm, "random": rnd}


def relabel(edges: list[tuple[int, int]], order: list[int]) -> list[tuple[int, int]]:
    pos = {old: new for new, old in enumerate(order)}  # chain position of each original qubit
    return [(pos[a], pos[b]) for a, b in edges]


def bandwidth(edges: list[tuple[int, int]]) -> int:
    return max(abs(a - b) for a, b in edges)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--distance", type=int, default=3)
    ap.add_argument("--steps", type=int, default=5)
    ap.add_argument("--thetas", default="3pi8,pi4")
    ap.add_argument("--chis", default="8,16,32,64,128")
    a = ap.parse_args()

    import bluequbit

    bq = bluequbit.init(load_token())
    n, edges = heavy_hex_edges(a.distance)
    terms = mean_z_terms(n)  # permutation-invariant observable
    orders = orderings(n, edges)
    chis = [int(c) for c in a.chis.split(",")]
    report = {"n": n, "steps": a.steps, "bandwidth": {}, "runs": []}

    for name, order in orders.items():
        report["bandwidth"][name] = bandwidth(relabel(edges, order))
    print("bandwidth by ordering:", report["bandwidth"])

    for tkey in a.thetas.split(","):
        th = THETAS[tkey]
        exact = None
        for name, order in orders.items():
            qc = kicked_ising(n, relabel(edges, order), th, a.steps)
            if exact is None:
                exact = exact_mean_z(qc, terms)
            else:  # oracle self-check: relabelling must not change the exact answer
                assert abs(exact_mean_z(qc, terms) - exact) < 1e-9, "relabel changed exact <M>"
            for chi in chis:
                t0 = time.time()
                r = bq.run(
                    qc, device="mps.cpu", pauli_sum=terms, options={"mps_bond_dimension": chi}
                )
                val = float(r.expectation_value)
                row = {
                    "theta": tkey,
                    "order": name,
                    "chi": chi,
                    "mps": val,
                    "exact": exact,
                    "abs_err": abs(val - exact),
                    "cost": getattr(r, "cost", None),
                    "wall_s": round(time.time() - t0, 1),
                }
                report["runs"].append(row)
                print(
                    json.dumps(
                        {k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()}
                    )
                )

    out = OUT / f"mps_ordering_hh{a.distance}_s{a.steps}.json"
    out.write_text(json.dumps(report, indent=1))
    print("saved", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
