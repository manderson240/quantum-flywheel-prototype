"""PREREG_UNDOPED_XEB_LOCAL §C(0) timing probe (small memory): ns per entry-update of the score_undoped_gpu chunk loop,
synthetic message of 2^27 complex64 entries (1 GiB; F_old + F_new = 2 GiB), single-threaded vs a thread pool over chunks.
Projects time per 70q amplitude from the annealed total work 2^33.81. Writes timing_probe.json."""
import json, math, os, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
m = int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]) / 2**20
if m < 24: sys.exit(f"MemAvailable {m:.1f} GiB < 24")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import score_undoped_gpu as S
KB, LOWB = 27, 24
rng = np.random.default_rng(0)
K = [int(x) for x in (1 << np.arange(KB))]; rng.shuffle(K)          # full-rank columns -> idx is a permutation
P = [int(x) for x in rng.integers(0, 2, KB)]
g = int(rng.integers(1, 2**KB))
F = (rng.standard_normal(2**KB) + 1j * rng.standard_normal(2**KB)).astype(np.complex64)
Fn = np.empty_like(F)
idt = np.uint64; low_idx = S._xor_span(K, LOWB, np, idt); low_par = S._xor_span(P, LOWB, np, np.uint8) & np.uint8(1)
h0, h1 = np.complex64(0.6 + 0.1j), np.complex64(-0.3 + 0.7j); step = 1 << LOWB
def chunk(s):
    hi = s >> LOWB
    idx = low_idx ^ idt(S._scalar_xor(K[LOWB:], hi)); par = low_par ^ np.uint8(S._scalar_xor(P[LOWB:], hi) & 1)
    a = F[idx]; b = F[idx ^ idt(g)]; b[par.astype(bool)] *= -1
    Fn[s:s + step] = h0 * a + h1 * b
starts = list(range(0, 2**KB, step)) * 2                               # 16 chunks
res = {}
for nt in (1, 4, 8, 16):
    t0 = time.time()
    if nt == 1: [chunk(s) for s in starts]
    else:
        with ThreadPoolExecutor(nt) as ex: list(ex.map(chunk, starts))
    dt = time.time() - t0; ns = dt / (len(starts) * step) * 1e9
    res[nt] = {"seconds": round(dt, 2), "ns_per_entry": round(ns, 2), "projected_s_per_amplitude": round(2**33.81 * ns * 1e-9, 1)}
    print(nt, res[nt], flush=True)
best = min(res.values(), key=lambda r: r["projected_s_per_amplitude"])
out = {"threads": res, "best_projected_s_per_amplitude": best["projected_s_per_amplitude"], "go_rule_s": 300,
       "GO": best["projected_s_per_amplitude"] <= 300, "load_avg": os.getloadavg(), "note": "synthetic 2^27 message; real 2^31 has worse cache locality"}
Path(__file__).with_name("timing_probe.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
