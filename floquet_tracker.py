"""IBM/Flatiron Quantum Advantage Tracker: Floquet mixed-field Ising candidate (51q heavy-hex).

Builds the tracker's OWN circuit truncated to N_c cycles (the published QASM is 16 cycles = 48 layers, each layer
= RX,RZ on every qubit then RZZ(pi/3) on one edge subset, separated by barriers), plus the three published
observables. Everything is cross-checked against the README before use:
  * each layer's RZZ edge set must equal the README's E_1/E_2/E_3 (cycled),
  * each pair in the ZZ_{d=2}/ZZ_{d=3} lists must be at that graph distance on the README edge set,
  * gate totals at N_c=16 must equal the file's (2448 rx, 2448 rz, 896 rzz).
"""

from __future__ import annotations

import ast
import math
import re
from collections import deque
from pathlib import Path

from qiskit import QuantumCircuit


T = Path(__file__).parent / "tracker"
QASM = T / "floquet_mixed_field_ising_mag_51qx16c.qasm"
N = 51
GATE = re.compile(r"^(rx|rz|rzz)\(([^)]+)\)\s+q\[(\d+)\](?:,\s*q\[(\d+)\])?;", re.M)


def _angle(s: str) -> float:
    return math.pi / 3 if s.strip() == "pi/3" else float(s)


def readme_spec() -> tuple[list[set[tuple[int, int]]], dict[int, list[tuple[int, int]]]]:
    r = (T / "README.md").read_text()
    r51 = r[: r.find("N=74$-qubit lattice")]  # first block of the README = 51-qubit lattice
    layers = [
        {tuple(sorted(e)) for e in ast.literal_eval(v)}
        for _, v in re.findall(r"\\mathcal\{E\}_(\d)\$\s*\|\s*(\[.*?\])\s*\|", r51)
    ]
    pairs = {
        int(d): [tuple(sorted(p)) for p in ast.literal_eval(v)]
        for d, v in re.findall(r"\|\s*\$ZZ_\{d=(\d)\}\$\s*\|\s*(\[.*?\])\s*\|", r51)
    }
    return layers, pairs


def parse_layers() -> list[list[tuple]]:
    body = QASM.read_text().split(f"qubit[{N}] q;")[1]
    out = []
    for blk in body.split("barrier"):
        ops = [(g, _angle(a), int(x), int(y) if y else None) for g, a, x, y in GATE.findall(blk)]
        if ops:
            out.append(ops)
    return out


def circuit(cycles: int) -> QuantumCircuit:
    layers = parse_layers()
    assert cycles * 3 <= len(layers), f"file holds {len(layers) // 3} cycles"
    qc = QuantumCircuit(N)
    for ops in layers[: 3 * cycles]:
        for g, a, x, y in ops:
            if g == "rx":
                qc.rx(a, x)
            elif g == "rz":
                qc.rz(a, x)
            else:
                qc.rzz(a, x, y)
    return qc


def graph_distances(edges: set[tuple[int, int]], src: int) -> dict[int, int]:
    adj: dict[int, list[int]] = {i: [] for i in range(N)}
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    dist, dq = {src: 0}, deque([src])
    while dq:
        u = dq.popleft()
        for v in adj[u]:
            if v not in dist:
                dist[v] = dist[u] + 1
                dq.append(v)
    return dist


def observables() -> dict[str, list[tuple[str, float]]]:
    """Pauli sums; label order is Qiskit's (rightmost character = qubit 0)."""
    _, pairs = readme_spec()

    def z(qs: tuple[int, ...]) -> str:
        s = ["I"] * N
        for q in qs:
            s[N - 1 - q] = "Z"
        return "".join(s)

    obs = {"mag": [(z((i,)), 1.0 / N) for i in range(N)]}
    for d in (2, 3):
        obs[f"zzd{d}"] = [(z(p), 1.0 / len(pairs[d])) for p in pairs[d]]
    return obs


def self_check() -> None:
    layers_spec, pairs = readme_spec()
    assert len(layers_spec) == 3 and [len(x) for x in layers_spec] == [19, 19, 18], [
        len(x) for x in layers_spec
    ]
    all_edges = set().union(*layers_spec)
    layers = parse_layers()
    assert len(layers) == 48, len(layers)
    for k, ops in enumerate(layers):
        got = {tuple(sorted((x, y))) for g, _, x, y in ops if g == "rzz"}
        assert got == layers_spec[k % 3], f"layer {k} edges differ from README E_{k % 3 + 1}"
        assert all(math.isclose(a, math.pi / 3) for g, a, *_ in ops if g == "rzz")
        assert sum(g == "rx" for g, *_ in ops) == N and sum(g == "rz" for g, *_ in ops) == N
    ops = circuit(16).count_ops()
    assert (ops["rx"], ops["rz"], ops["rzz"]) == (2448, 2448, 896), ops
    rx = next(a for g, a, *_ in layers[0] if g == "rx")
    rz = next(a for g, a, *_ in layers[0] if g == "rz")
    assert math.isclose(rx * 3, 1.56567, abs_tol=1e-5) and math.isclose(
        rz * 3, 0.33879, abs_tol=1e-5
    )
    for d in (2, 3):
        bad = [p for p in pairs[d] if graph_distances(all_edges, p[0]).get(p[1]) != d]
        assert not bad, f"d={d}: pairs not at distance {d}: {bad[:5]}"
        n_true = sum(
            1
            for i in range(N)
            for j, dd in graph_distances(all_edges, i).items()
            if j > i and dd == d
        )
        assert len(set(pairs[d])) == n_true, (
            f"d={d}: list has {len(set(pairs[d]))} pairs, graph has {n_true}"
        )
    print(
        f"self-check OK: 48 layers match README E1/E2/E3; params θx=3·{rx:.6f}, θz=3·{rz:.6f}; "
        f"{len(pairs[2])} d=2 and {len(pairs[3])} d=3 pairs verified by BFS and complete"
    )


if __name__ == "__main__":
    self_check()
