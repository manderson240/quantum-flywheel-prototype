"""Compute the exact file sets (paths + byte sizes) needed for (a) patch_xeb reproduction and (b) MPS calibration.

Input: teams/rcs/results/repo_tree_b9dd86b0.json, the GitHub API git-tree listing (recursive) of
BlueQubitDev/rcs-nighthawk at commit b9dd86b016743465ebc97fb9f6677f4a251a3baa (metadata only, no file content).
Output: teams/rcs/results/download_sets.json
"""

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
tree = {e["path"]: e for e in json.loads((HERE / "results/repo_tree_b9dd86b0.json").read_text())["tree"] if e["type"] == "blob"}
LOCAL = {p for p in tree if (HERE.parents[1] / "refs/rcs-nighthawk-meta" / p).exists()}


def pick(pattern):
    return sorted(p for p in tree if re.fullmatch(pattern, p))


code_patch = ["analysis/compute_patch_xeb.py", "analysis/fidelity_vs_depth.py", "rcs/estimators.py", "rcs/patching.py", "rcs/io.py", "rcs/simulate.py", "rcs/circuits.py", "rcs/layout.py"]
sets = {
    "A_min_d36_patch_xeb": {
        "purpose": "reproduce patch_xeb.json at d=36 (K3 and K4, 5 partitions x 3 instances) from released counts",
        "files": ["data/layout.json", "data/results/patch_xeb.json", "data/counts/patched_K3_d36.npz", "data/counts/patched_K4_d36.npz"]
        + pick(r"data/circuits/patched/K[34]/d36/partition\d_instance\d\.qasm")
        + code_patch,
    },
    "A_full_all_depths": {
        "purpose": "reproduce every patch_xeb.json entry and the 3-/4-patch curves of fidelity_vs_depth.json (d20-d40)",
        "files": ["data/layout.json", "data/results/patch_xeb.json"]
        + pick(r"data/counts/patched_K[34]_d\d\d\.npz")
        + pick(r"data/circuits/patched/K[34]/d\d\d/partition\d_instance\d\.qasm")
        + code_patch,
    },
    "B_mps_calibration": {
        "purpose": "finite-fidelity MPS calibration per DRAFT_PREREG_RCS.md: target prefix circuit to 40 cycles, C1 released patches (instance 0), device per-patch fidelities for the descriptive comparison, partitions",
        "files": ["data/circuits/full/d40_logical.qasm", "data/layout.json", "data/results/patch_xeb.json"]
        + pick(r"data/circuits/patched/K[34]/d(20|24|28|32|36|40)/partition\d_instance0\.qasm"),
    },
    "C_optional_audit": {
        "purpose": "optional: logical-vs-executed equivalence check (samples were drawn from d36_executed) and the 10^6 full-circuit samples (sorted uint64; np.load(allow_pickle=False))",
        "files": ["data/circuits/full/d36_executed.qasm", "data/samples/full_d36.npz", "rcs/io.py"],
    },
}
out = {}
for k, v in sets.items():
    files = sorted(set(v["files"]))
    missing = [f for f in files if f not in tree]
    assert not missing, missing
    rows = [{"path": f, "bytes": tree[f]["size"], "git_blob_sha1": tree[f]["sha"], "already_local": f in LOCAL} for f in files]
    need = [r for r in rows if not r["already_local"]]
    out[k] = {"purpose": v["purpose"], "n_files": len(rows), "n_to_download": len(need), "bytes_to_download": sum(r["bytes"] for r in need), "files": rows}
    print(f"{k:>22}: {len(need):>4} files to download, {sum(r['bytes'] for r in need)/1e6:7.2f} MB")
union = {r["path"]: r for v in out.values() for r in v["files"] if not r["already_local"]}
u_ab = {r["path"]: r for k in ("A_min_d36_patch_xeb", "B_mps_calibration") for r in out[k]["files"] if not r["already_local"]}
out["union_A_min_plus_B"] = {"n_files": len(u_ab), "bytes": sum(r["bytes"] for r in u_ab.values())}
out["union_all_sets"] = {"n_files": len(union), "bytes": sum(r["bytes"] for r in union.values())}
out["repo_total"] = {"n_blobs": len(tree), "bytes": sum(e["size"] for e in tree.values())}
print("union A_min+B:", out["union_A_min_plus_B"], " union all:", out["union_all_sets"], " repo:", out["repo_total"])
(HERE / "results/download_sets.json").write_text(json.dumps(out, indent=1))
