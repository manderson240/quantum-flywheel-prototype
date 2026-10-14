import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 20') if m < 20*2**20 else None
"""rcs wave 7 driver (PREREG.md §4-§6). Runs cells ONE AT A TIME, each in a fresh child process (cell.py).
Resumable: state in results/state.json, one JSON per finished cell in results/cells/. Refuses to run on a hash
mismatch of PREREG.md or any frozen script. Exits (for the supervisor to relaunch) whenever MemAvailable < 20 GiB
before a cell. When every cell is terminal or the deadline has passed, runs analyze.py and writes RUN_COMPLETE."""
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
import subprocess
import time

import common as C
import orderings as O


HERE = C.HERE
RES = HERE / "results"
CELLS = RES / "cells"
CELLS.mkdir(parents=True, exist_ok=True)
PY = "/home/mike-anderson/dev/cohezion/.venv/bin/python"
STATE = RES / "state.json"
LOG = RES / "runner.log"
DEADLINE = dt.datetime.fromisoformat(C.DEADLINE_ISO).timestamp()
FROZEN = [
    "PREREG.md",
    "common.py",
    "orderings.py",
    "own_mps.py",
    "variant_mps.py",
    "cell.py",
    "runner.py",
    "analyze.py",
    "supervise.sh",
]


def log(*a):
    with open(LOG, "a") as f:
        print(dt.datetime.now().strftime("%m-%d %H:%M:%S"), *a, file=f, flush=True)


def check_hashes():
    h = hashlib.sha256((HERE / "PREREG.md").read_bytes()).hexdigest()[:16]
    assert h == (HERE / "PREREG.sha16").read_text().strip(), "PREREG hash mismatch"
    frozen = dict(
        l.split()[::-1]
        for l in (RES / "scripts_at_freeze.sha256").read_text().splitlines()
        if l.strip()
    )
    for f in FROZEN:
        got = hashlib.sha256((HERE / f).read_bytes()).hexdigest()
        assert frozen.get(f) == got, f"frozen script changed: {f}"


def load():
    return (
        json.loads(STATE.read_text())
        if STATE.exists()
        else {"cells": {}, "threads": C.THREADS_DEFAULT}
    )


def save(st):
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1))
    tmp.replace(STATE)


def result(cid):
    f = CELLS / f"{cid}.json"
    return json.loads(f.read_text()) if f.exists() else None


def mem_ok():
    return (
        int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1])
        >= 20 * 2**20
    )


def run(st, cid, spec, predicted=None):
    """Run one cell to a terminal status unless it is already terminal. Returns the status string."""
    c = st["cells"].setdefault(cid, {"status": "pending", "attempts": 0})
    if c["status"] != "pending":
        return c["status"]
    left = DEADLINE - time.time()
    if left <= 0:
        c["status"] = "NOTRUN_deadline"
        save(st)
        log("NOTRUN", cid, "deadline")
        return c["status"]
    if predicted is not None and predicted > left:
        c.update(status="NOTRUN_predicted", predicted_s=predicted, left_s=left)
        save(st)
        log("NOTRUN", cid, f"predicted {predicted:.0f}s > left {left:.0f}s")
        return c["status"]
    if not mem_ok():
        log("WAIT mem before", cid)
        sys.exit(0)  # supervisor relaunches when MemAvailable >= 20 GiB
    env = dict(
        os.environ,
        **{
            k: str(st["threads"])
            for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
        },
    )
    out = CELLS / f"{cid}.json"
    log("START", cid, json.dumps(spec), f"pred={predicted}")
    c["started"] = time.time()
    save(st)
    try:
        p = subprocess.run(
            ["nice", "-n", "10", PY, str(HERE / "cell.py"), json.dumps(spec), str(out)],
            env=env,
            capture_output=True,
            text=True,
            timeout=max(1.0, left),
        )
    except subprocess.TimeoutExpired:
        c["status"] = "NOTRUN_deadline_killed"
        save(st)
        log("NOTRUN", cid, "killed at deadline")
        return c["status"]
    err = (p.stdout + p.stderr)[-2000:]
    if p.returncode == 0 and out.exists():
        c["status"] = "done"
        save(st)
        r = result(cid)
        log(
            "DONE",
            cid,
            {k: r.get(k) for k in ("survival", "max_abs_amp_err", "wall_s", "peak_rss_mb")},
        )
        return "done"
    if p.returncode == 4:
        c["status"] = "NOTRUN_rss"
        c["err"] = err
        save(st)
        log("NOTRUN", cid, "RSS cap")
        return c["status"]
    if p.returncode == 3 or "MemAvailable" in err:
        log("WAIT mem during", cid, err.strip()[-200:])
        save(st)
        sys.exit(0)  # not an attempt
    c["attempts"] += 1
    c["err"] = err
    if c["attempts"] >= 2:
        c["status"] = "FAILED"
        save(st)
        log("FAILED", cid, err[-300:])
        return c["status"]
    save(st)
    log("RETRY", cid, err[-300:])
    return run(st, cid, spec, predicted)


def mirror(v, inst, d, chi):
    return {"kind": "mirror", "variant": v, "inst": inst, "d": d, "chi": chi}


def hid(v, chi, d, i):
    return f"H_{v}_c{chi}_d{d}_i{i}"


def walls(st, chi, d):
    return [
        result(k)["wall_s"]
        for k, c in st["cells"].items()
        if c["status"] == "done" and k.startswith("H_") and f"_c{chi}_d{d}_" in k
    ]


NCZ = {}


def ncz(d):
    if d not in NCZ:
        from mirror_lib import derived_ops, n_cz

        NCZ[d] = n_cz(derived_ops(0, d))
    return NCZ[d]


def predict(st, chi, d):
    """PREREG §5 runtime prediction, most specific evidence first."""
    w = walls(st, chi, d)
    if w:
        return sum(w) / len(w)
    w = walls(st, chi // 2, d)
    if w:
        return 8 * sum(w) / len(w)
    for d2 in (36, 28):
        w = walls(st, chi, d2)
        if w:
            return sum(w) / len(w) * ncz(d) / ncz(d2)
    for d2 in (36, 28):
        w = walls(st, chi // 2, d2)
        if w:
            return 8 * sum(w) / len(w) * ncz(d) / ncz(d2)
    return None


def mean_surv(st, v, chi, d):
    s = [result(hid(v, chi, d, i)) for i in range(3)]
    return None if any(r is None for r in s) else sum(r["survival"] for r in s) / 3


def rank(st, variants, chi, d):
    """Variants ordered by 3-instance mean survival at (chi, d), best first; incomplete ones last, frozen order."""
    key = {v: mean_surv(st, v, chi, d) for v in variants}
    return sorted(variants, key=lambda v: (key[v] is None, -(key[v] or 0), variants.index(v)))


def controls(st):
    ok = True
    for v in O.CANDIDATES:  # C3: every candidate, exact 16q forward amplitudes
        run(st, f"C3_{v}", {"kind": "fwd16", "variant": v})
        r = result(f"C3_{v}")
        ok &= bool(r and r["max_abs_amp_err"] < C.C3_TOL_ABS)
    for v in O.CANDIDATES:  # M: mutation arms must go red
        for mut in (["g1raw"] if v != "LOG_SB" else []) + (["book"] if v.endswith("_NSB") else []):
            run(st, f"M_{mut}_{v}", {"kind": "fwd16", "variant": v, "mutate": mut})
            r = result(f"M_{mut}_{v}")
            ok &= bool(r and r["max_abs_amp_err"] > C.M_MIN_ERR)
    st["C3M_pass"] = ok
    save(st)
    if not ok:
        (RES / "STOP_CONTROL").write_text("C3 or M failed")
        log("STOP C3/M")
        return False
    w6 = C.ROOT / "teams/rcs/wave6/results"
    ref2 = json.loads((w6 / "posthoc_routing61.json").read_text())
    for tag in ["", "_t4"]:
        if tag == "_t4":
            if st.get("C12_pass"):
                break
            st["threads"] = 4
            save(st)
            log("C1/C2 failed at", C.THREADS_DEFAULT, "threads; rerun at 4")
        good = True
        for i in range(3):
            run(st, f"C1{tag}_i{i}", mirror("LOG_SB", i, 36, 128))
            ref = json.loads((w6 / f"local/L_chi128_i{i}_d36.json").read_text())["survival"]
            r = result(f"C1{tag}_i{i}")
            good &= bool(r and abs(r["survival"] / ref - 1) < C.C_TOL_REL)
            run(st, f"C2{tag}_i{i}", mirror("LOG_NSB", i, 36, 128))
            ref = ref2[f"chi128_i{i}"]["survival_no_swap_back_perm"]
            r = result(f"C2{tag}_i{i}")
            good &= bool(r and abs(r["survival"] / ref - 1) < C.C_TOL_REL)
        st["C12_pass"] = good
        st["C12_threads"] = st["threads"]
        save(st)
    if not st["C12_pass"]:
        (RES / "STOP_CONTROL").write_text("C1/C2 failed at both thread counts")
        log("STOP C1/C2")
        return False
    return True


def main():
    check_hashes()
    lockf = open(RES / "runner.lock", "w")
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("another runner holds the lock; exiting")
        return
    st = load()
    log("runner start, threads", st["threads"])
    for i in range(3):  # C0: wave-7 inputs are wave 6's analysis inputs
        w6 = C.ROOT / f"teams/rcs/wave6/results/local/L_chi128_i{i}_d36.json"
        assert json.loads(w6.read_text())["bits"] == C.INPUTS[i][0], "C0: inputs differ from wave 6"
    if (RES / "STOP_CONTROL").exists():
        log("STOP_CONTROL present")
        finish(st)
        return
    if not controls(st):
        finish(st)
        return
    # ---- calibration pilot (§4.2): chi=64, d16/d20, all 12 candidates, NOT used in the headline ----
    for v in O.CANDIDATES:
        for i in range(3):
            for d in C.PILOT_DEPTHS:
                run(st, f"P_{v}_d{d}_i{i}", mirror(v, i, d, C.PILOT_CHI))
    if "selected" not in st:
        score = {}
        for v in O.CANDIDATES:
            rs = [result(f"P_{v}_d{d}_i{i}") for i in range(3) for d in C.PILOT_DEPTHS]
            score[v] = (
                sum(math.log10(max(r["survival"], 1e-300)) for r in rs) / len(rs)
                if all(rs)
                else None
            )
        others = [v for v in O.CANDIDATES if v != "LOG_SB" and score[v] is not None]
        others.sort(key=lambda v: (-score[v], O.CANDIDATES.index(v)))
        st["pilot_score"] = score
        st["selected"] = ["LOG_SB"] + others[: C.N_SELECT - 1]
        save(st)
        log("SELECTED", st["selected"])
    sel = st["selected"]
    # ---- headline ladder (§4.3), frozen order ----
    for chi in (128, 256):
        for v in sel:
            for i in range(3):
                run(st, hid(v, chi, 36, i), mirror(v, i, 36, chi), predict(st, chi, 36))
    for v in rank(st, sel, 256, 36):
        for i in range(3):
            run(st, hid(v, 512, 36, i), mirror(v, i, 36, 512), predict(st, 512, 36))
    for chi in (128, 256):
        for v in sel:
            for i in range(3):
                run(st, hid(v, chi, 28, i), mirror(v, i, 28, chi), predict(st, chi, 28))
    for v in rank(st, sel, 256, 28):
        for i in range(3):
            run(st, hid(v, 512, 28, i), mirror(v, i, 28, 512), predict(st, 512, 28))
    chi1024(st, sel)
    finish(st)


def chi1024(st, sel):
    """§4.4: chi=1024 for the single best variant at d36, only if RSS and runtime predictions allow."""
    if "c1024" not in st:
        comp = [v for v in sel if mean_surv(st, v, 512, 36) is not None]
        dec = {"completed_512_variants": comp}
        rss = [
            result(hid(v, 512, d, i))["peak_rss_mb"]
            for v in sel
            for d in (36, 28)
            for i in range(3)
            if result(hid(v, 512, d, i))
        ]
        if not comp:
            dec["decision"] = "NOTRUN_no_complete_chi512"
        else:
            best = max(comp, key=lambda v: (mean_surv(st, v, 512, 36), -sel.index(v)))
            t512 = [result(hid(best, 512, 36, i))["wall_s"] for i in range(3)]
            t256 = [result(hid(best, 256, 36, i))["wall_s"] for i in range(3)]
            alpha = math.log2((sum(t512) / 3) / (sum(t256) / 3))
            pred_rss = 4 * max(rss)
            dec.update(
                best=best,
                alpha=alpha,
                pred_rss_mb=pred_rss,
                t512=t512,
                pred_s=[t * 2**alpha for t in t512],
            )
            dec["decision"] = "NOTRUN_rss_prediction" if pred_rss > 3072 else "run_if_time"
        st["c1024"] = dec
        save(st)
        log("CHI1024", dec)
    dec = st["c1024"]
    if dec["decision"] != "run_if_time":
        return
    for i in range(3):
        run(st, hid(dec["best"], 1024, 36, i), mirror(dec["best"], i, 36, 1024), dec["pred_s"][i])


def finish(st):
    log("finishing: running analyze.py")
    p = subprocess.run([PY, str(HERE / "analyze.py")], capture_output=True, text=True)
    log("analyze rc", p.returncode, (p.stdout + p.stderr)[-500:])
    if p.returncode == 0:
        (RES / "RUN_COMPLETE").write_text(dt.datetime.now().isoformat())


if __name__ == "__main__":
    main()
