import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 20') if m < 20*2**20 else None
"""Derived RCS mirror circuits (PREREG.md, sha16 3facc6f83d950e40). --device mps.cpu = free builder/bit-order validation;
--device quantum = approved QPU runs (cap $3, stop rules in PREREG)."""
import argparse, hashlib, json, math, re, sys, time
from pathlib import Path
import numpy as np
HERE = Path(__file__).parent; ROOT = HERE.parents[2]; sys.path.insert(0, str(ROOT))
from qiskit import QuantumCircuit
from qasm_angle import angle
from cost_ledger import ok_to_spend, record_job, record_cost, spent
assert hashlib.sha256((HERE / "PREREG.md").read_bytes()).hexdigest()[:16] == "3facc6f83d950e40"
SRC = ROOT / "refs/rcs-nighthawk-data/data/circuits/mirror/d36_instance0.qasm"
S = np.random.default_rng(20260926).integers(0, 2, 61)

def segments():
    segs = [[]]
    for ln in SRC.read_text().splitlines():
        if ln.startswith("barrier"): segs.append([]); continue
        m = re.match(r"(rx|rz)\((.+)\) q\[(\d+)\];", ln)
        if m:
            if "_theta" in m[2]: continue
            segs[-1].append((m[1], angle(m[2]), int(m[3]))); continue
        m = re.match(r"cz q\[(\d+)\], ?q\[(\d+)\];", ln)
        if m: segs[-1].append(("cz", None, (int(m[1]), int(m[2]))))
    return segs[1:-1]  # body: 73 segments, L0 C1 L1 ... (verified U U^dagger pairing)

def inv(seg):
    return [(g, (-a if g != "cz" else None), q) for g, a, q in reversed(seg)]

def build(depth):
    body = segments(); assert len(body) == 73 and depth % 2 == 0 and 2 <= depth <= 36
    k = depth // 2; fwd = body[:2 * k]; bwd = body[73 - 2 * k:]
    key = lambda seg: sorted((g, None if a is None else round(a, 9), q) for g, a, q in seg)
    assert all(key(inv(f)) == key(b) for f, b in zip(fwd, reversed(bwd))), "segment inverse check failed"
    c = QuantumCircuit(61)
    for i in range(61): c.rx(math.pi * int(S[i]), i)
    for seg in fwd + bwd:
        for g, a, q in seg:
            (c.cz(*q) if g == "cz" else getattr(c, g)(a, q))
    c.measure_all(); return c

def survival(counts):
    target = "".join(str(int(b)) for b in S)  # BlueQubit count keys are qubit-0-first (validated on mps.cpu, DEVIATIONS.md D1)
    hits = sum(v for k, v in counts.items() if k.replace(" ", "") == target); tot = sum(counts.values())
    return hits, tot

def wilson(h, n, z=1.96):
    p = h / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [c - w, c + w]

if __name__ == "__main__":
    import bluequbit
    from kicked_ising_crosscheck import load_token
    ap = argparse.ArgumentParser(); ap.add_argument("--device", required=True); ap.add_argument("--depth", type=int, required=True)
    ap.add_argument("--shots", type=int, default=1000); a = ap.parse_args()
    out = HERE / "results" / f"{a.device}_d{a.depth}.json"
    if out.exists(): sys.exit(f"exists: {out}")
    c = build(a.depth); bq = bluequbit.init(load_token())
    est = bq.estimate(c, device=a.device); est_cost = float(est.estimated_cost or 0)
    wave = sum(json.loads(p.read_text()).get("cost") or 0 for p in (HERE / "results").glob("quantum_d*.json"))
    if a.device == "quantum" and (not ok_to_spend(est_cost) or wave + est_cost > 3.0):
        sys.exit(f"STOP cap: wave ${wave:.2f} + est ${est_cost:.2f}; ledger ${spent():.2f}")
    j = bq.run(c, device=a.device, shots=a.shots, asynchronous=True, **({"options": {"mps_bond_dimension": 256}} if a.device.startswith("mps") else {}))
    record_job(j.job_id, device=a.device, purpose=f"wave6_qpu mirror d{a.depth}", est_cost=est_cost)
    t0 = time.time()
    while True:
        r = bq.get(j.job_id)
        if r.run_status in ("COMPLETED", "FAILED_VALIDATION", "NOT_ENOUGH_FUNDS", "CANCELED", "TERMINATED", "JOBS_LIMIT_EXCEEDED"): break
        if time.time() - t0 > 6 * 3600: print("still running; job id recorded:", j.job_id); sys.exit(0)
        time.sleep(30)
    record_cost(j.job_id, getattr(r, "cost", None), device=a.device)
    rec = {"job_id": j.job_id, "device": a.device, "depth": a.depth, "status": r.run_status, "cost": getattr(r, "cost", None),
           "est_cost": est_cost, "error": r.error_message, "device_options": str(r.device_options), "run_results": str(r.run_results)[:500],
           "cz": c.count_ops().get("cz"), "input_bits_q0_first": "".join(map(str, S))}
    if r.run_status == "COMPLETED":
        counts = r.get_counts(); h, n = survival(counts)
        rec.update(hits=h, shots=n, survival=h / n, wilson95=wilson(h, n), distinct_outcomes=len(counts))
    out.write_text(json.dumps(rec, indent=1)); print(json.dumps({k: rec[k] for k in rec if k != "run_results"})[:700])
