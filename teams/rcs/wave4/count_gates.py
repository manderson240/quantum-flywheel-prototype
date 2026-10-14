"""rcs wave 4: gate counts of mirror / patched / full d36 circuits and the pre-registered bias test (PREREG.md).

Own line parser; numeric angles only through qasm_angle.angle() (never eval). No binding of _theta_ inputs.
"""

from __future__ import annotations

import json
import math
import re
import resource
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from qasm_angle import angle  # noqa: E402


DATA = ROOT / "refs/rcs-nighthawk-data/data"
META = ROOT / "refs/rcs-nighthawk-meta/data"
OUT = Path(__file__).resolve().parent / "results"
N = 61

SKIP = re.compile(r"^(OPENQASM|include|bit\[|qubit\[|input\s+float)")
GATE = re.compile(r"^([a-z]+)\s*(?:\(([^)]*)\))?\s*(.*)$")
QARG = re.compile(r"^q\[(\d+)\]$")
MEAS = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\[\d+\]\s*=\s*measure\s+q\[\d+\]$")


class ParseError(ValueError):
    pass


def parse(path: Path):
    text = re.sub(r"//[^\n]*", "", path.read_text())
    ops = []  # (name, qubits tuple, param float | str | None)
    for raw in text.split(";"):
        s = " ".join(raw.split())
        if not s or SKIP.match(s):
            continue
        if MEAS.match(s):
            ops.append(("measure", (), None))
            continue
        m = GATE.match(s)
        if not m:
            raise ParseError(f"{path.name}: unrecognised statement {s[:80]!r}")
        name, par, args = m.group(1), m.group(2), m.group(3)
        if name == "barrier":
            ops.append(("barrier", (), None))
            continue
        if name == "measure":
            ops.append(("measure", (), None))
            continue
        if name not in ("rz", "rx", "sx", "x", "cz"):
            raise ParseError(f"{path.name}: unsupported gate {name!r}")
        qs = []
        for a in args.split(","):
            qm = QARG.match(a.strip())
            if not qm:
                raise ParseError(f"{path.name}: bad qubit arg {a!r}")
            qs.append(int(qm.group(1)))
        p = None
        if par is not None:
            ps = par.strip()
            if re.fullmatch(r"_theta_\d+_", ps):
                p = ps  # prep parameter: counted by name, never bound
            else:
                p = angle(ps)
        ops.append((name, tuple(qs), p))
    return ops


def counts(ops):
    c = {"cz": 0, "rx": 0, "rz": 0, "sx": 0, "x": 0, "prep_rx": 0, "barrier": 0, "measure": 0}
    layers, cur = [], []
    exposure = [0] * N
    coupler = {}
    for name, qs, p in ops:
        if name == "cz":
            cur.append(tuple(sorted(qs)))
            c["cz"] += 1
            for q in qs:
                exposure[q] += 1
            e = "%d-%d" % tuple(sorted(qs))
            coupler[e] = coupler.get(e, 0) + 1
            continue
        if cur:
            layers.append(cur)
            cur = []
        if name == "rx" and isinstance(p, str):
            c["prep_rx"] += 1
        else:
            c[name] += 1
    if cur:
        layers.append(cur)
    c["cz_layers"] = len(layers)
    c["idle_qubit_layers"] = sum(N - 2 * len(L) for L in layers)
    return c, layers, exposure, coupler


def _same(a, b):
    d = (a - b) % (2 * math.pi)
    return min(d, 2 * math.pi - d) <= 1e-9


def mirror_checks(ops, layers, layout):
    body = [o for o in ops if o[0] not in ("barrier", "measure") and not isinstance(o[2], str)]
    n = len(body)
    s1_bad = 0
    for k in range(n // 2):
        a, b = body[k], body[n - 1 - k]
        if (
            a[0] != b[0]
            or sorted(a[1]) != sorted(b[1])
            or (a[0] in ("rz", "rx") and not _same(a[2], -b[2]))
        ):
            s1_bad += 1
    s1 = {
        "ops": n,
        "even": n % 2 == 0,
        "mismatched_pairs": s1_bad,
        "pass": n % 2 == 0 and s1_bad == 0,
    }
    sched = layout["schedule"]
    parts = layout["partitions"]["3"]
    half = len(layers) // 2
    s2_bad = []
    for j in range(half):
        want = {
            tuple(sorted(e))
            for e in layout["matchings"][sched[j % len(sched)]]
            if e[0] < N and e[1] < N
        }
        want -= {tuple(sorted(e)) for e in parts[j % len(parts)]["boundary_edges"]}
        if set(layers[j]) != want:
            s2_bad.append(j)
    s2 = {
        "forward_layers": half,
        "mismatched_layers": s2_bad,
        "pass": not s2_bad and len(layers) % 2 == 0,
    }
    s3 = {
        "junction_duplicate": len(layers) % 2 == 0 and set(layers[half - 1]) == set(layers[half]),
        "junction_layer_size": len(layers[half - 1]) if half else 0,
    }
    return s1, s2, s3


def main():
    layout = json.loads((DATA / "layout.json").read_text())
    manifest = {
        c["qasm3"]: c for c in json.loads((META / "circuits/manifest.json").read_text())["circuits"]
    }
    res = {"circuits": {}, "missing": [], "s4_manifest": {}}
    groups = {
        "mirror": [DATA / f"circuits/mirror/d36_instance{i}.qasm" for i in range(3)],
        "K3": sorted((DATA / "circuits/patched/K3/d36").glob("*.qasm")),
        "K4": sorted((DATA / "circuits/patched/K4/d36").glob("*.qasm")),
        "full": [META / "circuits/full/d36_logical.qasm", DATA / "circuits/full/d40_logical.qasm"],
    }
    per = {}
    for g, files in groups.items():
        per[g] = []
        for f in files:
            rel = str(f.relative_to(next(p for p in f.parents if p.name == "circuits")))
            try:
                ops = parse(f)
            except Exception as e:
                res["missing"].append({"file": rel, "error": str(e)})
                continue
            c, layers, exp, cpl = counts(ops)
            rec = {"group": g, "counts": c, "exposure": exp, "coupler": cpl}
            if g == "mirror":
                s1, s2, s3 = mirror_checks(ops, layers, layout)
                rec.update({"S1": s1, "S2": s2, "S3": s3})
            mk = rel
            if mk in manifest:
                res["s4_manifest"][mk] = {
                    "manifest_cz": manifest[mk]["cz"],
                    "mine": c["cz"],
                    "agree": manifest[mk]["cz"] == c["cz"],
                }
            res["circuits"][mk] = {k: v for k, v in rec.items() if k not in ("exposure", "coupler")}
            per[g].append(rec)
    res["rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    OUT.mkdir(exist_ok=True)
    (OUT / "gate_counts.json").write_text(json.dumps(res, indent=1))
    decide(per, res)


def mean(v):
    return sum(v) / len(v)


def decide(per, res):
    if len(per["mirror"]) < 2 or len(per["K3"]) < 12:
        out = {"verdict": "MISSING", "n_mirror": len(per["mirror"]), "n_K3": len(per["K3"])}
        (OUT / "bias_test.json").write_text(json.dumps(out, indent=1))
        print(out)
        return
    F_m, se_m, B_m = 2.2407541873352317e-3, 5.572416141157374e-5, 1.3260228091349258
    F_3, se_3, B_3 = 1.8390523976486782e-3, 4.0850529700543075e-5, 1.3842077369180354
    F_4, se_4, B_4 = 1.999385896123157e-3, 3.216069760032846e-5, 1.4460426427130502
    f = 0.871674814249307
    g = math.log(F_m / F_3)
    sig = math.sqrt((se_m * B_m / F_m) ** 2 + (se_3 * B_3 / F_3) ** 2)
    thr, thr_alt = g - 2 * sig, g - 2 * 0.0506

    def fam(key, grp):
        return [r["counts"][key] for r in per[grp]]

    NK3, NK4 = mean(fam("cz", "K3")), mean(fam("cz", "K4"))
    c = math.log(F_4 / F_3) / (NK3 - NK4)
    se_c = math.sqrt((se_4 * B_4 / F_4) ** 2 + (se_3 * B_3 / F_3) ** 2) / (NK3 - NK4)
    c_max = 36 * (-math.log(f)) / NK3
    D = -math.log(F_3)
    cat = {}
    for k in ("cz", "rx", "cz_layers", "prep_rx", "idle_qubit_layers"):
        cat[k] = {
            "mirror_mean": mean(fam(k, "mirror")),
            "mirror_each": fam(k, "mirror"),
            "K3_mean": mean(fam(k, "K3")),
            "K3_min": min(fam(k, "K3")),
            "K3_max": max(fam(k, "K3")),
            "K4_mean": mean(fam(k, "K4")),
        }
    Nm = cat["cz"]["mirror_mean"]
    dN = {k: cat[k]["K3_mean"] - cat[k]["mirror_mean"] for k in ("cz", "rx", "cz_layers")}
    G_c = c * dN["cz"]
    G_cmax = c_max * dN["cz"]
    G_all = D * max(0.0, max(dN[k] / cat[k]["K3_mean"] for k in dN))

    def rule(t):
        if all(v <= 0 for v in dN.values()):
            return "CANNOT EXPLAIN (count difference goes the wrong way)"
        if G_c >= t:
            return "EXPLAINS"
        if G_all < t:
            return "CANNOT EXPLAIN"
        return "PARTLY EXPLAINS"

    v1, v2 = rule(thr), rule(thr_alt)
    verdict = v1 if v1 == v2 else "BORDERLINE (flips with sigma convention)"
    junction = [
        r["S3"]["junction_layer_size"] if r["S3"]["junction_duplicate"] else 0
        for r in per["mirror"]
    ]
    Nm_cancel = Nm - mean(junction)
    Nfull = per["full"][0]["counts"]["cz"] if per["full"] else None
    # descriptive exposure / coupler comparison
    k3_exp = [mean([r["exposure"][q] for r in per["K3"]]) for q in range(N)]
    m_exp = [mean([r["exposure"][q] for r in per["mirror"]]) for q in range(N)]
    diff = [m_exp[q] - k3_exp[q] for q in range(N)]
    edges = set().union(*[r["coupler"] for r in per["K3"] + per["mirror"]])
    cu = {
        e: (
            mean([r["coupler"].get(e, 0) for r in per["mirror"]]),
            mean([r["coupler"].get(e, 0) for r in per["K3"]]),
        )
        for e in edges
    }
    out = {
        "inputs": {
            "g_ln_gap": g,
            "sigma_ln": sig,
            "thr": thr,
            "thr_alt_sigma0.0506": thr_alt,
            "c": c,
            "se_c": se_c,
            "c_max": c_max,
            "D": D,
        },
        "categories": cat,
        "dN_K3_minus_mirror": dN,
        "relative_cz_diff_vs_K3": (Nm - NK3) / NK3,
        "mirror_inside_K3_range": cat["cz"]["K3_min"] <= Nm <= cat["cz"]["K3_max"],
        "G_c": G_c,
        "G_c_minus2se": (c - 2 * se_c) * dN["cz"],
        "G_c_plus2se": (c + 2 * se_c) * dN["cz"],
        "G_cmax": G_cmax,
        "G_all": G_all,
        "G_c_over_g": G_c / g,
        "count_corrected_ln_gap_c": g - G_c,
        "count_corrected_ln_gap_cmax": g - G_cmax,
        "verdict_thr": v1,
        "verdict_thr_alt": v2,
        "VERDICT": verdict,
        "variant_junction_cancelled": {
            "N_m": Nm_cancel,
            "G_c": c * (NK3 - Nm_cancel),
            "G_cmax": c_max * (NK3 - Nm_cancel),
        },
        "variant_prep_in_1q": {
            "dN_rx_prep61": dN["rx"] - cat["prep_rx"]["mirror_mean"],
            "dN_rx_prep_half": dN["rx"] - 30.5,
        },
        "secondary_K4": {"dN_cz": NK4 - Nm, "G_c": c * (NK4 - Nm)},
        "secondary_full": {
            "N_full": Nfull,
            "G_full_c": c * (Nfull - Nm) if Nfull else None,
            "G_full_cmax": c_max * (Nfull - Nm) if Nfull else None,
        },
        "descriptive_exposure": {
            "mirror_minus_K3_per_qubit_min": min(diff),
            "max": max(diff),
            "mean": mean(diff),
        },
        "descriptive_coupler": {
            "n_couplers": len(cu),
            "mirror_only": sum(1 for v in cu.values() if v[0] > 0 and v[1] == 0),
            "K3_only": sum(1 for v in cu.values() if v[1] > 0 and v[0] == 0),
            "max_abs_usage_diff": max(abs(a - b) for a, b in cu.values()),
        },
        "structural": {
            str(i): {k: r[k] for k in ("S1", "S2", "S3")} for i, r in enumerate(per["mirror"])
        },
        "missing": res["missing"],
        "s4_all_agree": all(v["agree"] for v in res["s4_manifest"].values()),
        "s4_n": len(res["s4_manifest"]),
        "rss_mb": res["rss_mb"],
    }
    (OUT / "bias_test.json").write_text(json.dumps(out, indent=1))
    print(
        json.dumps(
            {
                k: out[k]
                for k in (
                    "VERDICT",
                    "verdict_thr_alt",
                    "dN_K3_minus_mirror",
                    "G_c",
                    "G_cmax",
                    "G_all",
                    "relative_cz_diff_vs_K3",
                    "s4_all_agree",
                    "s4_n",
                )
            },
            indent=1,
        )
    )


if __name__ == "__main__":
    main()
