"""rcs wave 6: parse the released d36 mirror circuits and derive depth-d mirrors (same instance).

A depth-d mirror (d even) = input layer + the first d/2 cycles of U + the matching d/2 cycles of U^dagger taken from
the SAME released file. Label: "derived from the released d36 instances, same instance". No qasm3 importer, no eval.
"""
from __future__ import annotations
import re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from qasm_angle import angle  # noqa: E402
MIRROR = ROOT / "refs/rcs-nighthawk-data/data/circuits/mirror"
N = 61
_G1 = re.compile(r"(rx|rz)\((.+)\) q\[(\d+)\];$")
_CZ = re.compile(r"cz q\[(\d+)\], ?q\[(\d+)\];$")


def parse_segments(path: Path):
    """Return (input_qubits, segments). Each segment is a list of ('rx'|'rz', angle, q) or ('cz', a, b)."""
    segs, cur, inp = [], [], []
    for ln in path.read_text().splitlines():
        ln = ln.strip()
        if ln.startswith("barrier"):
            segs.append(cur); cur = []; continue
        m = re.match(r"rx\(_theta_(\d+)_\) q\[(\d+)\];$", ln)
        if m:
            assert m[1] == m[2]; inp.append(int(m[2])); continue
        m = _G1.match(ln)
        if m: cur.append((m[1], angle(m[2]), int(m[3]))); continue
        m = _CZ.match(ln)
        if m: cur.append(("cz", int(m[1]), int(m[2]))); continue
        assert (ln.startswith(("OPENQASM", "include", "input", "bit[", "qubit[", "meas[")) or not ln), ln
    segs.append(cur)
    assert inp == list(range(N)), "input layer must be rx(theta_i) on every qubit"
    body = [s for s in segs if s]
    return body


def is_cz(seg):
    return all(g[0] == "cz" for g in seg)


def inverse_seg(seg):
    out = []
    for g in reversed(seg):
        out.append(g if g[0] == "cz" else (g[0], -g[1], g[2]))
    return out


def seg_close(a, b, tol=1e-9):
    if len(a) != len(b): return False
    for x, y in zip(a, b):
        if x[0] != y[0] or x[2] != y[2]: return False
        if x[0] == "cz":
            if x[1] != y[1]: return False
        elif abs(x[1] - y[1]) > tol: return False
    return True


def cz_equal(a, b):
    return sorted(tuple(sorted(g[1:])) for g in a) == sorted(tuple(sorted(g[1:])) for g in b)


def load_instance(i: int):
    body = parse_segments(MIRROR / f"d36_instance{i}.qasm")
    assert len(body) == 72, len(body)
    fwd, bwd = body[:36], body[36:]
    # verify: forward cycles are (1q, cz) x 18; bwd[k] is the inverse of fwd[35-k]
    for k in range(36):
        assert is_cz(fwd[k]) == (k % 2 == 1)
        f, b = fwd[35 - k], bwd[k]
        assert (cz_equal(f, b) if is_cz(f) else seg_close(inverse_seg(f), b, 1e-9)), (i, k)
    return fwd, bwd


def derived_ops(i: int, d: int, cycles_fwd=None):
    """Gate list (no input layer) for the derived depth-d mirror of instance i: d/2 forward cycles + their inverse."""
    assert d % 2 == 0 and 2 <= d <= 36
    fwd, bwd = load_instance(i)
    h = d // 2  # forward cycles
    f = fwd[: 2 * h]
    b = bwd[36 - 2 * h:]
    ops = [g for s in f + b for g in s]
    return ops


def n_cz(ops):
    return sum(1 for g in ops if g[0] == "cz")


def to_qiskit(ops, bits, nq=N, measure=True):
    from qiskit import QuantumCircuit
    import math
    c = QuantumCircuit(nq)
    for q, x in enumerate(bits):
        if x: c.rx(math.pi, q)
    for g in ops:
        if g[0] == "cz": c.cz(g[1], g[2])
        else: getattr(c, g[0])(g[1], g[2])
    if measure: c.measure_all()
    return c


def bitstring_key(bits):
    """BlueQubit mps.cpu count keys put qubit 0 at the LEFTMOST character (big-endian). Established by the
    pre-registered V3 control (job bX2WQF8flRjiQOFM: only qubit 0 flipped -> '1000...0' in 10000/10000 shots).
    The PREREG §5 assumption (qubit 0 rightmost, Qiskit style) was wrong; see DEVIATIONS.md D1."""
    return "".join(str(b) for b in bits)
