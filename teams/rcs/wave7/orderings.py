"""rcs wave 7: candidate MPS chain orderings of the 61 logical qubits (pure data, no I/O besides layout.json).
order[site] = logical qubit at chain site `site`. Physical qubit p sits at (row, col) = (p // 10, p % 10)
(refs/rcs-nighthawk-data/rcs/layout.py). Logical 0..60 = row-major over the 8x8 subgrid rows 1-8, cols 2-9."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
_L = json.loads((ROOT / "refs/rcs-nighthawk-data/data/layout.json").read_text())
L2P = _L["logical_to_physical"]
RC = {q: divmod(p, 10) for q, p in enumerate(L2P)}          # logical -> (row, col)
EDGES = sorted({tuple(sorted(e)) for m in _L["matchings"].values() for e in m})  # coupler graph, logical indices
ROWS, COLS = range(1, 9), range(2, 10)
AT = {rc: q for q, rc in RC.items()}


def _seq(cells):
    return [AT[rc] for rc in cells if rc in AT]


def logical():
    return list(range(61))


def row_snake():
    return _seq([(r, c) for i, r in enumerate(ROWS) for c in (COLS if i % 2 == 0 else reversed(COLS))])


def col_raster():
    return _seq([(r, c) for c in COLS for r in ROWS])


def col_snake():
    return _seq([(r, c) for i, c in enumerate(COLS) for r in (ROWS if i % 2 == 0 else reversed(ROWS))])


def rcm():
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import reverse_cuthill_mckee
    a = np.zeros((61, 61))
    for i, j in EDGES: a[i, j] = a[j, i] = 1
    return [int(x) for x in reverse_cuthill_mckee(csr_matrix(a), symmetric_mode=True)]


def two_row():
    """Row pairs (1,2),(3,4),(5,6),(7,8); within a pair, column by column (top then bottom); pairs alternate
    column direction so consecutive pairs join at the same edge."""
    cells = []
    for k, r in enumerate((1, 3, 5, 7)):
        cols = COLS if k % 2 == 0 else list(reversed(COLS))
        for c in cols: cells += [(r, c), (r + 1, c)]
    return _seq(cells)


ORDERS = {"LOG": logical, "RSN": row_snake, "CRA": col_raster, "CSN": col_snake, "RCM": rcm, "TWR": two_row}
ROUTINGS = ("SB", "NSB")   # SB = swap back after each CZ (wave 6); NSB = leave moved qubit (track permutation)
CANDIDATES = [f"{o}_{r}" for o in ORDERS for r in ROUTINGS]   # 12 candidates, frozen order


def order_of(variant):
    o = ORDERS[variant.split("_")[0]]()
    assert sorted(o) == list(range(61)), variant
    return o
