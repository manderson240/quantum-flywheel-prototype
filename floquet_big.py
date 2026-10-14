"""Runs 2-3: first independent classical bracket for tracker candidates with no/originator-only classical entries.
74qx27c magnetization (QESEM-ZNE 0.365, tracker #236) and 51qx30c magnetization (QESEM-ZNE 0.366; originators' BP 0.541,
SPP 0.350/0.385). Pauli-path delta 1e-3, 1e-4 (lower edge) and MPS chi 64/256/512 (upper edge); bracket interpretation only
if PATCH_PREREG_27CYC.md is supported. Spend guarded by cost_ledger ($10 cap). Token read in-process, never printed."""
import argparse, json, time
import bluequbit
from floquet_any import load, magnetization
from kicked_ising_crosscheck import OUT, load_token
from cost_ledger import ok_to_spend, spent

ap = argparse.ArgumentParser(); ap.add_argument("--file", required=True); ap.add_argument("--tag", required=True)
a = ap.parse_args()
qc, n, cyc = load(a.file)
terms = magnetization(n)
bq = bluequbit.init(load_token())
path = OUT / f"floquet_big_{a.tag}.json"
rows = json.loads(path.read_text()) if path.exists() else [{"file": a.file, "n": n, "cycles": cyc, "obs": "mag"}]
r = rows[0]
plan = [("pau_0.001", "pauli-path", "pauli_path_truncation_threshold", 1e-3, 0.5),
        ("pau_0.0001", "pauli-path", "pauli_path_truncation_threshold", 1e-4, 0.5),
        ("mps_64", "mps.cpu", "mps_bond_dimension", 64, 1.0),
        ("mps_256", "mps.cpu", "mps_bond_dimension", 256, 1.0),
        ("mps_512", "mps.cpu", "mps_bond_dimension", 512, 1.0),
        # mps.cpu is free on the Standard plan (verified: all actual costs $0.00); estimate() shows list price only
        ("mps_1024", "mps.cpu", "mps_bond_dimension", 1024, 0.0),
        ("mps_2048", "mps.cpu", "mps_bond_dimension", 2048, 0.0)]
for name, dev, key, v, est in plan:
    if r.get(name) is not None:
        continue
    if not ok_to_spend(est):
        r[name + "_err"] = f"skipped: $10 cap (spent ${spent():.2f})"; path.write_text(json.dumps(rows, indent=1)); print(name, "SKIPPED cap"); continue
    t0 = time.time()
    try:
        res = bq.run(qc, device=dev, pauli_sum=terms, options={key: v}, **({"force_run": True} if dev.startswith("mps") and v >= 1024 else {}))
        r[name] = float(res.expectation_value); r[name + "_cost"] = getattr(res, "cost", None); r.pop(name + "_err", None)
    except Exception as e:
        r[name] = None; r[name + "_err"] = str(e)[:240]
    r[name + "_s"] = round(time.time() - t0, 1)
    path.write_text(json.dumps(rows, indent=1))
    print(a.tag, name, r.get(name), "cost", r.get(name + "_cost"), r.get(name + "_err", ""), f"| total spent ${spent():.2f}", flush=True)
