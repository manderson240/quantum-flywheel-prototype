"""Validate rgs/sweep.py (spatial sweep, width = #CZ per neighbour pair) against an exact Qiskit statevector on
slices of IBM's undoped RGS circuit: qubits 0..k-1, the first `ncz` CZ-bearing lines, plus the original final
(post-last-CZ) non-Clifford layer. Seconds of CPU."""
import re, sys
import numpy as np
from pathlib import Path
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
sys.path.insert(0, str(Path(__file__).parent))
from sweep import amplitude

SRC = Path(__file__).parent.parent / "tracker/cv/random_graph_sampling_nq70_depth70_checks27_basis_fstate.qasm"

def sliced(k, ncz):
    head, body = [], []
    for l in SRC.read_text().splitlines():
        qs = [int(x) for x in re.findall(r"q\[(\d+)\]", l)]
        if l.startswith("qreg"): head.append(f"qreg q[{k}];")
        elif not qs: head.append(l)
        elif all(q < k for q in qs): body.append(l)
    last_cz = max(i for i, l in enumerate(body) if l.startswith("cz"))
    kept, seen = [], 0
    for i, l in enumerate(body[: last_cz + 1]):
        if l.startswith("cz"):
            seen += 1
            if seen > ncz: break
        kept.append(l)
    return "\n".join(head + kept + body[last_cz + 1:])

worst = 0.0
rng = np.random.default_rng(1)
for k, ncz in [(4, 6), (6, 15), (8, 28), (10, 45), (12, 60)]:
    txt = sliced(k, ncz)
    sv = Statevector(QuantumCircuit.from_qasm_str(txt)).data
    p = np.abs(sv) ** 2
    errs, rank = [], 0
    for i in rng.choice(len(p), size=12, p=p / p.sum()):
        a, r = amplitude(txt, format(i, f"0{k}b")[::-1]); rank = max(rank, r)
        errs.append(abs(a - sv[i]) / abs(sv[i]))
    worst = max(worst, max(errs))
    print(f"k={k:2d} CZs={ncz:3d} max rel err={max(errs):.2e} max live rank={rank}")
print("SWEEP VALIDATION", "PASS" if worst < 1e-9 else "FAIL")
