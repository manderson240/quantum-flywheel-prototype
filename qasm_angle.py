"""Evaluate a QASM angle expression (numbers, pi, + - * / and unary minus) without eval().

The tracker's QASM files are third-party input; eval() with empty builtins is not a sandbox. Anything outside the grammar
raises ValueError instead of executing.
"""

from __future__ import annotations

import ast
import math
import operator


_BIN = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_UN = {ast.USub: operator.neg, ast.UAdd: operator.pos}


def angle(expr: str) -> float:
    def ev(n: ast.AST) -> float:
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if (
            isinstance(n, ast.Constant)
            and isinstance(n.value, (int, float))
            and not isinstance(n.value, bool)
        ):
            return float(n.value)
        if isinstance(n, ast.Name) and n.id == "pi":
            return math.pi
        if isinstance(n, ast.BinOp) and type(n.op) in _BIN:
            return _BIN[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _UN:
            return _UN[type(n.op)](ev(n.operand))
        raise ValueError(f"unsupported QASM angle expression: {expr!r}")

    return ev(ast.parse(expr.strip(), mode="eval"))
