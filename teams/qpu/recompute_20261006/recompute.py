"""Independent recompute of wave 8 / 8b from raw counts. Does NOT import wave8.py, wave8b.py, check_claims.py.
Only floquet_oracle19.{lattice, three_colour, circuit} are imported (builders). No network, no jobs."""
import json, math, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
W8, W8B = ROOT / "teams/qpu/wave8/results", ROOT / "teams/qpu/wave8b/results"

def load(p): return json.loads(p.read_text())

def bits_matrix(counts, order="q0first"):
    rows, w = [], []
    for k, v in counts.items():
        b = [int(c) for c in k]
        if order == "q0last": b = b[::-1]
        rows.append(b); w.append(v)
    return np.array(rows), np.array(w)

def expand(counts, order="q0first"):
    B, w = bits_matrix(counts, order)
    return np.repeat(B, w, axis=0)

def M_SE(counts):
    S = expand(counts); Z = 1 - 2 * S
    per = Z.mean(axis=1)
    return per.mean(), per.std() / math.sqrt(len(per)), per.std(ddof=1) / math.sqrt(len(per))

def retention(counts, s, order="q0first"):
    S = expand(counts, order)
    p_err = (S != s[None, :]).mean(axis=0)
    return float(np.mean(1 - 2 * p_err)), int((S == s[None, :]).all(axis=1).sum())

out = {}
n = 19
s = np.random.default_rng(20261005).integers(0, 2, 19)
out["s"] = "".join(map(str, s))

# Exact values
from floquet_oracle19 import lattice, three_colour, circuit
from qiskit.quantum_info import Statevector
nn, edges = lattice(); assert nn == n
layers = three_colour(edges, 0)
exact = {}
for c in (1, 2, 3, 4):
    p = Statevector(circuit(n, layers, c)).probabilities()
    idx = np.arange(p.size)
    # qiskit little-endian: bit q of index = qubit q
    mz = sum(float(np.sum(p * (1 - 2 * ((idx >> q) & 1)))) for q in range(n)) / n
    exact[c] = mz
oracle = {r["cycles"]: r["exact"] for r in load(ROOT / "results/floquet_oracle19.json") if r["obs"] == "mag"}
out["exact"] = exact
out["exact_vs_oracle_maxdiff"] = max(abs(exact[c] - oracle[c]) for c in exact)

J = {i: load(W8 / f"J{i}.json") for i in range(10)}
K = {i: load(W8B / f"K{i}.json") for i in range(1, 5)}

# J0 readout
S0 = expand(J[0]["counts"])
rho_q = 1 - 2 * (S0 == 0).mean(axis=0)
out["rho"] = float(rho_q.mean()); out["rho_q_std_over_q"] = float(rho_q.std(ddof=1))
out["rho_se_binom"] = math.sqrt(1 - out["rho"] ** 2) / math.sqrt(19000)
out["allones"] = int(J[0]["counts"].get("1" * n, 0))

# Floquet
out["M"] = {}
for c in (1, 2, 3, 4):
    m, se, se1 = M_SE(J[c]["counts"]); out["M"][c] = (m, se, se1)

# Orientation test using mirrors: q0first vs q0last
out["orient"] = {}
for c in (1, 2, 3, 4):
    out["orient"][c] = {o: retention(J[4 + c]["counts"], s, o) for o in ("q0first", "q0last")}

def binse(r): return math.sqrt(max(0.0, 1 - r * r)) / math.sqrt(19000)
out["r8"] = {c: retention(J[4 + c]["counts"], s) for c in (1, 2, 3, 4)}
out["r8b"] = {c: retention(K[c]["counts"], s) for c in (1, 2, 3, 4)}
out["distinct"] = {f"J{i}": len(J[i]["counts"]) for i in J} | {f"K{i}": len(K[i]["counts"]) for i in K}
out["J9_eq_J1"] = J[9]["counts"] == J[1]["counts"]
out["J9_vs_J1_tvd"] = 0.5 * sum(abs(J[9]["counts"].get(k, 0) - J[1]["counts"].get(k, 0)) for k in set(J[1]["counts"]) | set(J[9]["counts"])) / 1000
m9 = M_SE(J[9]["counts"]); out["M_J9"] = m9

# Hypothesis rule
z = {}
for c in (1, 2, 3, 4):
    rb, r = out["r8b"][c][0], out["r8"][c][0]
    z[c] = (rb - r) / math.sqrt(binse(rb) ** 2 + binse(r) ** 2)
r1b, r4b = out["r8b"][1][0], out["r8b"][4][0]
z41 = (r4b - r1b) / math.sqrt(binse(r4b) ** 2 + binse(r1b) ** 2)
if z[3] < -3 and z[4] < -3 and z41 < -3: verdict = "SUPPORTED"
elif all(abs(z[c]) <= 3 for c in z): verdict = "NOT SUPPORTED"
else: verdict = "MIXED"
out["H_z"] = z; out["H_z41"] = z41; out["H"] = verdict

# Recalibration agreement
def agree(rmap):
    res = {}
    rho, serho = out["rho"], out["rho_se_binom"]
    for c in (1, 2, 3, 4):
        r = rmap[c][0]; ser = binse(r); E = exact[c]
        prod = max(r * rho, 0.0)
        mp = E * math.sqrt(prod)
        if prod > 0:
            sep = math.sqrt((mp / (2 * r) * ser) ** 2 + (mp / (2 * rho) * serho) ** 2)
        else:
            sep = 0.0
        m, se, _ = out["M"][c]
        zz = (m - mp) / math.sqrt(se ** 2 + sep ** 2)
        res[c] = (mp, sep, zz, abs(zz) <= 3)
    return res
out["agree8"] = agree(out["r8"]); out["agree8b"] = agree(out["r8b"])

# Cost / dates
out["jobs"] = [(d["job"], d.get("status"), d.get("cost"), (d.get("run_start") or "")[:10]) for d in list(J.values()) + list(K.values())]

def conv(o):
    if isinstance(o, dict): return {str(k): conv(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [conv(v) for v in o]
    if isinstance(o, (np.floating, np.integer, np.bool_)): return o.item()
    return o
(Path(__file__).parent / "recompute.json").write_text(json.dumps(conv(out), indent=1))
print(json.dumps(conv(out), indent=1))
