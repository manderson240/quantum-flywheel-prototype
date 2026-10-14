"""Independent second implementation of the 'exact' truth used for the 27q patch points (BlueQubit device="cpu").

Not Qiskit, not BlueQubit: a from-scratch numpy complex64 statevector (27 q = 1 GiB state, ~2.5 GiB peak). Each layer is
(RX on every qubit) then one diagonal (RZ on every qubit x RZZ on that layer's edges), which equals the patch circuit
because RZ/RZZ commute with RX on other qubits and each qubit's RX precedes its RZ. One evolution to the largest cycle
count snapshots mag / zzd2 / zzd3 at every cycle present in the result files.

Run:  python xcheck_local27.py --validate      # 12-q slice vs qiskit Statevector (seconds)
      python xcheck_local27.py --n 27          # writes results/xcheck_local27.json
No network, no BlueQubit jobs, no token.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
from floquet_patch_oracle import TX, TZ, TZZ, build, observables, patch


HERE = Path(__file__).parent
CHUNK = 1 << 20  # keeps per-chunk float64 bit matrix ~230 MB


def _bits(start: int, stop: int, n: int) -> np.ndarray:
    idx = np.arange(start, stop, dtype=np.int64)
    return ((idx[:, None] >> np.arange(n)) & 1).astype(
        np.int8
    )  # column q = bit of qubit q (qiskit order)


def apply_rx_all(psi: np.ndarray, n: int, theta: float) -> None:
    c, s = np.float32(np.cos(theta / 2)), np.complex64(-1j * np.sin(theta / 2))
    for q in range(n):
        v = psi.reshape(-1, 2, 1 << q)
        a = v[:, 0, :].copy()
        b = v[:, 1, :].copy()
        v[:, 0, :] = c * a + s * b
        v[:, 1, :] = s * a + c * b
        del a, b


def apply_diag(psi: np.ndarray, n: int, tz: float, tzz: float, edges) -> None:
    ea = np.array([e[0] for e in edges], dtype=np.int64)
    eb = np.array([e[1] for e in edges], dtype=np.int64)
    for st in range(0, psi.size, CHUNK):
        z = 1 - 2 * _bits(st, min(st + CHUNK, psi.size), n).astype(np.float32)  # bit 0 -> z=+1
        ang = tz * z.sum(1) + (tzz * (z[:, ea] * z[:, eb]).sum(1) if len(edges) else 0.0)
        psi[st : st + len(z)] *= np.exp(-0.5j * ang).astype(np.complex64)


def expect(psi: np.ndarray, n: int, obs) -> dict[str, float]:
    out = dict.fromkeys(obs, 0.0)
    parsed = {
        k: [([n - 1 - i for i, ch in enumerate(lab) if ch == "Z"], w) for lab, w in terms]
        for k, terms in obs.items()
    }
    for st in range(0, psi.size, CHUNK):
        p = np.abs(psi[st : st + CHUNK]).astype(np.float64) ** 2
        z = 1 - 2 * _bits(st, st + len(p), n).astype(np.float64)
        for k, terms in parsed.items():
            out[k] += sum(w * float(p @ np.prod(z[:, qs], axis=1)) for qs, w in terms)
    return out


def evolve(n: int, layers, snap_cycles) -> dict[int, dict[str, float]]:
    obs = observables(n, layers)
    psi = np.zeros(1 << n, dtype=np.complex64)
    psi[0] = 1
    res = {}
    for cyc in range(1, max(snap_cycles) + 1):
        for lay in layers:
            apply_rx_all(psi, n, TX / 3)
            apply_diag(psi, n, TZ / 3, TZZ, lay)
        if cyc in snap_cycles:
            res[cyc] = expect(psi, n, obs)
            print(
                f"n={n} cycle {cyc}: " + ", ".join(f"{k}={v:.6f}" for k, v in res[cyc].items()),
                flush=True,
            )
    return res


def validate() -> bool:
    from qiskit.quantum_info import SparsePauliOp, Statevector

    _, layers = patch(12)
    obs = observables(12, layers)
    got = evolve(12, layers, {3, 5})
    worst = 0.0
    for cyc in (3, 5):
        sv = Statevector(build(12, layers, cyc))
        for k, terms in obs.items():
            ref = float(np.real(sv.expectation_value(SparsePauliOp.from_list(terms))))
            worst = max(worst, abs(ref - got[cyc][k]))
    print(f"validate 12q vs qiskit: max abs err {worst:.2e}")
    return worst < 1e-5


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=27)
    ap.add_argument("--validate", action="store_true")
    a = ap.parse_args()
    if a.validate:
        return 0 if validate() else 1
    rows = []
    for f in (f"floquet_patch{a.n}.json", f"floquet_patch{a.n}_27cyc.json"):
        p = HERE / "results" / f
        if p.exists():
            rows += [r for r in json.loads(p.read_text()) if r.get("exact") is not None]
    cycles = sorted({r["cycles"] for r in rows})
    _, layers = patch(a.n)
    t0 = time.time()
    local = evolve(a.n, layers, set(cycles))
    cmp = [
        {
            "cycles": r["cycles"],
            "obs": r["obs"],
            "bluequbit_exact": r["exact"],
            "local_c64": local[r["cycles"]][r["obs"]],
            "abs_diff": abs(r["exact"] - local[r["cycles"]][r["obs"]]),
        }
        for r in rows
    ]
    out = {
        "n": a.n,
        "seconds": round(time.time() - t0, 1),
        "max_abs_diff": max(c["abs_diff"] for c in cmp),
        "points": cmp,
    }
    (HERE / "results" / f"xcheck_local{a.n}.json").write_text(json.dumps(out, indent=1))
    print(f"n={a.n}: {len(cmp)} points, max |BlueQubit - local| = {out['max_abs_diff']:.2e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
