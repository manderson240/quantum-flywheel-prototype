import sys

m = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1])
sys.exit(f"MemAvailable {m / 2**20:.1f} GiB < 20") if m < 20 * 2**20 else None
"""Arm B: run the project's check_claims.py, UNMODIFIED on disk, with only its two text reads redirected.

check_claims.py reads the application text in exactly two places:
    _rep = (_HERE / "report" / "report.html").read_text()
    _frm = (_HERE / "FORM_ANSWERS.md").read_text()
This runner reads the checker source, replaces those two path expressions (asserting one occurrence each)
with the planted copy's paths, and executes it with __file__ = the ORIGINAL checker path, so every other
input (results/, pilot/, refs/, graph/, teams/rcs/...) is read from the project exactly as in production.
SUBMISSION_KIT.md is not read by check_claims.py at all, so arm B cannot see kit plants.

  python3 run_armB.py --dry                                   # replacement + compile only
  python3 run_armB.py --original > baseline.txt                # the same runner on the originals
  python3 run_armB.py --copy corpus/copy_A > A.txt             # a corpus copy
Exit status is check_claims.py's own (0 = all pass, 1 = some FAIL).
"""
import argparse
import os
from pathlib import Path


ROOT = Path.home() / "cohezion-labs" / "bluequbit-flywheel"
CHECKER = ROOT / "check_claims.py"
EXPR = {"report": '(_HERE / "report" / "report.html")', "form": '(_HERE / "FORM_ANSWERS.md")'}


def patched_source(report: Path, form: Path) -> str:
    src = CHECKER.read_text()
    for k, e in EXPR.items():
        n = src.count(e)
        assert n == 1, (
            f"checker text read {k!r} found {n} times (expected 1); checker changed, arm B invalid"
        )
    src = src.replace(EXPR["report"], f"Path({str(report.resolve())!r})")
    src = src.replace(EXPR["form"], f"Path({str(form.resolve())!r})")
    return src


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry", action="store_true")
    g.add_argument("--original", action="store_true")
    g.add_argument("--copy")
    a = ap.parse_args()
    if a.original or a.dry:
        report, form = ROOT / "report/report.html", ROOT / "FORM_ANSWERS.md"
    else:
        base = Path(a.copy)
        report, form = base / "report/report.html", base / "FORM_ANSWERS.md"
    assert report.is_file() and form.is_file(), (report, form)
    code = compile(patched_source(report, form), str(CHECKER), "exec")
    if a.dry:
        print(f"DRY OK: both text reads replaced once; compiled; would read {report} and {form}")
        return
    os.chdir(ROOT)
    sys.argv = [str(CHECKER)]
    exec(code, {"__name__": "__main__", "__file__": str(CHECKER)})


if __name__ == "__main__":
    main()
