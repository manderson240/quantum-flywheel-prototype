"""Independent classical data point for the tracker's OLE 56x1488 candidate (pending: hardware 0.236 #199, BP-TN 0.459
#203, hybrid MC Pauli propagation 0.1867 #204), using BlueQubit Pauli-path.

f_delta(O) = 2^-n sum_z sigma_z <z|W^dag O W|z>, sigma_z = <z|O|z>, estimated from random z (README). W = the tracker's
QASM (156-qubit register, 56 used; relabelled to 0..55 in sorted order; custom `sxdg` expanded exactly as the file defines
it). Each z = X gates prepended to |0...0>. alpha = 0 is an exact echo (W = identity up to cancellation) so every term must
equal 1 — a same-delta calibration of the truncation. Remote compute only.
Run: python ole56.py --alpha 0.00 --delta 1e-3 --nz 3 [--seed 0]
"""

from __future__ import annotations

import argparse
import json
import random
import re
import time
from pathlib import Path

from kicked_ising_crosscheck import OUT, load_token
from qasm_angle import angle
from qiskit import QuantumCircuit


HERE = Path(__file__).parent
O_QUBITS = (131, 132, 133, 134, 135, 138, 139, 151, 152, 153, 154, 155)  # README, 56x1488


def load(alpha: str) -> tuple[QuantumCircuit, dict[int, int]]:
    txt = (HERE / f"tracker/obs/ole/operator_loschmidt_echo_56x1488_alpha_{alpha}.qasm").read_text()
    body = txt.split("qubit[156] q;", 1)[1]
    ops = []
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith(("barrier", "//")):
            continue
        m = re.match(r"^(\w+)(?:\(([^)]*)\))?\s+(q\[\d+\](?:,\s*q\[\d+\])*);$", line)
        if not m:
            raise ValueError(f"unparsed line: {line}")
        qs = [int(x) for x in re.findall(r"q\[(\d+)\]", m[3])]
        ang = (
            angle(m[2]) if m[2] else None
        )  # AST-evaluated QASM angle
        ops.append((m[1], ang, qs))
    used = sorted({q for _, _, qs in ops for q in qs} | set(O_QUBITS))
    idx = {q: i for i, q in enumerate(used)}
    qc = QuantumCircuit(len(used))
    for g, a, qs in ops:
        q = [idx[x] for x in qs]
        if g == "rx":
            qc.rx(a, q[0])
        elif g == "rz":
            qc.rz(a, q[0])
        elif g == "cz":
            qc.cz(q[0], q[1])
        elif g == "sx":
            qc.sx(q[0])
        elif g == "sxdg":  # file's own definition: s; h; s
            qc.s(q[0])
            qc.h(q[0])
            qc.s(q[0])
        elif g in ("x", "z", "h", "s", "sdg"):
            getattr(qc, g)(q[0])
        else:
            raise ValueError(f"unsupported gate {g}")
    return qc, idx


def zlabel(n, qs):
    s = ["I"] * n
    for q in qs:
        s[n - 1 - q] = "Z"
    return "".join(s)


def main() -> int:
    import bluequbit

    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", default="0.15")
    ap.add_argument("--delta", type=float, default=1e-3)
    ap.add_argument("--nz", type=int, default=3)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    W, idx = load(a.alpha)
    n = W.num_qubits
    obs_q = [idx[q] for q in O_QUBITS]
    O = [(zlabel(n, obs_q), 1.0)]
    bq = bluequbit.init(load_token())
    rng = random.Random(a.seed)
    out = OUT / "ole56.json"
    rows = json.loads(out.read_text()) if out.exists() else []
    for k in range(a.nz):
        z = [rng.randint(0, 1) for _ in range(n)]
        sigma = (-1) ** sum(z[q] for q in obs_q)
        qc = QuantumCircuit(n)
        for q, b in enumerate(z):
            if b:
                qc.x(q)
        qc.compose(W, inplace=True)
        t0 = time.time()
        row = {
            "alpha": a.alpha,
            "delta": a.delta,
            "seed": a.seed,
            "k": k,
            "sigma": sigma,
            "n": n,
            "gates": W.size(),
        }
        try:
            r = bq.run(
                qc,
                device="pauli-path",
                pauli_sum=O,
                options={"pauli_path_truncation_threshold": a.delta},
            )
            row["f_z"] = float(r.expectation_value)
            row["term"] = sigma * row["f_z"]
            row["cost"] = getattr(r, "cost", None)
        except Exception as e:
            row["err"] = str(e)[:240]
        row["s"] = round(time.time() - t0, 1)
        rows.append(row)
        out.write_text(json.dumps(rows, indent=1))
        print(json.dumps(row), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
