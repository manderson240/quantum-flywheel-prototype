"""Strict line-grammar parser for the released RCS .qasm files (OpenQASM 3, rz/rx/cz/barrier/measure only).

Angles go through the project's safe parser qasm_angle.angle (AST whitelist, never eval). Any line outside the
grammar raises ValueError. Returns the ordered gate list, the CZ layers (maximal runs of consecutive cz lines),
and whether measurement is exactly c[i] = measure q[i] for all 61 qubits.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from qasm_angle import angle  # noqa: E402


R1 = re.compile(r"^(rz|rx)\((.+)\) q\[(\d+)\];$")
R2 = re.compile(r"^cz q\[(\d+)\], q\[(\d+)\];$")
RB = re.compile(r"^barrier( q\[\d+\],?)+;$")
RM = re.compile(r"^c\[(\d+)\] = measure q\[(\d+)\];$")
HEADER = ["OPENQASM 3.0;", 'include "stdgates.inc";', "bit[61] c;", "qubit[61] q;"]


def parse_qasm(path: Path, n: int = 61) -> dict:
    lines = [s.strip() for s in Path(path).read_text().splitlines() if s.strip()]
    if lines[:4] != HEADER:
        raise ValueError(f"unexpected header in {path}")
    gates, cz_layers, cur, meas = [], [], [], {}
    for s in lines[4:]:
        m = R1.match(s)
        if m:
            if meas:
                raise ValueError("gate after measurement")
            if cur:
                cz_layers.append(cur)
                cur = []
            gates.append((m.group(1), int(m.group(3)), angle(m.group(2))))
            continue
        m = R2.match(s)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if meas or a == b:
                raise ValueError("bad cz")
            gates.append(("cz", a, b))
            cur.append((a, b))
            continue
        if RB.match(s):
            if cur:
                cz_layers.append(cur)
                cur = []
            continue
        m = RM.match(s)
        if m:
            meas[int(m.group(1))] = int(m.group(2))
            continue
        raise ValueError(f"line outside grammar: {s[:80]!r}")
    if cur:
        cz_layers.append(cur)
    qs = {g[1] for g in gates} | {g[2] for g in gates if g[0] == "cz"}
    if max(qs) >= n:
        raise ValueError("qubit index out of range")
    return {
        "gates": gates,
        "cz_layers": cz_layers,
        "measure_identity": meas == {i: i for i in range(n)},
    }
