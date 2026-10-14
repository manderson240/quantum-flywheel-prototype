"""PREREG_UNDOPED_XEB_LOCAL (frozen 3e7bf7dd9a22d2d6): local complex64 scoring of a seeded random subset of IBM's 1,726
undoped-RGS samples. Same per-entry arithmetic as score_undoped_gpu.contract_chunked; chunks run on a thread pool.
Step P2: first subset sample in the annealed AND greedy orders (must agree <= 1e-4 rel). Then score subset in seed order
(annealed order), resumable, until the frozen cutoff 2026-10-12T04:00Z. Memory guard: >= 52 GiB at start, abort < 16 GiB."""
import datetime as dt, io, json, sys, time, zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE.parent))
import score_undoped_gpu as S, stabilizer_overlap as so
THREADS = 4; CUTOFF = dt.datetime(2026, 10, 12, 4, 0, tzinfo=dt.timezone.utc)
def mem_gib(): return int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]) / 2**20
if mem_gib() < 52: sys.exit(f"MemAvailable {mem_gib():.1f} GiB < 52: not starting")
POOL = ThreadPoolExecutor(THREADS)
def contract_threaded(steps, H, xp, cdtype):
    idt = np.uint64; F = np.ones(1, dtype=cdtype); peak = 1
    for v, K, P, g in steps:
        size = 1 << len(K); lowb = min(len(K), S.CHUNK_BITS)
        low_idx = S._xor_span(K, lowb, np, idt); low_par = S._xor_span(P, lowb, np, np.uint8) & np.uint8(1)
        Fn = np.empty(size, dtype=cdtype); h0, h1 = cdtype(H[v, 0]), cdtype(H[v, 1]); step = 1 << lowb
        def chunk(s, F=F, Fn=Fn, K=K, P=P, g=g, low_idx=low_idx, low_par=low_par, lowb=lowb, h0=h0, h1=h1, step=step):
            hi = s >> lowb
            idx = low_idx ^ idt(S._scalar_xor(K[lowb:], hi)); par = low_par ^ np.uint8(S._scalar_xor(P[lowb:], hi) & 1)
            a = F[idx]; b = F[idx ^ idt(g)]; b[par.astype(bool)] *= -1
            Fn[s:s + step] = h0 * a + h1 * b
        list(POOL.map(chunk, range(0, size, step)))
        if mem_gib() < 16: sys.exit(f"MemAvailable {mem_gib():.1f} GiB < 16: aborting (guard)")
        F = Fn; peak = max(peak, size)
    assert F.shape[0] == 1
    return complex(F[0]), peak
S.contract_chunked = contract_threaded
def amp(built, s): a, peak = S.amplitude(built, str(s)[::-1], np, np.complex64); return a, peak
z = zipfile.ZipFile(S.SAMPLES); samples = np.load(io.BytesIO(z.read(z.namelist()[0])), allow_pickle=False)
assert len(samples) == 1726
perm = np.random.default_rng(20261009).permutation(1726)
qasm = S.CIRCUIT.read_text()
ann = S.build(qasm, S.ANNEALED)
p2 = HERE / "P2.json"
if not p2.exists():
    greedy = json.load(open(HERE / "greedy_order.json"))["order"]
    i0 = int(perm[0]); t0 = time.time(); a1, pk1 = amp(ann, samples[i0]); t1 = time.time() - t0
    gb = S.build(qasm, greedy); t0 = time.time(); a2, pk2 = amp(gb, samples[i0]); t2 = time.time() - t0; del gb
    rel = abs(a1 - a2) / max(abs(a1), 1e-300)
    rec = {"sample_index": i0, "annealed": [a1.real, a1.imag], "greedy": [a2.real, a2.imag], "rel_diff": rel,
           "p_annealed": abs(a1) ** 2, "pass": bool(rel <= 1e-4), "s_annealed": round(t1, 1), "s_greedy": round(t2, 1),
           "peaks": [pk1, pk2], "threads": THREADS, "utc": dt.datetime.now(dt.timezone.utc).isoformat()}
    p2.write_text(json.dumps(rec, indent=1)); print("P2", rec, flush=True)
    if not rec["pass"]: sys.exit("P2 FAILED: abandon per PREREG_LOCAL §C(a)")
if "--p2-only" in sys.argv: sys.exit(0)
out = HERE / "subset_amplitudes.jsonl"
done = {json.loads(l)["rank"] for l in out.read_text().splitlines()} if out.exists() else set()
with out.open("a") as f:
    for r, i in enumerate(perm):
        if dt.datetime.now(dt.timezone.utc) >= CUTOFF: print("cutoff reached", flush=True); break
        if r in done: continue
        t0 = time.time(); a, pk = amp(ann, samples[int(i)])
        f.write(json.dumps({"rank": r, "i": int(i), "bits_qiskit": str(samples[int(i)]), "p": abs(a) ** 2, "peak": pk,
                            "s": round(time.time() - t0, 1), "dtype": "complex64", "utc": dt.datetime.now(dt.timezone.utc).isoformat()}) + "\n"); f.flush()
        print(r, int(i), f"{abs(a)**2:.3e}", f"{time.time()-t0:.0f}s", flush=True)
