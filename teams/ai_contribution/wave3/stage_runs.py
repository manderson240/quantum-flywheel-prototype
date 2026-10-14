import sys


m = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1])
sys.exit(f"MemAvailable {m / 2**20:.1f} GiB < 20") if m < 20 * 2**20 else None
"""Stage the 12 verifier runs (3 copies x 2 arms x 2 runs) for the orchestrator. Opens no copy's contents.

  python3 stage_runs.py            # stage all 12; refuses if runs/staging.tsv exists
  python3 stage_runs.py --one A_Q_run2   # re-stage ONE run for the PREREG sec. 4 retry (fresh dir, same prompt text)

For each run: `cp -a corpus/copy_<L>` to ~/cohezion-labs/review_pkg_<random hex>/ (the name carries no label or arm),
create a private `_scratch/` inside it, and write the exact prompt to briefs_sent/<L>_<ARM>_run<r>.md:
  the arm's brief with {PKG} and {OUT} substituted, followed by HARNESS_NOTE.md with {SCRATCH} substituted
  (identical note for both arms). Nothing else is added. runs/staging.tsv maps run -> dir, and runs/launch_order.txt
  is a random launch order that interleaves arms and copies.
"""
import os
import random
import secrets
import subprocess
from pathlib import Path


WAVE = Path(__file__).resolve().parent
BASE = Path.home() / "cohezion-labs"
BRIEF = {"G": WAVE / "VERIFIER_BRIEF.md", "Q": WAVE / "QUALIFIER_BRIEF.md"}
RUNS = [f"{L}_{a}_run{r}" for L in ("A", "B", "C") for a in ("G", "Q") for r in (1, 2)]


def prompt(arm, pkg):
    b = (
        BRIEF[arm]
        .read_text()
        .replace("{PKG}", str(pkg))
        .replace("{OUT}", str(pkg / "VERIFICATION.md"))
    )
    h = (WAVE / "HARNESS_NOTE.md").read_text().replace("{SCRATCH}", str(pkg / "_scratch"))
    assert "{PKG}" not in b and "{OUT}" not in b and "{SCRATCH}" not in h, "unsubstituted placeholder"
    return b + h


def stage(run_id):
    lab, arm = run_id[0], run_id.split("_")[1]
    d = BASE / f"review_pkg_{secrets.token_hex(4)}"
    assert not d.exists()
    subprocess.run(["cp", "-a", str(WAVE / "corpus" / f"copy_{lab}"), str(d)], check=True)
    (d / "_scratch").mkdir()
    out = WAVE / "briefs_sent" / f"{run_id}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(prompt(arm, d))
    return d


def main():
    (WAVE / "runs").mkdir(exist_ok=True)
    tsv = WAVE / "runs" / "staging.tsv"
    if len(sys.argv) > 2 and sys.argv[1] == "--one":
        rid = sys.argv[2]
        assert rid in RUNS, rid
        d = stage(rid)
        with tsv.open("a") as f:
            f.write(f"{rid}\t{d}\tretry\n")
        print(rid, d)
        return
    assert not tsv.exists(), "already staged"
    rows = [(rid, stage(rid)) for rid in RUNS]
    tsv.write_text("".join(f"{rid}\t{d}\tfirst\n" for rid, d in rows))
    order = [rid for rid, _ in rows]
    random.Random(os.urandom(8)).shuffle(order)
    (WAVE / "runs" / "launch_order.txt").write_text("\n".join(order) + "\n")
    print(f"staged {len(rows)} runs; prompts in briefs_sent/; order in runs/launch_order.txt")


if __name__ == "__main__":
    main()
