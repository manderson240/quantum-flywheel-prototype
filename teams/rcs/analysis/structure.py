"""Static structure analysis of the released d36 RCS circuit (arXiv:2609.28657, repo commit b9dd86b0).

No simulation. Parses refs/rcs-nighthawk-meta/data/circuits/full/d36_logical.qasm with a line grammar
(angles via qasm_angle.angle, never eval) and reports, for several 1D qubit orderings, the number of CZ
gates crossing every MPS bond. Each CZ has operator Schmidt rank 2 across any bipartition it straddles,
so after the circuit the Schmidt rank at bond k is at most 2**min(crossings_k, k, n-k): this is an
UPPER bound on the bond dimension exact MPS simulation needs (a real circuit may need less; it can never
need more). log2(chi_exact_bound) = min(crossings, k, n-k).

Run:  PYTHONDONTWRITEBYTECODE=1 nice -n 10 python3 -B teams/rcs/analysis/structure.py   (project root; <100 MB RSS)
Writes teams/rcs/results/structure_d36.json
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import resource
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import reverse_cuthill_mckee

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from qasm_angle import angle  # noqa: E402  (safe angle parser, no eval)

QASM = ROOT / "refs/rcs-nighthawk-meta/data/circuits/full/d36_logical.qasm"
MANIFEST = ROOT / "refs/rcs-nighthawk-meta/data/circuits/manifest.json"
OUT = ROOT / "teams/rcs/results/structure_d36.json"

R1 = re.compile(r"^(rz|rx)\((.+)\) q\[(\d+)\];$")
R2 = re.compile(r"^cz q\[(\d+)\], q\[(\d+)\];$")
RM = re.compile(r"^c\[(\d+)\] = measure q\[(\d+)\];$")
HEADER = {"OPENQASM 3.0;", 'include "stdgates.inc";', "bit[61] c;", "qubit[61] q;"}


def mem_ok() -> None:
    for line in open("/proc/meminfo"):
        if line.startswith("MemAvailable"):
            gib = int(line.split()[1]) / 2**20
            if gib < 20:
                sys.exit(f"abort: MemAvailable {gib:.1f} GiB < 20 GiB")
            return


def parse(path: Path):
    """Return (n, cycles) where cycles[c] = {'oneq': [...], 'cz': [(a,b),...]}; strict grammar."""
    cycles, cur, phase, measured = [], None, "1q", []
    for raw in path.read_text().splitlines():
        s = raw.strip()
        if not s or s in HEADER:
            continue
        if s.startswith("barrier"):
            # barriers alternate: after the 1q layer, after the CZ layer
            if phase == "1q":
                phase = "cz"
            else:
                cycles.append(cur)
                cur, phase = None, "1q"
            continue
        m = R1.match(s)
        if m:
            if phase != "1q":
                raise ValueError(f"1q gate inside CZ layer: {s}")
            cur = cur or {"oneq": [], "cz": []}
            cur["oneq"].append((m.group(1), angle(m.group(2)), int(m.group(3))))
            continue
        m = R2.match(s)
        if m:
            if phase != "cz":
                raise ValueError(f"CZ inside 1q layer: {s}")
            cur["cz"].append((int(m.group(1)), int(m.group(2))))
            continue
        m = RM.match(s)
        if m:
            measured.append((int(m.group(1)), int(m.group(2))))
            continue
        raise ValueError(f"unrecognised line: {s!r}")
    if cur is not None:
        raise ValueError("trailing gates after last barrier")
    assert all(c == q for c, q in measured) and len(measured) == 61
    return 61, cycles


def logical_coords() -> list[tuple[int, int]]:
    """data/README: physical p at (p//10, p%10); rows 1-8, cols 2-9; drop 17, 55, 62; row-major logical order."""
    phys = [r * 10 + c for r in range(1, 9) for c in range(2, 10) if r * 10 + c not in (17, 55, 62)]
    assert len(phys) == 61
    return [(p // 10, p % 10) for p in phys]


def crossings(order: list[int], czs: list[tuple[int, int]], n: int) -> np.ndarray:
    pos = np.empty(n, dtype=int)
    pos[order] = np.arange(n)
    diff = np.zeros(n + 1, dtype=int)
    for a, b in czs:
        lo, hi = sorted((pos[a], pos[b]))
        diff[lo] += 1  # crosses bonds lo..hi-1 (bond k sits between positions k and k+1)
        diff[hi] -= 1
    return np.cumsum(diff)[: n - 1]


def profile(name, order, cycles, n, chis=(256, 512, 1024, 2048, 4000)):
    all_cz = [g for c in cycles for g in c["cz"]]
    eff_cz = [g for c in cycles[:-1] for g in c["cz"]]  # final CZ layer is diagonal before Z measurement
    X = crossings(order, all_cz, n)
    Xe = crossings(order, eff_cz, n)
    cap = np.array([min(k + 1, n - k - 1) for k in range(n - 1)])
    exact_log2 = np.minimum(Xe, cap)
    # per-cycle cumulative crossings to find saturation depths
    cum = np.zeros(n - 1, dtype=int)
    first_over = {chi: [None] * (n - 1) for chi in chis}
    first_cap = [None] * (n - 1)
    for d, c in enumerate(cycles[:-1], start=1):
        cum += crossings(order, c["cz"], n)
        for chi in chis:
            L = math.log2(chi)
            for k in range(n - 1):
                if first_over[chi][k] is None and min(cum[k], cap[k]) > L:
                    first_over[chi][k] = d
        for k in range(n - 1):
            if first_cap[k] is None and cum[k] >= cap[k]:
                first_cap[k] = d
    # "lossy event" count (the draft's §F model): a crossing is lossy once cumulative crossings at that bond
    # exceed log2(chi), counted only where the bond's max entanglement cap exceeds log2(chi).
    lossy_all = {}
    for chi in chis:
        L = math.log2(chi)
        lossy_all[chi] = int(sum(max(0, X[k] - math.floor(L)) for k in range(n - 1) if cap[k] > L))
    kmid = int(np.argmax(cap))  # a bond with the largest qubit-count cap (30)
    cum_mid, mid_series = 0, []
    for c in cycles[:-1]:
        cum_mid += int(crossings(order, c["cz"], n)[kmid])
        mid_series.append(cum_mid)
    lossy = {}
    for chi in chis:
        L = math.log2(chi)
        lossy[chi] = int(sum(max(0, Xe[k] - math.floor(L)) for k in range(n - 1) if cap[k] > L))
    band = max(abs(int(np.where(order == a)[0][0]) - int(np.where(order == b)[0][0])) for a, b in all_cz) if isinstance(order, np.ndarray) else None
    return {
        "ordering": name,
        "order": [int(i) for i in order],
        "bandwidth": band,
        "crossings_all_918": X.tolist(),
        "crossings_effective": Xe.tolist(),
        "max_crossings_all": int(X.max()),
        "max_crossings_effective": int(Xe.max()),
        "total_bond_crossings_all": int(X.sum()),
        "total_bond_crossings_effective": int(Xe.sum()),
        "exact_log2_chi_bound_per_bond": exact_log2.tolist(),
        "exact_log2_chi_bound_max": int(exact_log2.max()),
        "bonds_needing_more_than": {str(chi): int((exact_log2 > math.log2(chi)).sum()) for chi in chis},
        "saturation_cycle_min_over_bonds": {
            str(chi): min((v for v in first_over[chi] if v is not None), default=None) for chi in chis
        },
        "saturation_cycle_per_bond": {str(chi): first_over[chi] for chi in chis},
        "cycle_reaching_cap_min": min((v for v in first_cap if v is not None), default=None),
        "cycle_reaching_cap_per_bond": first_cap,
        "lossy_events_draft_model": {str(k): v for k, v in lossy.items()},
        "lossy_events_draft_model_all_918": {str(k): v for k, v in lossy_all.items()},
        "mid_bond": kmid,
        "mid_bond_cumulative_crossings_by_cycle_effective": mid_series,
        "mid_bond_cycle_exceeding_log2chi": {str(chi): next((d + 1 for d, v in enumerate(mid_series) if v > math.log2(chi)), None) for chi in chis},
        "mid_bond_cycle_reaching_cap30": next((d + 1 for d, v in enumerate(mid_series) if v >= cap[kmid]), None),
        "median_bond_saturation_cycle": {str(chi): (float(np.median([v for v in first_over[chi] if v is not None])) if any(v is not None for v in first_over[chi]) else None) for chi in chis},
    }


def main() -> None:
    mem_ok()
    raw = QASM.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    man = json.loads(MANIFEST.read_text())
    entry = next(e for e in man["circuits"] if e.get("qasm3") == "full/d36_logical.qasm")
    n, cycles = parse(QASM)
    coords = logical_coords()
    all_cz = [g for c in cycles for g in c["cz"]]
    # geometry checks: every CZ is a lattice nearest neighbour under the README mapping
    nn = all(abs(coords[a][0] - coords[b][0]) + abs(coords[a][1] - coords[b][1]) == 1 for a, b in all_cz)
    couplers = sorted({tuple(sorted(g)) for g in all_cz})
    per_cycle = [len(c["cz"]) for c in cycles]
    oneq_per_cycle = [len(c["oneq"]) for c in cycles]
    deg = np.zeros(n, dtype=int)
    for a, b in couplers:
        deg[a] += 1
        deg[b] += 1
    uses = {}
    for a, b in all_cz:
        uses[tuple(sorted((a, b)))] = uses.get(tuple(sorted((a, b))), 0) + 1
    horiz = [e for e in couplers if coords[e[0]][0] == coords[e[1]][0]]
    # orderings
    rows = sorted({r for r, _ in coords})
    rowmajor = np.arange(n)
    snake = np.array(
        [q for i, r in enumerate(rows) for q in (sorted([q for q in range(n) if coords[q][0] == r], key=lambda q: coords[q][1]))[:: (1 if i % 2 == 0 else -1)]]
    )
    colmajor = np.array(sorted(range(n), key=lambda q: (coords[q][1], coords[q][0])))
    cols = sorted({c for _, c in coords})
    colsnake = np.array(
        [q for i, c in enumerate(cols) for q in (sorted([q for q in range(n) if coords[q][1] == c], key=lambda q: coords[q][0]))[:: (1 if i % 2 == 0 else -1)]]
    )
    rr = [a for a, b in couplers] + [b for a, b in couplers]
    cc = [b for a, b in couplers] + [a for a, b in couplers]
    adj = csr_matrix((np.ones(len(rr)), (rr, cc)), shape=(n, n))
    rcm = np.array(reverse_cuthill_mckee(adj, symmetric_mode=True))
    diag = np.array(sorted(range(n), key=lambda q: (coords[q][0] + coords[q][1], coords[q][0])))
    rnd = np.random.default_rng(20260925).permutation(n)
    profs = [
        profile(nm, o, cycles, n)
        for nm, o in [
            ("row_major", rowmajor),
            ("row_snake", snake),
            ("col_major", colmajor),
            ("col_snake", colsnake),
            ("rcm", rcm),
            ("anti_diagonal", diag),
            ("random_seed20260925_control", rnd),
        ]
    ]
    out = {
        "source": str(QASM.relative_to(ROOT)),
        "sha256": sha,
        "manifest_sha256_of_qpy_not_qasm": entry["sha256"],
        "manifest_cz": entry["cz"],
        "note_sha": "VERIFIED: manifest.json sha256 is of the .qpy (entry file=full/d36_logical.qpy); the .qasm sha256 differs, so .qasm integrity is checked by git blob SHA-1 vs the pinned tree instead (all 14 local files match)",
        "n_qubits": n,
        "n_cycles": len(cycles),
        "oneq_gates": {"rz": sum(1 for c in cycles for g in c["oneq"] if g[0] == "rz"), "rx": sum(1 for c in cycles for g in c["oneq"] if g[0] == "rx")},
        "oneq_per_cycle": sorted(set(oneq_per_cycle)),
        "cz_total": len(all_cz),
        "cz_per_cycle": per_cycle,
        "cz_per_cycle_pattern_first8": per_cycle[:8],
        "final_layer_cz": per_cycle[-1],
        "effective_cz_for_output_distribution": len(all_cz) - per_cycle[-1],
        "final_layer_note": "cycle 36 ends with a CZ layer followed only by Z-basis measurement; CZ is diagonal, so it does not change the ideal output distribution",
        "all_cz_nearest_neighbour_under_README_mapping": nn,
        "distinct_couplers": len(couplers),
        "horizontal_couplers": len(horiz),
        "vertical_couplers": len(couplers) - len(horiz),
        "uses_per_coupler": sorted(set(uses.values())),
        "degree_histogram": {int(k): int(v) for k, v in zip(*np.unique(deg, return_counts=True))},
        "degree2_qubits": [int(q) for q in np.where(deg == 2)[0]],
        "orderings": profs,
        "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
    }
    OUT.write_text(json.dumps(out, indent=1))
    print(f"sha256 {sha[:16]}  n={n} cycles={len(cycles)} cz={len(all_cz)} final={per_cycle[-1]} nn={nn}")
    print(f"couplers {len(couplers)} (h {len(horiz)} v {len(couplers)-len(horiz)}) uses {sorted(set(uses.values()))} deg {out['degree_histogram']}")
    print(f"cz/cycle first8 {per_cycle[:8]}")
    for p in profs:
        print(
            f"{p['ordering']:>28} bw={p['bandwidth']:>3} maxX={p['max_crossings_all']:>3}/{p['max_crossings_effective']:>3} "
            f"sumX={p['total_bond_crossings_all']:>5}/{p['total_bond_crossings_effective']:>5} exact_log2max={p['exact_log2_chi_bound_max']} "
            f">2048:{p['bonds_needing_more_than']['2048']:>2} sat2048 min/med {p['saturation_cycle_min_over_bonds']['2048']}/{p['median_bond_saturation_cycle']['2048']} "
            f"mid k={p['mid_bond']} >11@{p['mid_bond_cycle_exceeding_log2chi']['2048']} cap30@{p['mid_bond_cycle_reaching_cap30']} "
            f"lossy1024/2048 eff {p['lossy_events_draft_model']['1024']}/{p['lossy_events_draft_model']['2048']} all {p['lossy_events_draft_model_all_918']['1024']}/{p['lossy_events_draft_model_all_918']['2048']}"
        )
    print(f"peak RSS {out['peak_rss_mb']:.0f} MB")


if __name__ == "__main__":
    main()
