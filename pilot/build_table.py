"""Replay table for the search pilot: every (instance, strategy) run once on BlueQubit, exact value from local statevector.

Instances: 3 Floquet mixed-field Ising configurations (tracker params; (4.7,0.3) colouring 5; (2.4,0.9) colouring 5)
x 9 depths x 3 observables = 81, on the 19-qubit heavy-hex patch. Strategies: Pauli-path δ ∈ {1e-2,1e-3,3e-4,1e-4},
MPS χ ∈ {4,16,32,64,128}. Existing runs in results/floquet_oracle19*.json are reused, not repeated.
Output: pilot/table.json  (searchers read values + fixed costs from it; only the scorer reads "exact").
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
import floquet_oracle19 as o  # noqa: E402
from kicked_ising_crosscheck import OUT, load_token  # noqa: E402


CONFIGS = {
    "tracker": ("", o.TX, o.TZ, 0),
    "c47": ("_tx4.7_tz0.3_c5", 4.7, 0.3, 5),
    "c24": ("_tx2.4_tz0.9_c5", 2.4, 0.9, 5),
}
STRATS = [("pauli-path", d) for d in (1e-2, 1e-3, 3e-4, 1e-4)] + [
    ("mps.cpu", c) for c in (4, 16, 32, 64, 128)
]
OLD = {
    ("pauli-path", 1e-3): "pau_0.001",
    ("pauli-path", 1e-4): "pau_0.0001",
    ("mps.cpu", 16): "mps_16",
    ("mps.cpu", 64): "mps_64",
}


def sid(dev: str, v: float) -> str:
    return f"pp_{v:g}" if dev == "pauli-path" else f"mps_{v:g}"


def main() -> int:
    import bluequbit

    bq = bluequbit.init(load_token())
    n, edges = o.lattice()
    out = HERE / "table.json"
    table = json.loads(out.read_text()) if out.exists() else {}
    for cname, (tag, tx, tz, cseed) in CONFIGS.items():
        old = {
            (r["cycles"], r["obs"]): r
            for r in json.loads((OUT / f"floquet_oracle19{tag}.json").read_text())
        }
        layers = o.three_colour(edges, cseed)
        obs = {"mag": [(o.zlabel(n, (i,)), 1.0 / n) for i in range(n)]}
        for d in (2, 3):
            p = o.pairs_at(n, edges, d)
            obs[f"zzd{d}"] = [(o.zlabel(n, pr), 1.0 / len(p)) for pr in p]
        for (cyc, ob), r in sorted(old.items()):
            iid = f"{cname}|c{cyc}|{ob}"
            ent = table.setdefault(
                iid, {"config": cname, "cycles": cyc, "obs": ob, "exact": r["exact"], "runs": {}}
            )
            qc = None
            for dev, v in STRATS:
                k = sid(dev, v)
                if k in ent["runs"]:
                    continue
                if (dev, v) in OLD and r.get(OLD[(dev, v)]) is not None:
                    ent["runs"][k] = {
                        "value": r[OLD[(dev, v)]],
                        "wall_s": r[OLD[(dev, v)] + "_s"],
                        "reused": True,
                    }
                    continue
                qc = qc or o.circuit(n, layers, cyc, tx, tz)
                key = (
                    "pauli_path_truncation_threshold"
                    if dev == "pauli-path"
                    else "mps_bond_dimension"
                )
                t0 = time.time()
                try:
                    res = bq.run(qc, device=dev, pauli_sum=obs[ob], options={key: v})
                    ent["runs"][k] = {
                        "value": float(res.expectation_value),
                        "wall_s": round(time.time() - t0, 1),
                    }
                except Exception as e:
                    ent["runs"][k] = {
                        "value": None,
                        "wall_s": round(time.time() - t0, 1),
                        "error": str(e)[:160],
                    }
                out.write_text(json.dumps(table, indent=1))
                print(iid, k, ent["runs"][k], flush=True)
    out.write_text(json.dumps(table, indent=1))
    print("instances", len(table), "saved", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
