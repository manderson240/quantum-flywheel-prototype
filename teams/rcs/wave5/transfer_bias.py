import sys

m = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1])
sys.exit(f"MemAvailable {m / 2**20:.1f} GiB < 20") if m < 20 * 2**20 else None
"""rcs wave 5: gate-count bias of transferring proxy fidelities to the 918-CZ full circuit.

Implements PREREG.md (sha16 beed370d62a9d547) exactly. Reads qasm/json as text; never evals, never unpickles.
Usage: nice -n 10 python3 transfer_bias.py   (writes results/run_<timestamp>/, never overwrites)
"""
import datetime
import json
import math
import re
import resource
from pathlib import Path


resource.setrlimit(resource.RLIMIT_AS, (1 << 30, 1 << 30))
MEM_AVAIL_KB_AT_START = m

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from qasm_angle import angle  # noqa: E402


DATA = ROOT / "refs/rcs-nighthawk-data/data"
META = ROOT / "refs/rcs-nighthawk-meta/data"
WINDOW = [20, 24, 28, 32, 36, 40]
Z95 = 1.96
L_QUOTED = 1.8e-3
# PREREG K0.1 (wave-3 gap_d36.json): level, shot se, instance Birge
LEVEL = {
    "mirror": (2.2407541873352317e-3, 5.572416141157374e-05, 1.3260228091349258),
    "K3": (1.8390523976486782e-3, 4.0850529700543075e-05, 1.3842077369180354),
    "K4": (1.999385896123157e-3, 3.216069760032846e-05, 1.4460426427130502),
}

# ---------------------------------------------------------------- parser
SKIP = re.compile(r"^(OPENQASM|include|bit\s*\[|qubit\s*\[|input\s+float)")
G1 = re.compile(r"^(rz|rx|sx|x)\s*(?:\((.*)\))?\s+q\[(\d+)\]$")
CZ = re.compile(r"^cz\s+q\[(\d+)\]\s*,\s*q\[(\d+)\]$")
BAR = re.compile(r"^barrier\b")
MEAS = re.compile(r"^[A-Za-z_]\w*\[\d+\]\s*=\s*measure\s+q\[\d+\]$")


def parse(path):
    """Return (n_cz, final_cz_layer_size) or raise ValueError."""
    text = re.sub(r"//[^\n]*", "", Path(path).read_text())
    ops = []  # 'cz' | 'g' (1q gate) | 'b' (barrier) | 'm'
    for st in text.split(";"):
        st = " ".join(st.split())
        if not st or SKIP.match(st):
            continue
        if CZ.match(st):
            ops.append("cz")
            continue
        g = G1.match(st)
        if g:
            if g.group(2) is not None and "_theta_" not in g.group(2):
                angle(g.group(2))  # validates grammar; raises ValueError otherwise
            ops.append("g")
            continue
        if BAR.match(st):
            ops.append("b")
            continue
        if MEAS.match(st):
            ops.append("m")
            continue
        raise ValueError(f"unsupported statement in {path}: {st[:80]!r}")
    n_cz = ops.count("cz")
    # final CZ layer: maximal run of cz after which only barriers/measures follow
    i = len(ops) - 1
    while i >= 0 and ops[i] in ("b", "m"):
        i -= 1
    final = 0
    while i >= 0 and ops[i] == "cz":
        final += 1
        i -= 1
    return n_cz, final


# ---------------------------------------------------------------- stats
def wls_line(x, y, w):
    sw = sum(w)
    sx = sum(wi * xi for wi, xi in zip(w, x))
    sy = sum(wi * yi for wi, yi in zip(w, y))
    sxx = sum(wi * xi * xi for wi, xi in zip(w, x))
    sxy = sum(wi * xi * yi for wi, xi, yi in zip(w, x, y))
    det = sw * sxx - sx * sx
    b = (sw * sxy - sx * sy) / det
    a = (sy - b * sx) / sw
    se_b = math.sqrt(sw / det)
    chi2 = sum(wi * (yi - a - b * xi) ** 2 for wi, xi, yi in zip(w, x, y))
    return a, b, se_b, chi2


def ols_line(x, y):
    n = len(x)
    xb = sum(x) / n
    yb = sum(y) / n
    sxx = sum((xi - xb) ** 2 for xi in x)
    b = sum((xi - xb) * (yi - yb) for xi, yi in zip(x, y)) / sxx
    a = yb - b * xb
    s = math.sqrt(sum((yi - a - b * xi) ** 2 for xi, yi in zip(x, y)) / (n - 2))
    return a, b, s, xb, sxx, n


def fam_slope(points, depths, birge=True):
    x = depths
    y = [math.log(points[str(d)]["fidelity"]) for d in depths]
    w = [(points[str(d)]["fidelity"] / points[str(d)]["se"]) ** 2 for d in depths]
    a, b, se_b, chi2 = wls_line(x, y, w)
    s = max(1.0, math.sqrt(chi2 / (len(x) - 2))) if birge else 1.0
    return {
        "lambda": -b,
        "se_lambda": se_b * s,
        "se_lambda_shot": se_b,
        "chi2": chi2,
        "dof": len(x) - 2,
        "birge": s,
    }


# ---------------------------------------------------------------- main
def main():
    t0 = datetime.datetime.now()
    out_dir = Path(__file__).resolve().parent / "results" / f"run_{t0:%Y%m%d_%H%M%S}"
    out_dir.mkdir(parents=True, exist_ok=False)
    missing, errors = [], []

    # --- d36 counts (own parser)
    def count(paths, tag):
        res = {}
        for p in paths:
            try:
                res[str(p.relative_to(ROOT))] = parse(p)
            except (ValueError, OSError) as e:
                errors.append(f"{tag}: {e}")
        return res

    full = count([META / "circuits/full/d36_logical.qasm"], "full")
    mir = count(sorted((DATA / "circuits/mirror").glob("d36_instance*.qasm")), "mirror")
    k3 = count(sorted((DATA / "circuits/patched/K3/d36").glob("*.qasm")), "K3")
    k4 = count(sorted((DATA / "circuits/patched/K4/d36").glob("*.qasm")), "K4")
    if len(full) < 1:
        missing.append("full")
    if len(mir) < 2:
        missing.append("mirror")
    if len(k3) < 12:
        missing.append("K3")
    if len(k4) < 12:
        missing.append("K4")

    def mean(d, i=0):
        return sum(v[i] for v in d.values()) / len(d) if d else float("nan")

    N = {"full": mean(full), "mirror": mean(mir), "K3": mean(k3), "K4": mean(k4)}
    FINAL = {"full": mean(full, 1), "mirror": mean(mir, 1), "K3": mean(k3, 1), "K4": mean(k4, 1)}
    counts = {
        "N_mean": N,
        "final_layer_mean": FINAL,
        "per_file": {
            **{k: list(v) for k, v in full.items()},
            **{k: list(v) for k, v in mir.items()},
            **{k: list(v) for k, v in k3.items()},
            **{k: list(v) for k, v in k4.items()},
        },
        "K3_minmax": [min(v[0] for v in k3.values()), max(v[0] for v in k3.values())],
        "K4_minmax": [min(v[0] for v in k4.values()), max(v[0] for v in k4.values())],
    }

    # --- per-cycle CZ rates from manifest, with spot-check vs own counts
    man = json.loads((META / "circuits/manifest.json").read_text())["circuits"]
    by = {"mirror": {}, "K3": {}, "K4": {}, "full": {}}
    for c in man:
        q = c.get("qasm3", c["file"])
        md = re.search(r"d(\d+)", q.split("/")[-2] + "/" + q.split("/")[-1]) if "/" in q else None
        dm = re.search(r"/d(\d+)[_/]", "/" + q)
        if not dm:
            continue
        d = int(dm.group(1))
        if c["kind"] == "mirror":
            fam = "mirror"
        elif c["kind"] == "patched":
            fam = "K3" if "/K3/" in "/" + q else ("K4" if "/K4/" in "/" + q else None)
        elif c["kind"] == "full":
            fam = "full"
        else:
            continue
        if fam:
            by[fam].setdefault(d, []).append((q, c["cz"]))
    spot = []
    for fam in ("K3", "K4"):
        for d in WINDOW:
            for q, cz in by[fam].get(d, []):
                p = DATA / "circuits" / q
                if p.exists():
                    try:
                        own = parse(p)[0]
                    except ValueError as e:
                        errors.append(f"spot {q}: {e}")
                        continue
                    spot.append({"file": q, "manifest": cz, "own": own, "agree": own == cz})
    own_override = {s["file"]: s["own"] for s in spot if not s["agree"]}
    z, zmeans = {}, {}
    for fam in ("mirror", "K3", "K4", "full"):
        ds = [d for d in WINDOW if by[fam].get(d)]
        means = [sum(own_override.get(q, cz) for q, cz in by[fam][d]) / len(by[fam][d]) for d in ds]
        zmeans[fam] = {str(d): {"mean_cz": mm, "n": len(by[fam][d])} for d, mm in zip(ds, means)}
        if len(ds) >= 2:
            z[fam] = ols_line(ds, means)[1]
        else:
            missing.append(f"z_{fam}")

    # --- fidelity slopes
    fvd = json.loads((META / "results/fidelity_vs_depth.json").read_text())
    pts = {
        "mirror": fvd["points"]["mirror"],
        "K3": fvd["points"]["3-patch"],
        "K4": fvd["points"]["4-patch"],
    }
    for fam in pts:
        if any(str(d) not in pts[fam] for d in WINDOW):
            missing.append(f"points_{fam}")
    if missing:
        (out_dir / "transfer_bias.json").write_text(
            json.dumps({"verdict": "MISSING", "missing": missing, "errors": errors}, indent=1)
        )
        print("MISSING", missing, errors)
        return

    def slopes(windows, birge=True):
        return {fam: fam_slope(pts[fam], windows[fam], birge) for fam in pts}

    def m2(sl):
        fams = ["mirror", "K3", "K4"]
        a, b, se_b, chi2 = wls_line(
            [z[f] for f in fams],
            [sl[f]["lambda"] for f in fams],
            [1 / sl[f]["se_lambda"] ** 2 for f in fams],
        )
        return {
            "alpha": a,
            "beta": b,
            "se_beta_unscaled": se_b,
            "chi2_reg": chi2,
            "se_beta": se_b * max(1.0, math.sqrt(chi2 / 1)),
        }

    # star (authors' fit, unweighted OLS on ln F, mirror d4-40)
    md_all = sorted(int(d) for d in pts["mirror"])
    a_s, b_s, s_s, xb, sxx, n_s = ols_line(
        md_all, [math.log(pts["mirror"][str(d)]["fidelity"]) for d in md_all]
    )
    star = {
        "F": math.exp(a_s + b_s * 36),
        "se_ln": s_s * math.sqrt(1 / n_s + (36 - xb) ** 2 / sxx),
        "f_per_cycle": math.exp(b_s),
    }

    def sources(Nm_override=None, Nfull=None, Nsrc=None):
        Nf = N["full"] if Nfull is None else Nfull
        Ns = dict(N) if Nsrc is None else dict(Nsrc)
        if Nm_override is not None:
            Ns["mirror"] = Nm_override
        src = {}
        for fam in ("mirror", "K3", "K4"):
            F, se, B = LEVEL[fam]
            src[fam] = {"F": F, "se_ln": se * B / F, "dN": Nf - Ns[fam]}
        src["star"] = {"F": star["F"], "se_ln": star["se_ln"], "dN": Nf - Ns["mirror"]}
        return src

    def predict(beta, se_beta, src, beta_by_src=None):
        rows = {}
        for k, s in src.items():
            bb, sb = (beta, se_beta) if beta_by_src is None else beta_by_src[k]
            B = bb * s["dN"]
            sig = math.sqrt(s["se_ln"] ** 2 + (s["dN"] * sb) ** 2)
            Fh = s["F"] * math.exp(-B)
            rows[k] = {
                "dN": s["dN"],
                "bias_ln": B,
                "F_hat": Fh,
                "sigma_ln": sig,
                "lo95": Fh * math.exp(-Z95 * sig),
                "hi95": Fh * math.exp(Z95 * sig),
                "bias_ln_95up": (bb + Z95 * sb) * s["dN"],
                "F_at_95up_bias": s["F"] * math.exp(-(bb + Z95 * sb) * s["dN"]),
            }
        pts_ok = all(r["F_hat"] >= L_QUOTED for r in rows.values())
        beyond = all(r["hi95"] < L_QUOTED for r in rows.values())
        cls = (
            "WITHIN QUOTED RANGE"
            if pts_ok
            else "BIASED BEYOND QUOTED RANGE"
            if beyond
            else "BELOW RANGE FOR SOME SOURCES, NOT RESOLVED: "
            + ",".join(k for k, r in rows.items() if r["F_hat"] < L_QUOTED)
        )
        return {
            "rows": rows,
            "class": cls,
            "X": max(r["bias_ln"] for r in rows.values()),
            "X95": max(r["bias_ln_95up"] for r in rows.values()),
            "at_95up_all_ge_1.8e-3": all(r["F_at_95up_bias"] >= L_QUOTED for r in rows.values()),
            "at_95up_below_1.8e-3": [k for k, r in rows.items() if r["F_at_95up_bias"] < L_QUOTED],
        }

    def analysis(windows, birge=True, Nm_override=None, Nfull=None, Nsrc=None):
        sl = slopes(windows, birge)
        reg = m2(sl)
        src = sources(Nm_override, Nfull, Nsrc)
        b1 = {
            f: (sl[f]["lambda"] / z[f], sl[f]["se_lambda"] / z[f]) for f in ("mirror", "K3", "K4")
        }
        b1["star"] = b1["mirror"]
        beta_bound = b1["mirror"][0]
        lo, hi = reg["beta"] - Z95 * reg["se_beta"], reg["beta"] + Z95 * reg["se_beta"]
        t1 = "DETECTED" if lo > 0 else ("OPPOSITE SIGN" if hi < 0 else "NOT DETECTED")
        t2 = "M1 EXCLUDED" if hi < beta_bound else "M1 NOT EXCLUDED"
        # M3
        F3, se3, B3 = LEVEL["K3"]
        F4, se4, B4 = LEVEL["K4"]
        NK3 = N["K3"] if Nsrc is None else Nsrc["K3"]
        NK4 = N["K4"] if Nsrc is None else Nsrc["K4"]
        c = math.log(F4 / F3) / (NK3 - NK4)
        se_c = math.sqrt((se4 * B4 / F4) ** 2 + (se3 * B3 / F3) ** 2) / (NK3 - NK4)
        lam_m, zm = sl["mirror"]["lambda"], z["mirror"]
        res = {
            "slopes": sl,
            "z": z,
            "M2": reg,
            "beta_M1_mirror_bound": beta_bound,
            "T1": t1,
            "T2": t2,
            "beta_M2_ci95": [lo, hi],
            "MDE_beta": 2.80 * reg["se_beta"],
            "MDE_bias_ln_at_mirror": 2.80 * reg["se_beta"] * src["mirror"]["dN"],
            "phi_M2": reg["beta"] * zm / lam_m,
            "phi_M2_ci95": [lo * zm / lam_m, hi * zm / lam_m],
            "M3": {
                "c": c,
                "se_c": se_c,
                "phi": c * zm / lam_m,
                "phi_ci95": [(c - Z95 * se_c) * zm / lam_m, (c + Z95 * se_c) * zm / lam_m],
            },
            "pred": {
                "M0": predict(0.0, 0.0, src),
                "M1_bound": predict(None, None, src, b1),
                "M2": predict(reg["beta"], reg["se_beta"], src),
                "M3": predict(c, se_c, src),
            },
        }
        if t1 == "DETECTED":
            head = f"TRANSFER BIASED BY GATE COUNT (proxies' own data): M2 {res['pred']['M2']['class']}"
        elif t2 == "M1 EXCLUDED":
            head = (
                f"NO GATE-COUNT DEPENDENCE DETECTED ({t1}); data bound the bias at X_M2,95 = "
                f"{res['pred']['M2']['X95']:.4f} ln; at that bound all sources >= 1.8e-3: "
                f"{res['pred']['M2']['at_95up_all_ge_1.8e-3']}"
            )
        else:
            head = "UNDETERMINED - proxies cannot discriminate; bias in [0, M1 bound]"
        res["headline"] = head + " (MODEL-DEPENDENT)"
        return res

    W = dict.fromkeys(pts, WINDOW)
    primary = analysis(W)
    variants = {}
    # V1 output-affecting counts (subtract final pre-measure CZ layer; mirror unchanged)
    Nv1 = {
        "full": N["full"] - FINAL["full"],
        "mirror": N["mirror"] - FINAL["mirror"],
        "K3": N["K3"] - FINAL["K3"],
        "K4": N["K4"] - FINAL["K4"],
    }
    variants["V1_output_affecting"] = analysis(W, Nfull=Nv1["full"], Nsrc=Nv1)
    variants["V1_output_affecting"]["counts"] = Nv1
    # V2 junction cancelled mirror
    jl = 20  # duplicated layer size (wave-4 S3, re-derived below from parse is not possible without layer split)
    variants["V2_junction_cancelled"] = analysis(W, Nm_override=N["mirror"] - jl)
    # V3 windows
    variants["V3a_all_d24_40"] = analysis(dict.fromkeys(pts, WINDOW[1:]))
    variants["V3b_mirror_d4_40"] = analysis({"mirror": md_all, "K3": WINDOW, "K4": WINDOW})
    # V4 no Birge
    variants["V4_no_birge"] = analysis(W, birge=False)
    # M3 with K3/K4 extremes
    m3x = {}
    for tag, n3, n4 in (
        ("K3min_K4max", counts["K3_minmax"][0], counts["K4_minmax"][1]),
        ("K3max_K4min", counts["K3_minmax"][1], counts["K4_minmax"][0]),
    ):
        F3, se3, B3 = LEVEL["K3"]
        F4, se4, B4 = LEVEL["K4"]
        c = math.log(F4 / F3) / (n3 - n4)
        m3x[tag] = {
            "c": c,
            "bias_ln_mirror": c * (N["full"] - N["mirror"]),
            "F_hat_mirror": LEVEL["mirror"][0] * math.exp(-c * (N["full"] - N["mirror"])),
        }
    variants["M3_count_extremes"] = m3x

    cost = {
        k: primary["pred"][k]["rows"]["star"]["F_hat"] / 2.3e-3
        for k in ("M0", "M1_bound", "M2", "M3")
    }
    out = {
        "prereg_sha16": "beed370d62a9d547",
        "run_start": t0.isoformat(),
        "mem_avail_gib_at_start": MEM_AVAIL_KB_AT_START / 2**20,
        "counts": counts,
        "manifest_z_means": zmeans,
        "spot_check": {"n": len(spot), "all_agree": all(s["agree"] for s in spot), "rows": spot},
        "star": star,
        "primary": primary,
        "variants": variants,
        "derived_cost_factor_Eq3_star_source_NO_VERDICT_WEIGHT": cost,
        "errors": errors,
        "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
    }
    (out_dir / "transfer_bias.json").write_text(json.dumps(out, indent=1))
    p = primary
    print(
        "counts",
        {k: round(v, 2) for k, v in N.items()},
        "final",
        FINAL,
        "z",
        {k: round(v, 3) for k, v in z.items()},
    )
    print("spot all agree", out["spot_check"]["all_agree"], len(spot), "errors", errors)
    for f, s in p["slopes"].items():
        print(f, {k: round(v, 5) for k, v in s.items()})
    print(
        "M2",
        {k: round(v, 6) for k, v in p["M2"].items()},
        "M1 bound",
        round(p["beta_M1_mirror_bound"], 6),
    )
    print(
        "T1",
        p["T1"],
        "T2",
        p["T2"],
        "MDE",
        round(p["MDE_beta"], 6),
        round(p["MDE_bias_ln_at_mirror"], 4),
        "phi",
        round(p["phi_M2"], 3),
        [round(v, 3) for v in p["phi_M2_ci95"]],
        "M3",
        p["M3"],
    )
    for mdl, r in p["pred"].items():
        print(mdl, r["class"], "X", round(r["X"], 4), "X95", round(r["X95"], 4))
        for k, row in r["rows"].items():
            print(
                "   ",
                k,
                f"F_hat {row['F_hat']:.4e} [{row['lo95']:.3e},{row['hi95']:.3e}] bias {row['bias_ln']:.4f}",
            )
    print("HEADLINE", p["headline"])
    for vn, v in variants.items():
        if "T1" in v:
            print(
                vn,
                v["T1"],
                v["T2"],
                "beta",
                round(v["M2"]["beta"], 6),
                "+-",
                round(v["M2"]["se_beta"], 6),
                "M2",
                v["pred"]["M2"]["class"],
                "X95",
                round(v["pred"]["M2"]["X95"], 4),
                "| M3",
                v["pred"]["M3"]["class"],
            )
        else:
            print(vn, v)
    print("out", out_dir, "rss_mb", out["peak_rss_mb"])


if __name__ == "__main__":
    main()
