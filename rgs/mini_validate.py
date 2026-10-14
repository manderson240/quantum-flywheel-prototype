"""Validate the from-QASM tensor-network amplitude pipeline on a k-qubit slice of IBM's undoped RGS circuit
(all gates acting only on qubits 0..k-1; same gate conventions + final non-Clifford layer) against an exact
Qiskit statevector, including the Qiskit little-endian <-> q0-first bitstring conversion. Seconds of CPU."""
import re, sys, numpy as np
from pathlib import Path
import quimb.tensor as qtn
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

HERE = Path(__file__).parent.parent
SRC = HERE / "tracker/cv/random_graph_sampling_nq70_depth70_checks27_basis_fstate.qasm"

def slice_qasm(k: int) -> str:
    out = []
    for l in SRC.read_text().splitlines():
        qs = [int(x) for x in re.findall(r"q\[(\d+)\]", l)]
        if l.startswith("qreg"):
            out.append(f"qreg q[{k}];")
        elif not qs:
            out.append(l)
        elif all(q < k for q in qs):
            out.append(l)
    return "\n".join(out)

def main(k=16, nsamp=40, seed=0):
    txt = slice_qasm(k)
    qc = QuantumCircuit.from_qasm_str(txt)
    sv = Statevector(qc).data                      # index = sum_i b_i 2^i (Qiskit little-endian)
    tn = qtn.Circuit.from_openqasm2_str(txt)
    rng = np.random.default_rng(seed)
    # sample from the exact distribution, then compare amplitudes on those (high-probability) strings
    p = np.abs(sv) ** 2
    idx = rng.choice(len(p), size=nsamp, p=p / p.sum())
    errs = []
    for i in idx:
        qiskit_str = format(i, f"0{k}b")           # Qiskit string: leftmost char = highest qubit
        q0_first = qiskit_str[::-1]                # q0 first, as quimb's amplitude() expects
        a_tn = complex(tn.amplitude(q0_first, optimize="auto-hq"))
        errs.append(abs(a_tn - sv[i]) / abs(sv[i]))
    print(f"k={k}: gates={qc.size()} cz={qc.count_ops().get('cz',0)} max rel amplitude error over {nsamp} "
          f"sampled strings = {max(errs):.2e}")
    return max(errs)

if __name__ == "__main__":
    ok = all(main(k) < 1e-4 for k in (int(a) for a in (sys.argv[1:] or ["12", "16"])))
    print("MINI VALIDATION", "PASS" if ok else "FAIL")
