"""V2 diagnostic analysis per PREREG.md (frozen bd0b051e5df63034). Exact 16q statevector reference; linear XEB for
BlueQubit samples (bootstrap CI) and exact XEB for own MPS; control C0; pre-registered decision rules.
Writes results/analysis.json."""

import json
import math
import sys
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "wave6"))
sys.path.insert(0, str(HERE))
import own_mps as om
from run import BITS, CELLS, N


ORIG_V2 = {
    4: 0.199,
    8: 0.028,
    16: 0.618,
}  # wave-6 V2 survival (hits / 1e5): 19,9xx / 2,8xx / 61,836
ORIG_V2_HITS = {}
for x in (4, 8, 16):
    d = json.loads(
        (HERE.parent / "wave6" / "results" / "cells" / f"V2_16q_d36_chi{x}.json").read_text()
    )
    ORIG_V2_HITS[x] = d["hits"]
    ORIG_V2[x] = d["hits"] / d["shots"]
OWN_V2 = {
    4: 0.0046446101153679855,
    8: 0.006234762247084328,
    16: 0.024420970924545087,
}  # posthoc_v2_routing swap_back


def apply(m, ops):
    for q, x in enumerate(BITS):
        if x:
            m.g1(om.rx(math.pi), q)
    for g in ops:
        if g[0] == "cz":
            m.cz(g[1], g[2])
        elif g[0] == "rx":
            m.g1(om.rx(g[1]), g[2])
        else:
            m.g1(om.rz(g[1]), g[2])
    return m


def vec(m, perm=None):
    t = m.A[0]
    for a in m.A[1:]:
        t = np.tensordot(t, a, axes=([-1], [0]))
    v = t.reshape([2] * N)
    if perm is not None:
        v = np.transpose(v, np.argsort(perm))  # site s holds logical qubit perm[s]
    return v / np.linalg.norm(v)


class Perm(
    om.MPS
):  # descriptive variant: no swap-back, track a logical->site permutation (as posthoc_v2_routing)
    def __init__(self, bits, chi):
        super().__init__(bits, chi)
        self.pos = list(range(self.n))
        self.at = list(range(self.n))

    def cz(self, a, b):
        pa, pb = sorted((self.pos[a], self.pos[b]))
        for k in range(pb - 1, pa, -1):
            self.g2adj(om.SWAP, k)
            qa, qb = self.at[k], self.at[k + 1]
            self.at[k], self.at[k + 1] = qb, qa
            self.pos[qa], self.pos[qb] = k + 1, k
        self.g2adj(om.CZ, pa)

    def g1(self, U, q):
        super().g1(U, self.pos[q])


def key_index(k):  # BlueQubit keys: qubit 0 leftmost (V3 control)
    return tuple(int(c) for c in k)


def ideal(p):  # DEVIATIONS D1: normaliser = XEB of perfect sampling
    return 2**N * float((p**2).sum()) - 1


def xeb_samples(p, counts, rng, B=2000):
    keys = list(counts)
    w = np.array([counts[k] for k in keys], float)
    pv = np.array([p[key_index(k)] for k in keys])
    n = int(w.sum())
    z = ideal(p)
    est = (2**N * float((w * pv).sum()) / n - 1) / z
    draws = rng.multinomial(n, w / n, size=B)
    boot = (2**N * (draws @ pv) / n - 1) / z
    return est, float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)), n


def main():
    rng = np.random.default_rng(0)
    res = {"cells": {}}
    refs = {}
    for cid, (ops, chi) in CELLS.items():
        if cid.startswith("R_"):
            continue
        key = cid.split("_")[0]
        if key not in refs:
            _, psi = om.statevector_survival(ops, BITS)
            refs[key] = np.abs(psi) ** 2
    # C0: instrument control on F's exact distribution
    pF = refs["F"]
    flat = pF.ravel()
    s = rng.choice(flat.size, size=100_000, p=flat / flat.sum())
    c0_raw = 2**N * float(flat[s].mean()) - 1
    c0 = c0_raw / ideal(pF)
    res["C0_raw"] = c0_raw
    res["C0_xeb_exact_samples"] = c0
    res["C0_pass"] = 0.9 <= c0 <= 1.1
    if not res["C0_pass"]:
        (HERE / "results" / "analysis.json").write_text(json.dumps(res, indent=1))
        sys.exit("C0 failed: instrument broken")
    for cid, (ops, chi) in CELLS.items():
        f = HERE / "results" / "cells" / f"{cid}.json"
        d = json.loads(f.read_text()) if f.exists() else None
        row = {
            "chi": chi,
            "job_id": d and d["job_id"],
            "status": d and d["status"],
            "cost": d and d["cost"],
        }
        if cid.startswith("R_"):
            key = "".join(map(str, BITS))
            hits = (d["counts"] or {}).get(key, 0) if d and d["counts"] else None
            n = sum(d["counts"].values()) if d and d["counts"] else None
            row.update(
                hits=hits,
                shots=n,
                survival=hits / n if n else None,
                orig_survival=ORIG_V2[chi],
                own_survival=OWN_V2[chi],
            )
            if n:  # 99% binomial (normal approx) interval around the ORIGINAL rate
                p0 = ORIG_V2[chi]
                half = 2.576 * math.sqrt(p0 * (1 - p0) / n)
                row["within_99pct_of_original"] = abs(hits / n - p0) <= half
                row["interval"] = [p0 - half, p0 + half]
        else:
            p = refs[cid.split("_")[0]]
            m = apply(om.MPS([0] * N, chi), ops)
            q = np.abs(vec(m)) ** 2
            mp = apply(Perm([0] * N, chi), ops)
            qp = np.abs(vec(mp, perm=mp.at)) ** 2
            _, psi = om.statevector_survival(ops, BITS)
            row["own_xeb"] = 2**N * float((q * p).sum()) - 1 ; row["own_xeb_raw"] = row["own_xeb"]
            row["own_xeb"] = row["own_xeb_raw"] / ideal(p)
            row["own_fidelity"] = float(abs(np.vdot(psi.ravel(), vec(m).ravel())) ** 2)
            row["own_noswapback_xeb_descriptive"] = (2**N * float((qp * p).sum()) - 1) / ideal(p)
            if d and d["counts"]:
                est, lo, hi, n = xeb_samples(p, d["counts"], rng)
                row.update(
                    bq_xeb=est,
                    bq_ci95=[lo, hi],
                    shots=n,
                    trunc_win=(est > 2 * row["own_xeb"] and lo > row["own_xeb"]),
                    trunc_refuted=(lo <= row["own_xeb"] <= hi) or hi < row["own_xeb"],
                )
        res["cells"][cid] = row

    def verdict(prefix):
        rows = [res["cells"][f"{prefix}_chi{x}"] for x in (4, 8, 16)]
        if any("bq_xeb" not in r for r in rows):
            return "INCOMPLETE"
        if sum(r["trunc_win"] for r in rows) >= 2:
            return "SUPPORTED"
        if sum(r["trunc_refuted"] for r in rows) >= 2:
            return "REFUTED"
        return "INCONCLUSIVE"

    vF, vB = verdict("F"), verdict("B")
    v2_gap = sum(ORIG_V2[x] > 2 * OWN_V2[x] for x in (4, 8, 16)) >= 2
    res["H_trunc_on_F"] = vF
    res["H_trunc_on_B"] = vB
    res["H_trunc"] = vF
    res["H_cancel"] = (
        "SUPPORTED"
        if (vF == "REFUTED" and vB == "REFUTED" and v2_gap)
        else "REFUTED"
        if (vF == "SUPPORTED" and vB == "SUPPORTED")
        else "INCONCLUSIVE"
    )
    (HERE / "results" / "analysis.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: v for k, v in res.items() if k != "cells"}, indent=1))
    for cid, r in res["cells"].items():
        print(
            cid,
            {
                k: (round(v, 5) if isinstance(v, float) else v)
                for k, v in r.items()
                if k not in ("job_id", "interval")
            },
        )


if __name__ == "__main__":
    main()
