"""ADDENDUM_POSTDEADLINE.md runner: the 9 frozen d36 chi=512 cells, after the PREREG deadline (deviation W4).
Calls the frozen cell.py exactly as runner.py did; writes only to results_post/. Resumable. Never runs runner.py/analyze.py."""
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = "/home/mike-anderson/dev/cohezion/.venv/bin/python"
OUT = HERE / "results_post" / "cells"
LOG = HERE / "results_post" / "post.log"
STOP = dt.datetime.fromisoformat("2026-10-06T12:00:00-04:00").timestamp()
ORDER = [(v, i) for v in ("CRA_NSB", "RCM_NSB", "LOG_NSB") for i in (0, 1, 2)]
THREADS = json.loads((HERE / "results" / "state.json").read_text())["threads"]
FROZEN = {l.split()[1]: l.split()[0] for l in (HERE / "results" / "scripts_at_freeze.sha256").read_text().splitlines() if l.strip()}


def log(*a):
    line = dt.datetime.now().strftime("%m-%d %H:%M:%S") + " " + " ".join(map(str, a))
    print(line, flush=True)
    with LOG.open("a") as f:
        f.write(line + "\n")


def hashes_ok():
    bad = [f for f, h in FROZEN.items() if hashlib.sha256((HERE / f).read_bytes()).hexdigest() != h]
    add = (HERE / "ADDENDUM_POSTDEADLINE.sha16").read_text().strip()
    if hashlib.sha256((HERE / "ADDENDUM_POSTDEADLINE.md").read_bytes()).hexdigest()[:16] != add:
        bad.append("ADDENDUM_POSTDEADLINE.md")
    return bad


def mem_gib():
    return int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1]) / 2**20


OUT.mkdir(parents=True, exist_ok=True)
log("post_deadline start, threads", THREADS)
def run_cell(v, i):
    """One cell, with runner.py's frozen return-code semantics: rc 3 / MemAvailable = memory interruption, not an attempt
    (wait, re-run from scratch); rc 4 = RSS cap (NOT RUN); anything else = failure, never retried (addendum)."""
    cid = f"H_{v}_c512_d36_i{i}"
    out = OUT / f"{cid}.json"
    while True:
        if out.exists() or (OUT / f"{cid}.fail").exists() or (OUT / f"{cid}.notrun").exists():
            return
        if (bad := hashes_ok()):
            log("REFUSE: frozen-file hash mismatch", bad)
            sys.exit(2)
        while mem_gib() < 20 and time.time() < STOP:
            log("WAIT mem", f"{mem_gib():.1f} GiB < 20")
            time.sleep(120)
        left = STOP - time.time()
        if left <= 0:
            log("NOTRUN", cid, "addendum stop")
            (OUT / f"{cid}.notrun").write_text("addendum stop")
            return
        spec = {"kind": "mirror", "variant": v, "inst": i, "d": 36, "chi": 512}
        env = dict(os.environ, **{k: str(THREADS) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")})
        log("START", cid, json.dumps(spec))
        try:
            p = subprocess.run(["nice", "-n", "10", PY, str(HERE / "cell.py"), json.dumps(spec), str(out)],
                               env=env, capture_output=True, text=True, timeout=left)
        except subprocess.TimeoutExpired:
            log("NOTRUN", cid, "killed at addendum stop")
            (OUT / f"{cid}.notrun").write_text("killed at addendum stop")
            return
        err = (p.stdout + p.stderr)[-2000:]
        if p.returncode == 0 and out.exists():
            r = json.loads(out.read_text())
            log("DONE", cid, {k: r.get(k) for k in ("survival", "wall_s", "peak_rss_mb")})
            return
        out.unlink(missing_ok=True)
        if p.returncode == 3 or "MemAvailable" in err:
            log("WAIT mem during", cid, err.strip()[-200:].replace("\n", " | "), "(not an attempt; re-run from scratch)")
            continue
        if p.returncode == 4:
            log("NOTRUN", cid, "RSS cap")
            (OUT / f"{cid}.notrun").write_text(err)
            return
        log("FAIL", cid, "rc", p.returncode, err[-400:].replace("\n", " | "))
        (OUT / f"{cid}.fail").write_text(err)
        return


for v, i in ORDER:
    run_cell(v, i)
log("POST_DEADLINE_FINISHED", sorted(f.stem for f in OUT.glob("*.json")))
