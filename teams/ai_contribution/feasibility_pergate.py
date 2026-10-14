"""Step 1 feasibility: does quimb 1.13 CircuitMPS honour PER-GATE truncation overrides (max_bond, cutoff,
cutoff_mode) passed to apply_gate_raw, including on the swap path for non-adjacent gates? And would a
silently-ignored setting be detected? 12 qubits, all exact-checkable. Run: nice -n 10 python3 feasibility_pergate.py
"""
import json, math, sys
from pathlib import Path
import numpy as np
import quimb, quimb.tensor as qtn

N = 12
rng = np.random.default_rng(1)
def rx(t): return np.array([[math.cos(t/2), -1j*math.sin(t/2)], [-1j*math.sin(t/2), math.cos(t/2)]])
def rz(t): return np.diag([np.exp(-1j*t/2), np.exp(1j*t/2)])
def rzz(t): return np.diag([np.exp(-1j*t/2), np.exp(1j*t/2), np.exp(1j*t/2), np.exp(-1j*t/2)])
# nearest-neighbour + some non-adjacent (distance 3) edges -> exercises swap+split
EDGES = [(i, i+1) for i in range(N-1)] + [(i, i+3) for i in range(0, N-3, 2)]

def run(per_gate=None, default=None, layers=6):
    """per_gate: dict of opts applied to EVERY 2q gate call, or a callable(layer)->dict. default: ctor opts."""
    c = qtn.CircuitMPS(N, **(default or {}))
    maxb = []
    for l in range(layers):
        for q in range(N):
            c.apply_gate_raw(rx(1.1), [q]); c.apply_gate_raw(rz(0.37), [q])
        opts = per_gate(l) if callable(per_gate) else (per_gate or {})
        for a, b in EDGES:
            c.apply_gate_raw(rzz(math.pi/3), [a, b], **opts)
        maxb.append(int(c.psi.max_bond()))
    v = c.psi.to_dense().ravel()
    v = v / np.linalg.norm(v)
    return v, maxb

out = {"quimb": quimb.__version__, "python": sys.version.split()[0], "N": N, "edges": EDGES}
v_ex, mb_ex = run(default=dict(max_bond=None, cutoff=0.0))
# independent dense check of the exact engine
psi = np.zeros(2**N, complex); psi[0] = 1
def app1(psi, U, q):
    t = psi.reshape([2]*N); t = np.moveaxis(np.tensordot(U, t, axes=([1], [q])), 0, q); return t.ravel()
def app2(psi, U, a, b):
    t = psi.reshape([2]*N); U4 = U.reshape(2, 2, 2, 2)
    t = np.tensordot(U4, t, axes=([2, 3], [a, b])); t = np.moveaxis(t, [0, 1], [a, b]); return t.ravel()
for l in range(6):
    for q in range(N): psi = app1(psi, rx(1.1), q); psi = app1(psi, rz(0.37), q)
    for a, b in EDGES: psi = app2(psi, rzz(math.pi/3), a, b)
out["exact_engine_vs_dense_fidelity"] = float(abs(np.vdot(psi, v_ex))**2)
out["exact_maxbond_per_layer"] = mb_ex

def fid(v): return float(abs(np.vdot(v_ex, v))**2)
# A: default ctor max_bond=32, per-gate override max_bond=4
vA0, mbA0 = run(default=dict(max_bond=32))
vA1, mbA1 = run(default=dict(max_bond=32), per_gate=dict(max_bond=4))
out["A_ctor32_maxbond"] = mbA0; out["A_ctor32_fid"] = fid(vA0)
out["A_override4_maxbond"] = mbA1; out["A_override4_fid"] = fid(vA1)
# B: per-gate cutoff override (rsum2 discarded weight) with no max_bond
vB0, mbB0 = run(default=dict(max_bond=None, cutoff=1e-10))
vB1, mbB1 = run(default=dict(max_bond=None, cutoff=1e-10), per_gate=dict(cutoff=1e-2, cutoff_mode="rsum2"))
out["B_default_maxbond"] = mbB0; out["B_cut1e-2_maxbond"] = mbB1; out["B_cut1e-2_fid"] = fid(vB1)
# C: a per-LAYER schedule (chi grows 2->64 by layer)
sched = [2, 4, 8, 16, 32, 64]
vC, mbC = run(default=dict(max_bond=64), per_gate=lambda l: dict(max_bond=sched[l]))
out["C_schedule"] = sched; out["C_maxbond"] = mbC; out["C_fid"] = fid(vC)
# D: silent-ignore detector — a misspelled key. Does quimb raise, or silently ignore?
try:
    vD, mbD = run(default=dict(max_bond=32), per_gate=dict(maxbond=4))
    out["D_misspelled_key"] = {"raised": False, "maxbond": mbD, "fid": fid(vD),
                               "detected_by_bond_assert": any(m > 4 for m in mbD)}
except TypeError as e:
    out["D_misspelled_key"] = {"raised": True, "error": str(e)[:200]}

checks = {
    "exact_engine_matches_dense": out["exact_engine_vs_dense_fidelity"] > 1 - 1e-10,
    "override_max_bond_honoured": max(mbA1) <= 4 and max(mbA0) > 4,
    "override_changes_result": abs(out["A_override4_fid"] - out["A_ctor32_fid"]) > 1e-3,
    "override_cutoff_honoured": max(mbB1) < max(mbB0),
    "per_layer_schedule_honoured": all(m <= s for m, s in zip(mbC, sched)) and mbC[0] <= 2,
}
out["checks"] = checks
out["all_pass"] = all(checks.values())
p = Path(__file__).parent / "results" / "feasibility_pergate.json"
p.write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
sys.exit(0 if out["all_pass"] else 1)
