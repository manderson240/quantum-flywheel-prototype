"""Collect the χ=512 MPS jobs on the tracker's 51-qubit Floquet circuit (submitted asynchronously 2026-09-23).

Job ids: results/tracker_chi512_jobs.json. Prints status; when all are done, writes
results/tracker_floquet51_chi512.json and reports how the MPS upper edge moved (χ 64 → 256 → 512) against the
published values. Run: python collect_chi512.py   (token read inside the process, never printed)
"""

from __future__ import annotations

import json

from kicked_ising_crosscheck import OUT, load_token


PUB = {
    ("mag", 13): 0.396,
    ("mag", 16): 0.3904,
    ("zzd2", 13): 0.2916,
    ("zzd2", 16): 0.2657,
    ("zzd3", 13): 0.2278,
    ("zzd3", 16): 0.2111,
}  # QESEM (IBM hardware), tracker README


def main() -> int:
    import bluequbit

    bq = bluequbit.init(load_token())
    jobs = json.loads((OUT / "tracker_chi512_jobs.json").read_text())
    sweep = {
        (r["obs"], r["cycles"], r["setting"]): r["value"]
        for r in json.loads((OUT / "tracker_floquet51_sweep.json").read_text())
        if r["method"] == "mps.cpu"
    }
    rows, done = [], True
    for j in jobs:
        r = bq.get(j["job_id"])
        status = getattr(r, "run_status", "?")
        row = {**j, "status": status}
        if status == "COMPLETED":
            row["value"] = float(r.expectation_value)
            row["cost"] = getattr(r, "cost", None)
        else:
            done = False
        rows.append(row)
        k = (j["obs"], j["cycles"])
        chis = " -> ".join(f"{sweep.get((k[0], k[1], c), float('nan')):.4f}" for c in (64, 256))
        print(
            f"{j['obs']:5s} c{j['cycles']}  {status:10s}  chi64/256: {chis}  chi512: "
            f"{row.get('value', float('nan')):.4f}   QESEM {PUB[k]}"
        )
    if done:
        (OUT / "tracker_floquet51_chi512.json").write_text(json.dumps(rows, indent=1))
        print("all complete -> results/tracker_floquet51_chi512.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
