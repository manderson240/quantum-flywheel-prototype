"""PREREG_UNDOPED_XEB_LOCAL §A P2: deterministic greedy qubit order over GF(2) cut-ranks (ties -> lowest index).
Writes local/greedy_order.json with the order, plan cut-ranks, peak and log2 total work."""
import json, math, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE.parent))
import stabilizer_overlap as so, score_undoped_gpu as S
n, ops, V = so.parse(S.CIRCUIT.read_text()); gf = so.graph_form(n, ops); G = np.array(gf["G"], dtype=np.uint8) % 2
N = G.shape[0]
def gf2_rank(M):
    M = M.copy(); r = 0
    for c in range(M.shape[1]):
        piv = np.nonzero(M[r:, c])[0]
        if piv.size == 0: continue
        p = r + piv[0]; M[[r, p]] = M[[p, r]]
        rows = np.nonzero(M[:, c])[0]; rows = rows[rows != r]; M[rows] ^= M[r]
        r += 1
        if r == M.shape[0]: break
    return r
order, rest = [], list(range(N))
while rest:
    best = min(rest, key=lambda v: (gf2_rank(G[np.ix_(order + [v], [u for u in rest if u != v])]) if len(rest) > 1 else 0, v))
    order.append(best); rest.remove(best)
steps, ranks = so.plan(gf["G"], order)
_, ranks_ann = so.plan(gf["G"], S.ANNEALED)
out = {"order": order, "peak": max(ranks), "log2_work": math.log2(sum(2**r for r in ranks)),
       "annealed_peak": max(ranks_ann), "annealed_log2_work": math.log2(sum(2**r for r in ranks_ann)), "differs_from_annealed": order != S.ANNEALED}
(HERE / "greedy_order.json").write_text(json.dumps(out)); print({k: v for k, v in out.items() if k != "order"})
