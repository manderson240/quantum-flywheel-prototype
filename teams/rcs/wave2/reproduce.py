"""rcs wave 2: independent reproduction of the released d36 patch-XEB numbers (PREREG.md, hash in PREREG.sha16).

Own implementation (numpy statevector, no Qiskit in the primary path). Conventions follow PREREG.md §3.
Controls P1 / N1 / N2 per PREREG.md §6. Resource rules per §7 (MemAvailable floor 20 GiB with capped backoff,
RSS guard 0.9 GB, run under nice -n 10). Counts via np.load(allow_pickle=False); nothing unpickled.

Run (project root):  PYTHONDONTWRITEBYTECODE=1 nice -n 10 python3 -B teams/rcs/wave2/reproduce.py
Writes teams/rcs/wave2/results/{controls,per_circuit,pooled,comparison}.json
"""

from __future__ import annotations

import hashlib
import json
import math
import resource
import sys
import time
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from qasm_patch import parse_qasm  # noqa: E402


DATA = ROOT / "refs/rcs-nighthawk-data"
META = ROOT / "refs/rcs-nighthawk-meta"
OUT = HERE / "results"
FLOOR_GIB = 20.0
BACKOFF = [60, 120, 240, 480] + [600] * 10
WAIT_CAP_S = 3600
RSS_CAP_KB = int(0.9 * 1024**2)
LOG: list = []


def log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    LOG.append(line)
    print(line, flush=True)


def mem_available_gib() -> float:
    for line in open("/proc/meminfo"):
        if line.startswith("MemAvailable"):
            return int(line.split()[1]) / 2**20
    raise RuntimeError("no MemAvailable")


def wait_for_memory(tag: str) -> bool:
    """PREREG §7: wait with backoff while MemAvailable < 20 GiB; cap 60 min; False = DEFERRED."""
    waited = 0
    for delay in BACKOFF:
        gib = mem_available_gib()
        if gib >= FLOOR_GIB:
            return True
        if waited + delay > WAIT_CAP_S:
            break
        log(f"{tag}: MemAvailable {gib:.1f} GiB < {FLOOR_GIB}; waiting {delay} s")
        time.sleep(delay)
        waited += delay
    ok = mem_available_gib() >= FLOOR_GIB
    if not ok:
        log(f"{tag}: DEFERRED after {waited} s wait")
    return ok


def rss_guard() -> None:
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > RSS_CAP_KB:
        raise MemoryError("RSS guard 0.9 GB exceeded")


# ---------------------------------------------------------------- simulator (own implementation)
def rz(t: float) -> np.ndarray:
    return np.array([[np.exp(-0.5j * t), 0], [0, np.exp(0.5j * t)]], dtype=complex)


def rx(t: float) -> np.ndarray:
    c, s = math.cos(t / 2), math.sin(t / 2)
    return np.array([[c, -1j * s], [-1j * s, c]], dtype=complex)


GATE = {"rz": rz, "rx": rx}


def _apply_1q(psi: np.ndarray, n: int, j: int, m: np.ndarray) -> None:
    """In place: qubit j (little-endian: index bit j) is tensor axis n-1-j of psi.reshape((2,)*n)."""
    v = psi.reshape((2,) * n)
    ax = n - 1 - j
    i0 = tuple(0 if a == ax else slice(None) for a in range(n))
    i1 = tuple(1 if a == ax else slice(None) for a in range(n))
    s0 = v[i0].copy()
    s1 = v[i1]
    v[i0] = m[0, 0] * s0 + m[0, 1] * s1
    v[i1] = m[1, 0] * s0 + m[1, 1] * s1


def _apply_cz(psi: np.ndarray, n: int, a: int, b: int) -> None:
    v = psi.reshape((2,) * n)
    idx = tuple(1 if ax in (n - 1 - a, n - 1 - b) else slice(None) for ax in range(n))
    v[idx] *= -1.0


def statevector(gates, n: int) -> np.ndarray:
    """gates: list of (name, local_q, angle) / ('cz', a, b) in circuit order, local qubit indices 0..n-1."""
    psi = np.zeros(2**n, dtype=np.complex128)
    psi[0] = 1.0
    pending = [None] * n

    def flush(q):
        if pending[q] is not None:
            _apply_1q(psi, n, q, pending[q])
            pending[q] = None

    for g in gates:
        if g[0] == "cz":
            flush(g[1])
            flush(g[2])
            _apply_cz(psi, n, g[1], g[2])
        else:
            m = GATE[g[0]](g[2])
            pending[g[1]] = m if pending[g[1]] is None else m @ pending[g[1]]
    for q in range(n):
        flush(q)
    return psi


def dense_reference(gates, n: int) -> np.ndarray:
    """Independent check: full 2^n x 2^n operator per gate (np.kron, qubit n-1 leftmost), applied to the vector."""
    psi = np.zeros(2**n, dtype=np.complex128)
    psi[0] = 1.0
    eye = np.eye(2, dtype=complex)
    for g in gates:
        if g[0] == "cz":
            d = np.ones(2**n)
            x = np.arange(2**n)
            d[((x >> g[1]) & 1) & ((x >> g[2]) & 1) == 1] = -1
            psi = d * psi
        else:
            op = np.array([[1.0 + 0j]])
            for q in range(n - 1, -1, -1):
                op = np.kron(op, GATE[g[0]](g[2]) if q == g[1] else eye)
            psi = op @ psi
    return psi


# ---------------------------------------------------------------- estimator (PREREG §3)
def sub_bits(shots: np.ndarray, qubits) -> np.ndarray:
    out = np.zeros(shots.shape, dtype=np.int64)
    for j, q in enumerate(qubits):
        out |= ((shots >> np.uint64(q)) & np.uint64(1)).astype(np.int64) << j
    return out


def product_se(means: np.ndarray, cov: np.ndarray) -> float:
    k = len(means)
    g = np.array([np.prod([means[m] for m in range(k) if m != i]) for i in range(k)])
    h = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            if i != j:
                h[i, j] = np.prod([means[m] for m in range(k) if m not in (i, j)])
    ch = cov @ h
    return math.sqrt(max(float(g @ cov @ g) + 0.5 * float(np.trace(ch @ ch)), 0.0))


def patch_gates(circ: dict, qubits) -> list:
    loc = {q: j for j, q in enumerate(qubits)}
    out = []
    for g in circ["gates"]:
        if g[0] == "cz":
            if g[1] in loc and g[2] in loc:
                out.append(("cz", loc[g[1]], loc[g[2]]))
            elif g[1] in loc or g[2] in loc:
                raise ValueError("CZ crosses patch boundary")
        elif g[1] in loc:
            out.append((g[0], loc[g[1]], g[2]))
    return out


def patch_probs(circ: dict, patch_qubits: dict) -> dict:
    probs = {}
    for name, qs in patch_qubits.items():
        psi = statevector(patch_gates(circ, qs), len(qs))
        probs[name] = psi.real**2 + psi.imag**2
        del psi
        rss_guard()
    return probs


def xeb(shots: np.ndarray, probs: dict, patch_qubits: dict, reverse_bits: bool = False) -> dict:
    names = list(patch_qubits)
    ideal = {p: float(probs[p].size * np.dot(probs[p], probs[p]) - 1.0) for p in names}
    scores = []
    for p in names:
        qs = patch_qubits[p][::-1] if reverse_bits else patch_qubits[p]
        pr = probs[p]
        scores.append((pr.size * pr[sub_bits(shots, qs)] - 1.0) / ideal[p])
    scores = np.array(scores)
    means = scores.mean(axis=1)
    cov = np.atleast_2d(np.cov(scores, bias=True)) / scores.shape[1]
    return {
        "fidelity": float(np.prod(means)),
        "se": product_se(means, cov),
        "patch_fidelity": {p: float(m) for p, m in zip(names, means)},
        "patch_ideal_xeb": ideal,
        "patch_qubits": {p: len(patch_qubits[p]) for p in names},
        "shots": int(shots.size),
    }


def ivw(values, ses):
    w = 1.0 / np.asarray(ses, dtype=float) ** 2
    return float(np.sum(w * np.asarray(values)) / np.sum(w)), float(math.sqrt(1.0 / np.sum(w)))


# ---------------------------------------------------------------- tiers (PREREG §5)
def tier(mine: float, rel: float) -> tuple:
    rho = abs(mine - rel) / abs(rel)
    return rho, ("EXACT" if rho <= 1e-6 else "NUMERICAL" if rho <= 1e-3 else "DISCREPANT")


WORST = {"EXACT": 0, "NUMERICAL": 1, "DISCREPANT": 2}


def load_counts(k: int) -> dict:
    with np.load(DATA / f"data/counts/patched_K{k}_d36.npz", allow_pickle=False) as z:
        return {name: z[name] for name in z.files}


def circuit_path(k, j, i) -> Path:
    return DATA / f"data/circuits/patched/K{k}/d36/partition{j}_instance{i}.qasm"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    prereg = (HERE / "PREREG.md").read_bytes()
    frozen = (HERE / "PREREG.sha16").read_text().strip()
    assert hashlib.sha256(prereg).hexdigest()[:16] == frozen, "PREREG.md changed after freeze"
    log(f"PREREG hash verified {frozen}; MemAvailable {mem_available_gib():.1f} GiB")
    layout = json.loads((DATA / "data/layout.json").read_text())
    released = [
        r
        for r in json.loads((DATA / "data/results/patch_xeb.json").read_text())
        if r["depth"] == 36
    ]
    fvd = json.loads((META / "data/results/fidelity_vs_depth.json").read_text())["points"]

    # ---- P1: simulator control
    controls = {}
    if not wait_for_memory("P1"):
        sys.exit("P1 deferred: cannot run the instrument control")
    c = parse_qasm(circuit_path(4, 0, 0))
    block = layout["partitions"]["4"][0]["patch_qubits"]["0"][:10]
    loc = {q: j for j, q in enumerate(block)}
    g10 = [
        ("cz", loc[g[1]], loc[g[2]]) if g[0] == "cz" else (g[0], loc[g[1]], g[2])
        for g in c["gates"]
        if (g[0] != "cz" and g[1] in loc) or (g[0] == "cz" and g[1] in loc and g[2] in loc)
    ]
    p_mine = np.abs(statevector(g10, 10)) ** 2
    p_dense = np.abs(dense_reference(g10, 10)) ** 2
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector

    qc = QuantumCircuit(10)
    for g in g10:
        getattr(qc, g[0])(*((g[1], g[2]) if g[0] == "cz" else (g[2], g[1])))
    p_qk = Statevector.from_label("0" * 10).evolve(qc).probabilities()
    controls["P1"] = {
        "n_gates": len(g10),
        "max_abs_dp_vs_dense": float(np.max(np.abs(p_mine - p_dense))),
        "max_abs_dp_vs_qiskit_calls": float(np.max(np.abs(p_mine - p_qk))),
    }
    controls["P1"]["pass"] = (
        max(controls["P1"]["max_abs_dp_vs_dense"], controls["P1"]["max_abs_dp_vs_qiskit_calls"])
        <= 1e-12
    )
    log(f"P1 {controls['P1']}")
    if not controls["P1"]["pass"]:
        (OUT / "controls.json").write_text(json.dumps(controls, indent=1))
        sys.exit("P1 FAILED: instrument bug; stop")

    # ---- main reproduction (30 circuits)
    per_circuit, cache = [], {}
    for k in (3, 4):
        counts = load_counts(k)
        for j, part in enumerate(layout["partitions"][str(k)]):
            pq = part["patch_qubits"]
            for i in range(3):
                tag = f"K{k}/p{j}/i{i}"
                rec = {"K": k, "depth": 36, "partition": j, "instance": i, "status": "missing"}
                if wait_for_memory(tag):
                    for attempt in (1, 2):
                        try:
                            t0 = time.time()
                            probs = patch_probs(parse_qasm(circuit_path(k, j, i)), pq)
                            rec.update(
                                xeb(counts[f"partition{j}_instance{i}"], probs, pq),
                                status="ok",
                                seconds=round(time.time() - t0, 1),
                            )
                            if k == 3 and j == 0:
                                cache[i] = probs
                            break
                        except (MemoryError, ValueError) as e:
                            log(f"{tag} attempt {attempt} failed: {e!r}")
                            rec["error"] = repr(e)
                else:
                    rec["status"] = "deferred"
                per_circuit.append(rec)
                log(
                    f"{tag} {rec['status']} F={rec.get('fidelity')} rss={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024} MB"
                )
        del counts

    # ---- N1 / N2 negative controls (K3 partition 0)
    c3 = load_counts(3)
    pq0 = layout["partitions"]["3"][0]["patch_qubits"]
    if len(cache) == 3:
        controls["N1"] = []
        for i in range(3):
            r = xeb(c3[f"partition0_instance{i}"], cache[(i + 1) % 3], pq0)
            controls["N1"].append(
                {
                    "counts_instance": i,
                    "circuit_instance": (i + 1) % 3,
                    "fidelity": r["fidelity"],
                    "se": r["se"],
                    "abs_F_over_se": abs(r["fidelity"]) / r["se"],
                    "pass": abs(r["fidelity"]) <= 5 * r["se"],
                }
            )
        r = xeb(c3["partition0_instance0"], cache[0], pq0, reverse_bits=True)
        controls["N2"] = {
            "fidelity": r["fidelity"],
            "se": r["se"],
            "abs_F_over_se": abs(r["fidelity"]) / r["se"],
            "pass": abs(r["fidelity"]) <= 5 * r["se"],
        }
    log(f"N1 {controls.get('N1')}  N2 {controls.get('N2')}")
    (OUT / "controls.json").write_text(json.dumps(controls, indent=1))
    (OUT / "per_circuit.json").write_text(json.dumps(per_circuit, indent=1))

    # ---- comparison (PREREG §4, §5)
    rel_by = {(r["K"], r["partition"], r["instance"]): r for r in released}
    units = []
    for m in per_circuit:
        key = (m["K"], m["partition"], m["instance"])
        rr = rel_by[key]
        if m["status"] != "ok":
            units.append({"unit": f"K{key[0]}/p{key[1]}/i{key[2]}", "tier": "MISSING"})
            continue
        fields = {"fidelity": (m["fidelity"], rr["fidelity"]), "se": (m["se"], rr["se"])}
        for p in rr["patch_fidelity"]:
            fields[f"patch_fidelity[{p}]"] = (m["patch_fidelity"][p], rr["patch_fidelity"][p])
            fields[f"patch_ideal_xeb[{p}]"] = (m["patch_ideal_xeb"][p], rr["patch_ideal_xeb"][p])
        comp = {
            f: dict(zip(("mine", "released"), v), **dict(zip(("rho", "tier"), tier(*v))))
            for f, v in fields.items()
        }
        worst = max((c["tier"] for c in comp.values()), key=WORST.get)
        units.append(
            {
                "unit": f"K{key[0]}/p{key[1]}/i{key[2]}",
                "tier": worst,
                "fields": comp,
                "abs_dF_over_released_se": abs(m["fidelity"] - rr["fidelity"]) / rr["se"],
                "patch_sizes_match": m["patch_qubits"] == rr["patch_qubits"],
                "shots_match": m["shots"] == rr["shots"],
            }
        )
    pooled = {}
    for k, label in ((3, "3-patch"), (4, "4-patch")):
        mine = [m for m in per_circuit if m["K"] == k and m["status"] == "ok"]
        rel_k = [r for r in released if r["K"] == k]
        f_rel_recs = ivw([r["fidelity"] for r in rel_k], [r["se"] for r in rel_k])
        if len(mine) == 15:
            f_mine = ivw([m["fidelity"] for m in mine], [m["se"] for m in mine])
            ft, st = (
                tier(f_mine[0], fvd[label]["36"]["fidelity"]),
                tier(f_mine[1], fvd[label]["36"]["se"]),
            )
            units.append(
                {
                    "unit": f"pooled {label} d36",
                    "tier": max(ft[1], st[1], key=WORST.get),
                    "fields": {
                        "fidelity": {
                            "mine": f_mine[0],
                            "released": fvd[label]["36"]["fidelity"],
                            "rho": ft[0],
                            "tier": ft[1],
                        },
                        "se": {
                            "mine": f_mine[1],
                            "released": fvd[label]["36"]["se"],
                            "rho": st[0],
                            "tier": st[1],
                        },
                    },
                    "abs_dF_over_released_se": abs(f_mine[0] - fvd[label]["36"]["fidelity"])
                    / fvd[label]["36"]["se"],
                }
            )
        else:
            units.append({"unit": f"pooled {label} d36", "tier": "MISSING"})
        pooled[label] = {
            "mine": units[-1].get("fields"),
            "pooling_rule_on_released_records": {
                "fidelity": f_rel_recs[0],
                "se": f_rel_recs[1],
                "rho_vs_fidelity_vs_depth_json": tier(f_rel_recs[0], fvd[label]["36"]["fidelity"])[
                    0
                ],
            },
        }
    tally = {
        t: sum(u["tier"] == t for u in units)
        for t in ("EXACT", "NUMERICAL", "DISCREPANT", "MISSING")
    }
    if tally["EXACT"] == 32:
        verdict = "REPRODUCED"
    elif tally["DISCREPANT"] >= 16:
        verdict = "NOT REPRODUCED"
    elif tally["EXACT"] + tally["NUMERICAL"] == 32:
        verdict = "REPRODUCED-NUMERICAL"
    else:
        verdict = f"PARTIAL ({tally['EXACT']}/32 EXACT, {tally['DISCREPANT']}/32 DISCREPANT, {tally['MISSING']} missing)"
    all_rho = {
        f: max(u["fields"][f]["rho"] for u in units if "fields" in u and f in u["fields"])
        for f in ("fidelity", "se")
    }
    summary = {
        "prereg_sha16": frozen,
        "verdict": verdict,
        "tally": tally,
        "n_units": len(units),
        "max_rho": all_rho,
        "max_rho_patch_fidelity": max(
            v["rho"]
            for u in units
            if "fields" in u
            for f, v in u["fields"].items()
            if f.startswith("patch_fidelity")
        ),
        "max_rho_patch_ideal_xeb": max(
            v["rho"]
            for u in units
            if "fields" in u
            for f, v in u["fields"].items()
            if f.startswith("patch_ideal_xeb")
        ),
        "max_abs_dF_over_released_se": max(
            u["abs_dF_over_released_se"] for u in units if "abs_dF_over_released_se" in u
        ),
    }
    (OUT / "pooled.json").write_text(json.dumps(pooled, indent=1))
    (OUT / "comparison.json").write_text(
        json.dumps({"summary": summary, "units": units, "log": LOG}, indent=1)
    )
    log(f"SUMMARY {json.dumps(summary)}")


if __name__ == "__main__":
    main()
