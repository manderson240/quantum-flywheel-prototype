"""Toy version of the live Track-02 target: OTOC echo circuits (Google 'Quantum Echoes' class).

Echo circuit on |0...0>:  U  ->  X on butterfly qubit b  ->  U^dagger  ->  measure <Z_m>.
Because |0...0> is a +1 eigenstate of Z_m, <Z_m> here equals the OTOC <Z_m B(t) Z_m B(t)>, with
B(t) = U^dagger X_b U. U = `cycles` layers of random single-qubit gates from {sqrt X, sqrt Y, sqrt W}
(Google's set; only sqrt W is non-Clifford) + CZ on alternating grid-edge patterns.

Ground truth: local exact statevector (independent of BlueQubit). Challengers: BlueQubit Pauli-path
(threshold sweep) and MPS (bond-dimension sweep). Toy scale only (4x4 = 16 qubits); the real
circuits (Zenodo 15640503, 65+ qubits) are the proposal's target, not this script's.

Run: python otoc_echo_toy.py
The API token is read from .env inside the process and never printed.
"""

from __future__ import annotations

import argparse
import json
import math
import time

import numpy as np
from kicked_ising_crosscheck import OUT, exact_mean_z, load_token
from qiskit import QuantumCircuit


def grid_edges(rows: int, cols: int) -> list[list[tuple[int, int]]]:
    """Four CZ layer patterns (horizontal even/odd, vertical even/odd), cycled like Google's ABCD."""
    q = lambda r, c: r * cols + c  # noqa: E731
    pats: list[list[tuple[int, int]]] = [[], [], [], []]
    for r in range(rows):
        for c in range(cols - 1):
            pats[c % 2].append((q(r, c), q(r, c + 1)))
    for r in range(rows - 1):
        for c in range(cols):
            pats[2 + r % 2].append((q(r, c), q(r + 1, c)))
    return pats


def sqrt_gate(qc: QuantumCircuit, kind: int, q: int) -> None:
    if kind == 0:
        qc.rx(math.pi / 2, q)  # sqrt X (Clifford)
    elif kind == 1:
        qc.ry(math.pi / 2, q)  # sqrt Y (Clifford)
    else:  # sqrt W, W = (X+Y)/sqrt2 (non-Clifford)
        qc.rz(-math.pi / 4, q)
        qc.rx(math.pi / 2, q)
        qc.rz(math.pi / 4, q)


def random_u(n: int, pats, cycles: int, rng) -> tuple[QuantumCircuit, int]:
    u = QuantumCircuit(n)
    prev = [-1] * n
    n_w = 0
    for k in range(cycles):
        for q in range(n):
            kind = int(
                rng.choice([g for g in (0, 1, 2) if g != prev[q]])
            )  # no repeats, as in Google
            prev[q] = kind
            n_w += kind == 2
            sqrt_gate(u, kind, q)
        for a, b in pats[k % 4]:
            u.cz(a, b)
    return u, n_w


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=4)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--cycles", default="2,4,6,8,10,12")
    ap.add_argument("--thresholds", default="1e-2,1e-3,1e-4")
    ap.add_argument("--chis", default="4,16,64")
    ap.add_argument("--seeds", default="7")
    ap.add_argument(
        "--order",
        type=int,
        default=1,
        choices=(1, 2),
        help="1: OTOC; 2: OTOC^2 (Google's quantity)",
    )
    a = ap.parse_args()

    import bluequbit

    bq = bluequbit.init(load_token())
    n = a.rows * a.cols
    pats = grid_edges(a.rows, a.cols)
    b, m = 0, n - 1  # butterfly and measured qubit at opposite corners
    zm = [("I" * (n - 1 - m) + "Z" + "I" * m, 1.0)]
    rows = []
    out = OUT / f"otoc{a.order}_echo_{a.rows}x{a.cols}_seeds{a.seeds.replace(',', '-')}.json"
    for seed in [int(s) for s in a.seeds.split(",")]:
        for cyc in [int(c) for c in a.cycles.split(",")]:
            run_one(bq, a, n, pats, b, m, zm, seed, cyc, rows)
            out.write_text(json.dumps(rows, indent=1))  # incremental: a crash keeps finished rows
    print("saved", out)
    return 0


def run_one(bq, a, n, pats, b, m, zm, seed, cyc, rows) -> None:
    u, n_w = random_u(n, pats, cyc, np.random.default_rng(seed * 1000 + cyc))
    echo = u.copy()
    echo.x(b)
    echo.compose(u.inverse(), inplace=True)  # B(t) = U^dag X_b U, as a circuit on |0..0>
    qc = echo.copy()
    if a.order == 2:  # <0|B(t) Z B(t) Z B(t) Z B(t)|0> = OTOC^2, since Z_m|0..0> = |0..0>
        qc.z(m)
        qc.compose(echo, inplace=True)
    row = {
        "n": n,
        "order": a.order,
        "seed": seed,
        "cycles": cyc,
        "sqrtW_count": n_w,
        "exact": exact_mean_z(qc, zm),
    }
    for thr in [float(x) for x in a.thresholds.split(",")]:
        t0 = time.time()
        r = bq.run(
            qc,
            device="pauli-path",
            pauli_sum=zm,
            options={"pauli_path_truncation_threshold": thr},
        )
        row[f"pp_{thr:g}"] = float(r.expectation_value)
        row[f"pp_{thr:g}_s"] = round(time.time() - t0, 1)
        row[f"pp_{thr:g}_cost"] = getattr(r, "cost", None)
    for chi in [int(c) for c in a.chis.split(",")]:
        t0 = time.time()
        r = bq.run(qc, device="mps.cpu", pauli_sum=zm, options={"mps_bond_dimension": chi})
        row[f"mps_{chi}"] = float(r.expectation_value)
        row[f"mps_{chi}_s"] = round(time.time() - t0, 1)
        row[f"mps_{chi}_cost"] = getattr(r, "cost", None)
    rows.append(row)
    print(
        json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()}),
        flush=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
