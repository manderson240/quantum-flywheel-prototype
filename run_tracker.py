"""Run BlueQubit Pauli-path and MPS on the tracker's Floquet Ising candidate; save every job as it completes.

MPS runs use a reverse Cuthill-McKee relabelling of the heavy-hex graph (bandwidth-minimising); circuit AND
observable are relabelled with the same permutation, so the expectation value is unchanged by construction.
Run: python run_tracker.py --cycles 13,16 --obs zzd3,mag --pp 1e-3,1e-4 --chi 64,128
The API token is read from .env inside the process and never printed.
"""

from __future__ import annotations

import argparse
import json
import time

import floquet_tracker as ft
import numpy as np
from kicked_ising_crosscheck import OUT, load_token
from qiskit import QuantumCircuit
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import reverse_cuthill_mckee


def rcm_perm() -> list[int]:
    layers, _ = ft.readme_spec()
    edges = sorted(set().union(*layers))
    r = [a for a, b in edges] + [b for a, b in edges]
    c = [b for a, b in edges] + [a for a, b in edges]
    order = reverse_cuthill_mckee(
        csr_matrix((np.ones(len(r)), (r, c)), shape=(ft.N, ft.N)), symmetric_mode=True
    )
    return [int(i) for i in order]


def relabel(qc: QuantumCircuit, obs: list[tuple[str, float]], order: list[int]):
    pos = {old: new for new, old in enumerate(order)}
    out = QuantumCircuit(ft.N)
    for ins in qc.data:
        out.append(ins.operation, [out.qubits[pos[qc.find_bit(q).index]] for q in ins.qubits])
    n = ft.N
    new_obs = []
    for lab, c in obs:
        s = ["I"] * n
        for k, ch in enumerate(lab):
            if ch != "I":
                s[n - 1 - pos[n - 1 - k]] = ch
        new_obs.append(("".join(s), c))
    return out, new_obs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", default="13")
    ap.add_argument("--obs", default="zzd3")
    ap.add_argument("--pp", default="1e-3")
    ap.add_argument("--chi", default="64")
    ap.add_argument("--tag", default="run")
    a = ap.parse_args()

    import bluequbit

    ft.self_check()
    bq = bluequbit.init(load_token())
    obs_all = ft.observables()
    order = rcm_perm()
    out = OUT / f"tracker_floquet51_{a.tag}.json"
    rows = json.loads(out.read_text()) if out.exists() else []
    done = {(r["cycles"], r["obs"], r["method"], r["setting"]) for r in rows}
    for cyc in [int(c) for c in a.cycles.split(",")]:
        qc = ft.circuit(cyc)
        for ob in a.obs.split(","):
            jobs = [("pauli-path", float(d)) for d in a.pp.split(",") if d] + [
                ("mps.cpu", int(c)) for c in a.chi.split(",") if c
            ]
            for dev, setting in jobs:
                if (cyc, ob, dev, setting) in done:
                    continue
                if dev == "mps.cpu":
                    circ, terms = relabel(qc, obs_all[ob], order)
                    opts = {"mps_bond_dimension": setting}
                else:
                    circ, terms = qc, obs_all[ob]
                    opts = {"pauli_path_truncation_threshold": setting}
                t0 = time.time()
                try:
                    r = bq.run(circ, device=dev, pauli_sum=terms, options=opts)
                    val, err = float(r.expectation_value), None
                    cost = getattr(r, "cost", None)
                except Exception as e:  # record the failure, keep going
                    val, err, cost = None, f"{type(e).__name__}: {str(e)[:200]}", None
                row = {
                    "cycles": cyc,
                    "obs": ob,
                    "method": dev,
                    "setting": setting,
                    "value": val,
                    "wall_s": round(time.time() - t0, 1),
                    "cost": cost,
                    "error": err,
                }
                rows.append(row)
                out.write_text(json.dumps(rows, indent=1))
                print(json.dumps(row), flush=True)
    print("saved", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
