"""Run 1 (PATCH_PREREG_27CYC.md): exact truths first ($0 per BlueQubit estimate); Pauli-path / MPS only with --approx
(awaiting approval of possible charges). Results: results/floquet_patch{n}_27cyc.json. Token read in-process."""
import argparse, json, time
import bluequbit
from floquet_patch_oracle import patch, build, observables
from kicked_ising_crosscheck import OUT, load_token

ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, required=True); ap.add_argument("--approx", action="store_true")
a = ap.parse_args()
bq = bluequbit.init(load_token())
keep, layers = patch(a.n); n = len(keep); obs = observables(n, layers)
path = OUT / f"floquet_patch{n}_27cyc.json"
rows = json.loads(path.read_text()) if path.exists() else []
byk = {(r["cycles"], r["obs"]): r for r in rows}
jobs = [("exact", "cpu", None, None)]
if a.approx:
    jobs += [("pau_0.001", "pauli-path", "pauli_path_truncation_threshold", 1e-3), ("pau_0.0001", "pauli-path", "pauli_path_truncation_threshold", 1e-4),
             ("mps_64", "mps.cpu", "mps_bond_dimension", 64), ("mps_256", "mps.cpu", "mps_bond_dimension", 256)]
for cyc in (20, 27):
    qc = build(n, layers, cyc)
    for ob, terms in obs.items():
        r = byk.setdefault((cyc, ob), {"n": n, "cycles": cyc, "obs": ob, "n_terms": len(terms)})
        if r not in rows: rows.append(r)
        for name, dev, key, v in jobs:
            if r.get(name) is not None:
                continue
            for attempt in (1, 2, 3):  # first run + at most 2 retries (pre-registered)
                t0 = time.time()
                try:
                    res = bq.run(qc, device=dev, pauli_sum=terms, **({"options": {key: v}} if key else {}))
                    r[name] = float(res.expectation_value); r[name + "_cost"] = getattr(res, "cost", None); r.pop(name + "_err", None)
                    break
                except Exception as e:
                    r[name] = None; r[name + "_err"] = f"attempt {attempt}: " + str(e)[:200]
                finally:
                    r[name + "_s"] = round(time.time() - t0, 1)
            path.write_text(json.dumps(rows, indent=1))
            print(cyc, ob, name, r.get(name), r.get(name + "_cost"), r.get(name + "_err", ""), flush=True)
