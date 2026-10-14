"""Wave-2 pre-freeze structural checks (NO simulation, NO XEB). rcs team, 2026-09-25.

1. Integrity: git blob SHA-1 (computed by hand: sha1(b"blob <len>\\0" + bytes)) of every d36 file used,
   against teams/rcs/results/repo_tree_b9dd86b0.json (pinned commit b9dd86b0).
2. Partition <-> file mapping: for each patched d36 circuit, the CZs absent relative to the full d36
   circuit must be exactly (boundary edges of layout.partitions[K][j]) x 9 uses; no surviving CZ may cross
   patches; measurement is c[i] = q[i]; the 1q-gate/CZ skeleton parses under a strict grammar.
3. Counts: np.load(allow_pickle=False); 15 keys per K; dtype uint64; shot counts; all values < 2**61.

Run (project root): nice -n 10 python3 -B teams/rcs/wave2/precheck.py
Writes teams/rcs/wave2/results/precheck.json
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from qasm_patch import parse_qasm  # noqa: E402


DATA = ROOT / "refs/rcs-nighthawk-data"
META = ROOT / "refs/rcs-nighthawk-meta"
TREE = ROOT / "teams/rcs/results/repo_tree_b9dd86b0.json"


def blob_sha1(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def main() -> None:
    tree = {e["path"]: e for e in json.loads(TREE.read_text())["tree"] if e["type"] == "blob"}
    files = [
        "analysis/compute_patch_xeb.py",
        "rcs/estimators.py",
        "rcs/io.py",
        "rcs/simulate.py",
        "data/layout.json",
        "data/results/patch_xeb.json",
        "data/counts/patched_K3_d36.npz",
        "data/counts/patched_K4_d36.npz",
    ]
    files += [
        f"data/circuits/patched/K{k}/d36/partition{j}_instance{i}.qasm"
        for k in (3, 4)
        for j in range(5)
        for i in range(3)
    ]
    integ = {}
    for f in files:
        local = blob_sha1(DATA / f)
        integ[f] = {
            "local": local,
            "tree": tree[f]["sha"],
            "match": local == tree[f]["sha"],
            "size": tree[f].get("size"),
        }
    full_f = "data/circuits/full/d36_logical.qasm"
    integ["meta:" + full_f] = {
        "local": blob_sha1(META / full_f),
        "tree": tree[full_f]["sha"],
        "match": blob_sha1(META / full_f) == tree[full_f]["sha"],
    }
    fvd = "data/results/fidelity_vs_depth.json"
    integ["meta:" + fvd] = {
        "local": blob_sha1(META / fvd),
        "tree": tree[fvd]["sha"],
        "match": blob_sha1(META / fvd) == tree[fvd]["sha"],
    }

    layout = json.loads((DATA / "data/layout.json").read_text())
    full = parse_qasm(META / full_f)
    full_cz = Counter(tuple(sorted(e)) for layer in full["cz_layers"] for e in layer)
    mapping = {}
    for k in (3, 4):
        for j, part in enumerate(layout["partitions"][str(k)]):
            owner = {q: p for p, qs in part["patch_qubits"].items() for q in qs}
            assert sorted(owner) == list(range(61)), "patches must cover 61 qubits exactly once"
            boundary = {tuple(sorted(e)) for e in part["boundary_edges"]}
            for i in range(3):
                c = parse_qasm(
                    DATA / f"data/circuits/patched/K{k}/d36/partition{j}_instance{i}.qasm"
                )
                cz = Counter(tuple(sorted(e)) for layer in c["cz_layers"] for e in layer)
                missing = full_cz - cz
                extra = cz - full_cz
                crossing = [e for e in cz if owner[e[0]] != owner[e[1]]]
                boundary_true = {e for e in full_cz if owner[e[0]] != owner[e[1]]}
                mapping[f"K{k}/p{j}/i{i}"] = {
                    "n_cz": sum(cz.values()),
                    "n_cycles": len(c["cz_layers"]),
                    "missing_equals_boundary_x9": dict(missing) == dict.fromkeys(boundary, 9),
                    "layout_boundary_equals_true_cut": boundary == boundary_true,
                    "n_boundary": len(boundary),
                    "extra_cz": len(extra),
                    "crossing_cz": len(crossing),
                    "measure_identity": c["measure_identity"],
                    "patch_sizes": {p: len(qs) for p, qs in part["patch_qubits"].items()},
                    "patch_lists_sorted": all(
                        qs == sorted(qs) for qs in part["patch_qubits"].values()
                    ),
                }
    counts = {}
    for k in (3, 4):
        with np.load(DATA / f"data/counts/patched_K{k}_d36.npz", allow_pickle=False) as z:
            for name in z.files:
                a = z[name]
                counts[f"K{k}/{name}"] = {
                    "dtype": str(a.dtype),
                    "shots": int(a.size),
                    "max_lt_2^61": bool(int(a.max()) < 2**61),
                }
    fv = json.loads((META / fvd).read_text())
    released_pooled = {key: fv["points"][key]["36"] for key in ("3-patch", "4-patch", "mirror")}
    out = {
        "integrity": integ,
        "all_integrity_match": all(v["match"] for v in integ.values()),
        "mapping": mapping,
        "counts": counts,
        "released_pooled_d36_fidelity_vs_depth_json": released_pooled,
        "full_circuit_cz": sum(full_cz.values()),
    }
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results/precheck.json").write_text(json.dumps(out, indent=1))
    bad_map = [
        k
        for k, v in mapping.items()
        if not (
            v["missing_equals_boundary_x9"]
            and v["extra_cz"] == 0
            and v["crossing_cz"] == 0
            and v["measure_identity"]
            and v["patch_lists_sorted"]
            and v["layout_boundary_equals_true_cut"]
        )
    ]
    print(
        "integrity all match:",
        out["all_integrity_match"],
        [k for k, v in integ.items() if not v["match"]],
    )
    print("mapping failures:", bad_map)
    print(
        "counts:",
        Counter((v["dtype"], v["shots"], v["max_lt_2^61"]) for v in counts.values()),
        len(counts),
    )
    print("released pooled d36:", released_pooled)
    print("n_cz per circuit:", Counter(v["n_cz"] for v in mapping.values()))


if __name__ == "__main__":
    main()
