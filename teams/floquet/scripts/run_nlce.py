"""Run the pre-registered NLCE (PREREG.md sha16 8cc7cc4f71c11fdc): K=16 on patch(27), patch(33); baseline patch(16)."""
import os
for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[v] = "1"
import json, pickle, sys, time
from multiprocessing import Pool
import numpy as np
sys.path.insert(0, "/home/mike-anderson/cohezion-labs/bluequbit-flywheel/teams/floquet/scripts")
import nlce

K = 16
OUTD = "/home/mike-anderson/cohezion-labs/bluequbit-flywheel/teams/floquet/results"
L51 = nlce.lattice51()

def mem_ok():
    kb = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1])
    return kb > 20 * 1024 * 1024

def work(c):
    for attempt in (0, 1):
        try:
            z = nlce.simulate(c, L51)
            if np.all(np.isfinite(z)): return c, z.sum(axis=1), attempt
        except Exception:
            pass
    return c, None, 2

def main():
    clusters = set()
    per = {}
    for n in (27, 33):
        nodes = nlce.patch_nodes(n)
        adj = nlce.adjacency(nodes, nlce.induced(nodes, L51))
        cs = nlce.esu(nodes, adj, K)
        per[n] = (nodes, cs)
        clusters |= set(cs)
    todo = sorted(clusters, key=len, reverse=True)
    print("clusters", len(todo), flush=True)
    P, failed, retried = {}, [], 0
    t0 = time.time()
    with Pool(4) as pool:
        for i, (c, p, att) in enumerate(pool.imap_unordered(work, todo, chunksize=8)):
            if p is None: failed.append(sorted(c))
            else: P[c] = p; retried += att
            if i % 2000 == 0:
                back = 60
                while not mem_ok():
                    print("MemAvailable < 20 GiB, pausing", back, flush=True); time.sleep(back); back = min(back * 2, 1800)
                print(i, round(time.time() - t0), flush=True)
    base = nlce.simulate(nlce.patch_nodes(16), L51).mean(axis=1)
    out = {"K": K, "failed": failed, "retried": retried, "baseline_patch16_mag": base.tolist(), "orders": {}}
    for n, (nodes, cs) in per.items():
        kmax = K
        if failed: kmax = min(len(f) for f in failed) - 1
        S, _ = nlce.nlce_orders(nodes, {c: P[c] for c in cs if len(c) <= kmax}, kmax)
        out["orders"][n] = {"kmax": kmax, "n_clusters": len(cs), "S_over_n": (S / n).tolist()}
    json.dump(out, open(f"{OUTD}/nlce_run.json", "w"))
    print("done", round(time.time() - t0), "failed", len(failed), flush=True)

if __name__ == "__main__":
    main()
