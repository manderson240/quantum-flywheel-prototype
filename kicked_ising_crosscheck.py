"""Quantum Flywheel Track 02 prototype: adversarial classical simulation of the IBM 'utility' circuit family.

Circuit: kicked Ising on a heavy-hex lattice (Kim et al., Nature 618, 500 (2023)) — per Trotter step,
RX(theta_h) on every qubit, then RZZ(-pi/2) on every coupling-map edge. Observable: mean magnetization
<M> = (1/n) sum_i <Z_i>.

Falsifiable design:
  1. Small scale (n <= ~25): an INDEPENDENT exact oracle (local Qiskit statevector, not BlueQubit) gives
     ground truth; BlueQubit's pauli-path and MPS must match it within stated tolerance.
  2. Large scale (n = 127): no exact oracle exists; two independent approximate methods (pauli-path, MPS)
     must agree with each other, and the answer is reported with its truncation/bond-dimension sweep.
This script is step 1 only.

Run: python kicked_ising_crosscheck.py [--steps 5] [--distance 3]
"""

from __future__ import annotations

import os

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp, Statevector
from qiskit.transpiler import CouplingMap


ENV = Path(os.environ.get("BLUEQUBIT_ENV_FILE", Path.home() / ".env"))  # fallback file with a BLUEQUBIT_API_TOKEN= line
OUT = Path(__file__).parent / "results"


def load_token() -> str:
    if os.environ.get("BLUEQUBIT_API_TOKEN"):
        return os.environ["BLUEQUBIT_API_TOKEN"]
    for line in ENV.read_text().splitlines():
        if line.startswith("BLUEQUBIT_API_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("BLUEQUBIT_API_TOKEN not found")


def heavy_hex_edges(distance: int) -> tuple[int, list[tuple[int, int]]]:
    cm = CouplingMap.from_heavy_hex(distance, bidirectional=False)
    return cm.size(), sorted({tuple(sorted(e)) for e in cm.get_edges()})


def kicked_ising(
    n: int, edges: list[tuple[int, int]], theta_h: float, steps: int
) -> QuantumCircuit:
    qc = QuantumCircuit(n)
    for _ in range(steps):
        for q in range(n):
            qc.rx(theta_h, q)
        for a, b in edges:
            qc.rzz(-math.pi / 2, a, b)
    return qc


def mean_z_terms(n: int) -> list[tuple[str, float]]:
    # BlueQubit / Qiskit label order: rightmost character = qubit 0.
    return [("I" * (n - 1 - i) + "Z" + "I" * i, 1.0 / n) for i in range(n)]


def exact_mean_z(qc: QuantumCircuit, terms: list[tuple[str, float]]) -> float:
    return float(np.real(Statevector(qc).expectation_value(SparsePauliOp.from_list(terms))))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--distance", type=int, default=3)
    ap.add_argument("--steps", type=int, default=5)
    ap.add_argument("--thresholds", default="1e-3,1e-4")
    ap.add_argument(
        "--skip-remote", action="store_true", help="local exact oracle only ($0, no API calls)"
    )
    a = ap.parse_args()

    n, edges = heavy_hex_edges(a.distance)
    thetas = [0.0, math.pi / 8, math.pi / 4, 3 * math.pi / 8, math.pi / 2]
    terms = mean_z_terms(n)
    print(f"heavy-hex distance={a.distance}: n={n} qubits, {len(edges)} edges, steps={a.steps}")

    bq = None
    if not a.skip_remote:
        import bluequbit

        bq = bluequbit.init(load_token())

    rows = []
    for th in thetas:
        qc = kicked_ising(n, edges, th, a.steps)
        row = {"theta_h": th, "n": n, "steps": a.steps}
        t0 = time.time()
        row["exact_local"] = exact_mean_z(qc, terms)
        row["exact_local_s"] = round(time.time() - t0, 2)
        if bq is not None:
            for thr in [float(x) for x in a.thresholds.split(",")]:
                r = bq.run(
                    qc,
                    device="pauli-path",
                    pauli_sum=terms,
                    options={"pauli_path_truncation_threshold": thr},
                )
                row[f"pp_{thr:g}"] = float(r.expectation_value)
                row[f"pp_{thr:g}_cost"] = getattr(r, "cost", None)
        rows.append(row)
        print(json.dumps({k: (round(v, 5) if isinstance(v, float) else v) for k, v in row.items()}))

    OUT.mkdir(exist_ok=True)
    out = OUT / f"kicked_ising_hh{a.distance}_s{a.steps}.json"
    out.write_text(json.dumps(rows, indent=1))
    if bq is not None:
        for thr in a.thresholds.split(","):
            k = f"pp_{float(thr):g}"
            err = max(abs(r[k] - r["exact_local"]) for r in rows)
            print(f"pauli-path threshold {thr}: max |error| vs exact = {err:.2e}")
    print("saved", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
