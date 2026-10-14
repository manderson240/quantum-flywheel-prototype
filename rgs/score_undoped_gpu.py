"""Score IBM's 1,726 published samples of the UNDOPED random-graph-state sampling candidate (tracker #151) with our exact
graph-state / cut-rank method (rgs/stabilizer_overlap.py), on numpy (CPU) or cupy (NVIDIA GPU).

Memory: the message F peaks at 2^31 entries with the annealed qubit order (research/20260924-rgs-stabilizer-method.md),
i.e. 32 GiB in complex128. The update is CHUNKED so peak memory is ~ |F_old| + |F_new| (<= 64 GiB) plus small chunk
buffers: fits one 80 GB H100. Index/parity arrays for a chunk are built from a precomputed low-bit table XOR a scalar.

Usage:
  python score_undoped_gpu.py --validate                          # CPU, small slices vs the reference implementation
  python score_undoped_gpu.py --backend cupy --limit 5           # timing probe on the GPU
  python score_undoped_gpu.py --backend cupy                      # all 1,726 samples (resumable; appends JSONL)
Criterion (#151): linear/log XEB on IBM's samples significantly above 0.092. Results never posted anywhere by this script.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import sys
import time
import zipfile
from pathlib import Path

import numpy as np


HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import stabilizer_overlap as so  # noqa: E402


CIRCUIT = HERE.parent / "tracker/cv/random_graph_sampling_nq70_depth70_checks27_basis_fstate.qasm"
SAMPLES = HERE.parent / "data/rgs/samples_undoped.npy.zip"
ANNEALED = [
    36,
    46,
    37,
    15,
    29,
    49,
    38,
    39,
    34,
    66,
    7,
    28,
    48,
    17,
    65,
    4,
    31,
    52,
    32,
    12,
    9,
    68,
    47,
    51,
    6,
    20,
    61,
    21,
    40,
    0,
    64,
    56,
    3,
    16,
    44,
    1,
    55,
    11,
    60,
    19,
    42,
    8,
    41,
    63,
    67,
    53,
    10,
    59,
    30,
    54,
    22,
    43,
    57,
    25,
    13,
    45,
    14,
    35,
    33,
    50,
    26,
    2,
    23,
    27,
    58,
    18,
    24,
    62,
    69,
    5,
]
CHUNK_BITS = 24


def _xor_span(cols, k, xp, dtype):
    """Array over c in [0, 2^k): XOR of cols[j] for set bits j < k."""
    a = xp.zeros(1, dtype=dtype)
    for col in cols[:k]:
        a = xp.concatenate([a, a ^ dtype(col)])
    return a


def _scalar_xor(cols, c):
    r, j = 0, 0
    while c:
        if c & 1:
            r ^= cols[j]
        c >>= 1
        j += 1
    return r


def contract_chunked(steps, H, xp, cdtype):
    idt = np.uint64
    F = xp.ones(1, dtype=cdtype)
    peak = 1
    for v, K, P, g in steps:
        size = 1 << len(K)
        lowb = min(len(K), CHUNK_BITS)
        low_idx = _xor_span(K, lowb, xp, idt)
        low_par = _xor_span(P, lowb, xp, np.uint8) & np.uint8(1)
        Fn = xp.empty(size, dtype=cdtype)
        h0, h1 = cdtype(H[v, 0]), cdtype(H[v, 1])
        step = 1 << lowb
        for s in range(0, size, step):
            hi = s >> lowb
            idx = low_idx ^ idt(_scalar_xor(K[lowb:], hi))
            par = low_par ^ np.uint8(_scalar_xor(P[lowb:], hi) & 1)
            a = F[idx]
            b = F[idx ^ idt(g)]
            b[par.astype(bool)] *= -1
            Fn[s : s + step] = h0 * a + h1 * b
        F = Fn
        peak = max(peak, size)
    assert F.shape[0] == 1
    return complex(F[0]), peak


def build(qasm: str, order):
    n, ops, V = so.parse(qasm)
    gf = so.graph_form(n, ops)
    steps, ranks = so.plan(gf["G"], list(order))
    return V, gf, steps, ranks


def amplitude(built, bits_q0_first, xp, cdtype):
    V, gf, steps, _ = built
    s, peak = contract_chunked(steps, so.unaries(gf, V, bits_q0_first, None), xp, cdtype)
    return s * 2.0 ** gf["lg"] * so.W8 ** gf["w8"], peak


def validate() -> bool:
    ns = {"__file__": str(HERE / "mini_sweep_validate.py")}
    exec((HERE / "mini_sweep_validate.py").read_text().split("worst = 0.0")[0], ns)
    rng = np.random.default_rng(3)
    worst = 0.0
    global CHUNK_BITS
    for k, ncz in ((9, 33), (12, 70), (14, 120)):
        txt = ns["sliced"](k, ncz)
        for cb in (2, 24):  # exercise both multi-chunk and single-chunk paths
            CHUNK_BITS = cb
            order = list(rng.permutation(k))
            b = build(txt, order)
            for _ in range(6):
                bits = "".join(rng.choice(["0", "1"]) for _ in range(k))
                ref = complex(so.amplitude(txt, bits, order=order)[0])
                got, _ = amplitude(b, bits, np, np.complex128)
                if abs(ref) > 1e-12:
                    worst = max(worst, abs(got - ref) / abs(ref))
    CHUNK_BITS = 24
    print(f"validate: max rel err vs reference implementation = {worst:.2e}")
    return worst < 1e-9


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["numpy", "cupy"], default="numpy")
    ap.add_argument("--dtype", choices=["complex128", "complex64"], default="complex128")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--out", default=str(HERE.parent / "results/rgs_undoped_amplitudes.jsonl"))
    a = ap.parse_args()
    if a.validate:
        return 0 if validate() else 1
    xp = __import__(a.backend)
    cdtype = getattr(np, a.dtype)
    built = build(CIRCUIT.read_text(), ANNEALED)
    print(f"plan: max cut-rank {max(built[3])} (message 2^{max(built[3])})", flush=True)
    z = zipfile.ZipFile(SAMPLES)
    samples = np.load(io.BytesIO(z.read(z.namelist()[0])), allow_pickle=False)
    out = Path(a.out)
    done = {json.loads(l)["i"] for l in out.read_text().splitlines()} if out.exists() else set()
    with out.open("a") as f:
        for i, s in enumerate(samples[: a.limit or len(samples)]):
            if i in done:
                continue
            t0 = time.time()
            amp, peak = amplitude(
                built, str(s)[::-1], xp, cdtype
            )  # Qiskit little-endian -> q0 first
            f.write(
                json.dumps(
                    {
                        "i": i,
                        "bits_qiskit": str(s),
                        "p": abs(amp) ** 2,
                        "peak": peak,
                        "s": round(time.time() - t0, 2),
                        "dtype": a.dtype,
                    }
                )
                + "\n"
            )
            f.flush()
            print(i, f"{abs(amp) ** 2:.3e}", f"{time.time() - t0:.1f}s", flush=True)
    ps = np.array([json.loads(l)["p"] for l in out.read_text().splitlines()])
    n = 70
    lin = 2**n * ps.mean() - 1
    logx = np.euler_gamma + n * math.log(2) + np.log(ps).mean()
    se_lin = 2**n * ps.std(ddof=1) / math.sqrt(len(ps))
    se_log = np.log(ps).std(ddof=1) / math.sqrt(len(ps))
    print(
        json.dumps(
            {
                "n_samples": len(ps),
                "linear_XEB": lin,
                "linear_XEB_se": se_lin,
                "log_XEB": logx,
                "log_XEB_se": se_log,
                "criterion": "rgs/PREREG_UNDOPED_XEB.md section 4",
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
