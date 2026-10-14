"""Calibration for the ordering-invention pilot: is there headroom between orderings, and at which chi?"""

from __future__ import annotations

import json
import statistics

import ordering_lab as L


LATTICES = {"dev_heavyhex19": L.dev_lattice(), "test_square4x5": L.square_lattice(4, 5)}
INST = [(0, cyc, 1.56567, 0.33879, ob) for cyc in (6, 12) for ob in ("mag", "zzd2")]


def orderings(n, e):
    out = {"native": L.native(n, e), "rcm": L.rcm(n, e), "spectral": L.spectral(n, e)}
    for s in range(4):
        out[f"cutwidthSA{s}"] = L.cutwidth_sa(n, e, 30000, seed=s)
    for s in range(6):
        out[f"random{s}"] = L.random_order(n, e, seed=s)
    return out


def main() -> int:
    res = {}
    for lname, (n, e) in LATTICES.items():
        ords = orderings(n, e)
        # relabelling must not change the exact value (checked once per ordering)
        worst = max(L.check_relabel_invariance(n, e, od, INST[0]) for od in ords.values())
        assert worst < 1e-9, f"relabel changed exact value by {worst}"
        for chi in (4, 8, 16):
            ev = L.Evaluator(n, e, INST, chi, L.HERE / f"cache_{lname}.json")
            for oname, od in ords.items():
                le = ev.log_errors(od)
                res.setdefault(lname, {}).setdefault(str(chi), {})[oname] = {
                    "cutwidth": L.cutwidth(od, e),
                    "mean_log10_err": statistics.mean(le),
                    "log10_errs": le,
                }
                print(
                    lname, chi, oname, L.cutwidth(od, e), round(statistics.mean(le), 3), flush=True
                )
            (L.HERE / "calibration.json").write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
