"""Retry ONLY the exact (device=cpu) values that BlueQubit terminated server-side in floquet_patch<n>.json.
Same circuits, same observables; no parameter changes (allowed by PATCH_PREREG.md: infrastructure retry, max 2 attempts)."""
import json, sys, time
import bluequbit
from floquet_patch_oracle import patch, build, observables
from kicked_ising_crosscheck import OUT, load_token

n = int(sys.argv[1])
path = OUT / f"floquet_patch{n}.json"
rows = json.loads(path.read_text())
keep, layers = patch(n)
obs = observables(len(keep), layers)
bq = bluequbit.init(load_token())
for r in rows:
    if r.get("exact") is not None:
        continue
    for attempt in (1, 2):
        t0 = time.time()
        try:
            res = bq.run(build(len(keep), layers, r["cycles"]), device="cpu", pauli_sum=obs[r["obs"]])
            r["exact"] = float(res.expectation_value); r["exact_retry"] = attempt; r.pop("exact_err", None)
            break
        except Exception as e:
            r["exact_err"] = f"attempt {attempt}: " + str(e)[:200]
        finally:
            r["exact_s"] = round(time.time() - t0, 1)
    path.write_text(json.dumps(rows, indent=1))
    print(r["cycles"], r["obs"], "exact", r.get("exact"), r.get("exact_err", ""), flush=True)
