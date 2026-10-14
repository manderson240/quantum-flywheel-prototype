"""Generic loader for the tracker's Floquet mixed-field Ising QASM3 files (51q or 74q, any cycle count), self-checked
against the README's own edge layers (E_1..E_3 for that lattice) and angles. Builds the full-file circuit and the
magnetization Pauli sum. Used for the 74qx27c (no classical entry yet) and 51qx30c instances.
"""

from __future__ import annotations

import ast
import math
import re
from pathlib import Path

from qasm_angle import angle
from qiskit import QuantumCircuit


T = Path(__file__).parent / "tracker"
GATE = re.compile(r"^(rx|rz|rzz)\(([^)]+)\)\s+q\[(\d+)\](?:,\s*q\[(\d+)\])?;", re.M)


def _angle(s: str) -> float:
    return angle(s)  # AST-evaluated: numbers, pi, + - * / only


def readme_layers(n: int) -> list[set[tuple[int, int]]]:
    r = (T / "README.md").read_text()
    block = r[: r.find("N=74$-qubit lattice")] if n == 51 else r[r.find("N=74$-qubit lattice") :]
    return [
        {tuple(sorted(e)) for e in ast.literal_eval(v)}
        for _, v in re.findall(r"\\mathcal\{E\}_(\d)\$\s*\|\s*(\[.*?\])\s*\|", block)
    ][:3]


def load(name: str) -> tuple[QuantumCircuit, int, int]:
    txt = (T / name).read_text()
    n = int(re.search(r"qubit\[(\d+)\] q;", txt)[1])
    body = txt.split(f"qubit[{n}] q;")[1]
    layers = [
        [(g, _angle(a), int(x), int(y) if y else None) for g, a, x, y in GATE.findall(b)]
        for b in body.split("barrier")
    ]
    layers = [l for l in layers if l]
    spec = readme_layers(n)
    assert len(spec) == 3, "README edge layers not found"
    for k, ops in enumerate(layers):
        got = {tuple(sorted((x, y))) for g, _, x, y in ops if g == "rzz"}
        assert got == spec[k % 3], f"{name}: layer {k} edges differ from README E_{k % 3 + 1}"
        assert sum(g == "rx" for g, *_ in ops) == n and sum(g == "rz" for g, *_ in ops) == n
    rx = next(a for g, a, *_ in layers[0] if g == "rx")
    rz = next(a for g, a, *_ in layers[0] if g == "rz")
    assert math.isclose(rx * 3, 1.56567, abs_tol=1e-5) and math.isclose(
        rz * 3, 0.33879, abs_tol=1e-5
    )
    qc = QuantumCircuit(n)
    for ops in layers:
        for g, a, x, y in ops:
            if g == "rx":
                qc.rx(a, x)
            elif g == "rz":
                qc.rz(a, x)
            else:
                qc.rzz(a, x, y)
    assert len(layers) % 3 == 0
    return qc, n, len(layers) // 3


def magnetization(n: int) -> list[tuple[str, float]]:
    return [("".join("Z" if n - 1 - k == i else "I" for k in range(n)), 1.0 / n) for i in range(n)]


if __name__ == "__main__":
    for f in (
        "floquet_mixed_field_ising_mag_74qx27c.qasm",
        "floquet_mixed_field_ising_mag_51qx30c.qasm",
    ):
        qc, n, cyc = load(f)
        print(f, "OK:", n, "qubits,", cyc, "cycles,", dict(qc.count_ops()))
