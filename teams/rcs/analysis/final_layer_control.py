"""Numerical control: the final CZ layer of d36_logical does not change the output distribution.

Takes the sub-circuit of d36_logical on logical qubits 8..22 (grid rows 2-3; first attempt on rows 1-2 had ZERO
final-layer CZs inside the subset, caught by the negative control; CZs touching other qubits
dropped), simulates it by exact statevector with and without the cycle-36 CZ layer, and compares Z-basis
probabilities. Negative control: dropping an INTERIOR CZ layer (cycle 20) must change the distribution.
Also checks gate conventions: RZ(a)=diag(e^{-ia/2},e^{ia/2}), RX(a)=exp(-i a X/2), applied in file order.
Run: nice -n 10 python3 teams/rcs/analysis/final_layer_control.py   (<100 MB)
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from structure import QASM, ROOT, parse  # noqa: E402

S = list(range(8, 23))
M = len(S)
LOC = {q: i for i, q in enumerate(S)}


def rz(a):
    return np.diag([np.exp(-0.5j * a), np.exp(0.5j * a)])


def rx(a):
    c, s = np.cos(a / 2), np.sin(a / 2)
    return np.array([[c, -1j * s], [-1j * s, c]])


def apply1(psi, U, q):
    psi = psi.reshape([2] * M)
    psi = np.moveaxis(np.tensordot(U, psi, axes=([1], [M - 1 - q])), 0, M - 1 - q)
    return psi.reshape(-1)


def run(cycles, skip_cz_cycle=None):
    psi = np.zeros(2**M, dtype=complex)
    psi[0] = 1
    idx = np.arange(2**M)
    for d, c in enumerate(cycles, start=1):
        for g, a, q in c["oneq"]:
            if q in LOC:
                psi = apply1(psi, rz(a) if g == "rz" else rx(a), LOC[q])
        if d == skip_cz_cycle:
            continue
        for a, b in c["cz"]:
            if a in LOC and b in LOC:
                mask = ((idx >> LOC[a]) & 1) & ((idx >> LOC[b]) & 1)
                psi = np.where(mask == 1, -psi, psi)
    return np.abs(psi) ** 2


n, cycles = parse(QASM)
p_full = run(cycles)
p_nofinal = run(cycles, skip_cz_cycle=36)
p_nomid = run(cycles, skip_cz_cycle=20)
res = {
    "qubits": S,
    "norm": float(p_full.sum()),
    "max_abs_diff_drop_final_layer": float(np.abs(p_full - p_nofinal).max()),
    "tvd_drop_final_layer": float(0.5 * np.abs(p_full - p_nofinal).sum()),
    "tvd_drop_cycle20_layer_negative_control": float(0.5 * np.abs(p_full - p_nomid).sum()),
    "collision_ratio_2^m_sum_p2_minus_1": float(2**M * (p_full**2).sum() - 1),
    "final_layer_cz_inside_subcircuit": sum(1 for a, b in cycles[-1]["cz"] if a in LOC and b in LOC),
    "cycle20_layer_cz_inside_subcircuit": sum(1 for a, b in cycles[19]["cz"] if a in LOC and b in LOC),
}
print(res)
(ROOT / "teams/rcs/results/final_layer_control.json").write_text(json.dumps(res, indent=1))
