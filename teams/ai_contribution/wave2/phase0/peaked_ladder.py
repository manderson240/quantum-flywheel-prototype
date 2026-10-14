import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 20') if m < 20*2**20 else None
"""Free API fetch of BlueQubit peaked circuits by difficulty. Peak keys go ONLY to SEALED/ (never printed, never shown to agents)."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]; sys.path.insert(0, str(ROOT))
import bluequbit
from kicked_ising_crosscheck import load_token
HERE = Path(__file__).parent; SEAL = HERE.parent / "SEALED"; CIRC = HERE / "circuits"; CIRC.mkdir(exist_ok=True)
bq = bluequbit.init(load_token()); ladder, keys = [], {}
for d in range(1, 41):
    try:
        pc = bq.get_peaked_circuit(d)
    except Exception as ex:
        ladder.append({"difficulty": d, "err": str(ex)[:200]}); print(d, "ERR", str(ex)[:120]); 
        if len(ladder) >= 3 and all("err" in x for x in ladder[-3:]): break
        continue
    c = pc.circuit; ops = c.count_ops()
    two_q = sum(v for k, v in ops.items() if k in ("cx", "cz", "ecr", "rzz", "swap", "iswap", "cp", "crz", "rxx", "ryy", "u2q", "unitary"))
    tag = f"d{d:02d}"; (CIRC / f"{tag}.qasm").write_text(pc.qasm_str); keys[tag] = pc.key
    row = {"difficulty": d, "tag": tag, "num_qubits": c.num_qubits, "depth": c.depth(), "ops": dict(ops), "two_qubit": two_q,
           "metadata": pc.metadata[:200], "key_len": len(pc.key)}
    ladder.append(row); print(d, c.num_qubits, "q, depth", c.depth(), "2q", two_q, "|", pc.metadata[:80], flush=True)
(HERE / "ladder.json").write_text(json.dumps(ladder, indent=1)); (SEAL / "keys.json").write_text(json.dumps(keys))
