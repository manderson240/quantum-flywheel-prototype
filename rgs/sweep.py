"""Exact amplitude of a 1D open-chain CZ brickwork circuit by a spatial sweep (the temporal-boundary idea of
Manabe, Gu & Pan, arXiv:2608.13110): walk qubit by qubit, carrying a boundary tensor whose axes are the CZ bonds to
the next qubit (one bond per CZ = the neighbour's computational value at that time). Width ~ #CZs per neighbour pair
(= d/2 for IBM's 70x70 instance), independent of the single-qubit gates. Reimplementation, validated against an exact
statevector in mini_sweep_validate.py; NOT the authors' code.
"""

from __future__ import annotations

import math
import re

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from qasm_angle import angle  # noqa: E402


_SX = np.array([[1 + 1j, 1 - 1j], [1 - 1j, 1 + 1j]]) / 2
_FIXED = {
    "sx": _SX,
    "sxdg": _SX.conj().T,
    "s": np.diag([1, 1j]),
    "sdg": np.diag([1, -1j]),
    "h": np.array([[1, 1], [1, -1]]) / math.sqrt(2),
    "z": np.diag([1, -1]),
    "x": np.array([[0, 1], [1, 0]]),
    "t": np.diag([1, np.exp(1j * math.pi / 4)]),
    "tdg": np.diag([1, np.exp(-1j * math.pi / 4)]),
}


def _angle(expr: str) -> float:
    return angle(expr)  # AST-evaluated QASM angle (numbers, pi, + - * /)


def parse(qasm: str) -> tuple[int, list[tuple]]:
    n, ops = 0, []
    for line in qasm.splitlines():
        line = line.strip()
        if m := re.match(r"qreg\s+q\[(\d+)\]", line):
            n = int(m[1])
            continue
        qs = [int(x) for x in re.findall(r"q\[(\d+)\]", line)]
        if not qs:
            continue
        name = re.match(r"([a-z]+)", line)[1]
        if name == "cz":
            ops.append(("cz", tuple(sorted(qs))))
        elif name == "rz":
            th = _angle(re.search(r"rz\(([^)]*)\)", line)[1])
            ops.append(("u", qs[0], np.diag([np.exp(-0.5j * th), np.exp(0.5j * th)])))
        elif name in _FIXED:
            ops.append(("u", qs[0], _FIXED[name]))
        else:
            raise ValueError(f"unsupported gate: {line}")
    for op in ops:
        if op[0] == "cz" and op[1][1] - op[1][0] != 1:
            raise ValueError("only nearest-neighbour CZs on an open chain are supported")
    return n, ops


def amplitude(qasm: str, bits_q0_first: str) -> tuple[complex, int]:
    """<x| C |0...0>. Returns (amplitude, max live boundary rank = log2 of the largest tensor)."""
    n, ops = parse(qasm)
    events = [
        [] for _ in range(n)
    ]  # per-qubit time-ordered: ("u", U) | ("L",) consume | ("R",) produce
    for op in ops:
        if op[0] == "u":
            events[op[1]].append(("u", op[2]))
        else:
            a, b = op[1]
            events[a].append(("R",))
            events[b].append(("L",))
    # boundary: array with axes [s, bond_0, bond_1, ...]; bonds kept in production order (FIFO)
    carry = np.ones(1, dtype=np.complex128)[None]  # dummy; replaced at qubit 0
    carry_bonds = 0
    max_rank = 0
    for q in range(n):
        # start column: s = |0>, pending left bonds = carry_bonds (axes 1..)
        state = np.zeros((2,) + (2,) * carry_bonds, dtype=np.complex128)
        state[0] = carry.reshape((2,) * carry_bonds) if carry_bonds else carry.reshape(())
        left_pending = carry_bonds  # left bonds sit at axes 1..left_pending (oldest first)
        produced = 0  # right bonds appended after the left ones
        for ev in events[q]:
            if ev[0] == "u":
                state = np.tensordot(ev[1], state, axes=([1], [0]))
            elif ev[0] == "L":  # consume oldest left bond l: sum_l (-1)^{l s} B[l]
                b = np.moveaxis(state, 1, 1)  # oldest left bond is axis 1
                b0, b1 = b.take(0, axis=1), b.take(1, axis=1)
                sign = np.array([1, -1]).reshape((2,) + (1,) * (b1.ndim - 1))
                state = b0 + sign * b1
                left_pending -= 1
            else:  # produce right bond r = copy of s (appended as last axis)
                out = np.zeros(state.shape + (2,), dtype=np.complex128)
                out[0, ..., 0] = state[0]
                out[1, ..., 1] = state[1]
                state = out
                produced += 1
            max_rank = max(max_rank, state.ndim)
        assert left_pending == 0, "unconsumed left bonds"
        carry = state[int(bits_q0_first[q])]  # project the worldline onto the measured bit
        carry_bonds = produced
    return complex(carry.reshape(())), max_rank
