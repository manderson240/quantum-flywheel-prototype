"""rcs wave 3: independent mirror-fidelity reproduction + d36 mirror-vs-patch gap analysis.

Implements teams/rcs/wave3/PREREG.md (sha256[:16] checked at start). Own implementation; the authors'
analysis/fidelity_vs_depth.py and rcs/estimators.py were read, never imported or executed. JSON/qasm text only.
Run:  nice -n 10 python3 teams/rcs/wave3/mirror_analysis.py
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import resource
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = ROOT / "refs" / "rcs-nighthawk-data"
META = ROOT / "refs" / "rcs-nighthawk-meta"
OUT = HERE / "results"
LN10 = math.log(10.0)


def check_prereg():
    h = hashlib.sha256((HERE / "PREREG.md").read_bytes()).hexdigest()[:16]
    frozen = (HERE / "PREREG.sha16").read_text().strip()
    if h != frozen:
        sys.exit(f"PREREG hash mismatch {h} != {frozen}")
    return h


def mem_available_gib():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / 2**20
    return 0.0


# ---------- basic estimators (own code) ----------
def instance_survival(hits, shots):
    h = np.array(hits, dtype=float).sum(axis=1)
    n = np.array(shots, dtype=float).sum(axis=1)
    p = h / n
    se = np.sqrt(np.maximum(p * (1 - p), 1e-12) / n)
    return p, se, n


def ivw(values, ses):
    v, s = np.asarray(values, float), np.asarray(ses, float)
    w = 1.0 / s**2
    m = float((w * v).sum() / w.sum())
    return (
        m,
        float(math.sqrt(1.0 / w.sum())),
        float((w * (v - m) ** 2).sum()),
    )  # mean, se, chi2 about mean


def dersimonian_laird(values, ses):
    v, s = np.asarray(values, float), np.asarray(ses, float)
    w = 1.0 / s**2
    m0 = (w * v).sum() / w.sum()
    q = (w * (v - m0) ** 2).sum()
    k = len(v)
    tau2 = max(0.0, (q - (k - 1)) / (w.sum() - (w**2).sum() / w.sum()))
    ws = 1.0 / (s**2 + tau2)
    return float((ws * v).sum() / ws.sum()), float(math.sqrt(1.0 / ws.sum())), float(tau2)


def ols(x, y):
    """Closed-form simple OLS: returns intercept, slope, residual s^2 (dof n-2), Sxx, xbar."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    xb, yb = x.mean(), y.mean()
    sxx = ((x - xb) ** 2).sum()
    b = ((x - xb) * (y - yb)).sum() / sxx
    a = yb - b * xb
    rss = ((y - a - b * x) ** 2).sum()
    return a, b, rss / (len(x) - 2), sxx, xb


def wls(X, y, w):
    X, y, w = np.asarray(X, float), np.asarray(y, float), np.asarray(w, float)
    A = X.T @ (w[:, None] * X)
    cov = np.linalg.inv(A)
    beta = cov @ (X.T @ (w * y))
    r = y - X @ beta
    return beta, cov, float((w * r**2).sum())


def rel(a, b):
    return abs(a - b) / abs(b)


def tier(r):
    return "EXACT" if r <= 1e-9 else ("NUMERICAL" if r <= 1e-6 else "DISCREPANT")


def normal_p(z):
    return math.erfc(abs(z) / math.sqrt(2))


def main():
    prereg = check_prereg()
    mem0 = mem_available_gib()
    log = {"prereg_sha16": prereg, "mem_available_gib_at_start": mem0}
    mirror = json.loads((DATA / "data" / "counts" / "mirror_survival.json").read_text())["depths"]
    released = json.loads((META / "data" / "results" / "fidelity_vs_depth.json").read_text())
    records = json.loads((DATA / "data" / "results" / "patch_xeb.json").read_text())
    nq = json.loads((DATA / "data" / "layout.json").read_text())["num_qubits"]
    depths = sorted(int(d) for d in mirror)

    # ---------------- data-consistency checks C1-C3 ----------------
    c1_equal, c2_range, c3_ok, c1_meaninputs = True, True, True, {}
    inst = {}
    tot_prev = 0.0
    c2_monotone = True
    for d in depths:
        e = mirror[str(d)]
        H, N = np.array(e["hits"]), np.array(e["shots"])
        c3_ok &= bool(
            np.all(np.round(H) == H)
            and np.all(np.round(N) == N)
            and np.all(H >= 0)
            and np.all(H <= N)
        )
        eq = bool(np.all(N[:, :1] == N))
        c1_equal &= eq
        p, se, n = instance_survival(H, N)
        inst[d] = (p, se, n, H, N)
        c2_range &= bool(np.all(n >= 3e4) and np.all(n <= 3.5e5))
        c2_monotone &= bool(n.min() >= tot_prev)
        tot_prev = n.max()
        pm = (H / N).mean(axis=1)
        c1_meaninputs[d] = {"max_abs_diff_sum_vs_mean": float(np.abs(pm - p).max())}
    checks = {
        "C1_equal_shots_across_inputs": c1_equal,
        "C2_instance_shots_in_3e4_3.5e5": c2_range,
        "C2_nondecreasing_with_depth": c2_monotone,
        "C3_integer_and_bounded": c3_ok,
        "instance_shot_totals": {d: inst[d][2].tolist() for d in depths},
        "per_input_shots_min_max": {
            d: [int(inst[d][4].min()), int(inst[d][4].max())] for d in depths
        },
        "C1_sum_vs_mean_over_inputs": c1_meaninputs,
    }

    # ---------------- reproduction R1-R23 ----------------
    pooled = {}
    chi2_m, dof_m = 0.0, 0
    for d in depths:
        p, se, _, _, _ = inst[d]
        m, s, c2 = ivw(p, se)
        pooled[d] = (m, s)
        chi2_m += c2
        dof_m += len(p) - 1
    logF = np.log10([pooled[d][0] for d in depths])
    a, b, s2, sxx, xb = ols(depths, logF)
    A, f = 10**a, 10**b
    epq = -math.log(f) / nq
    fitted = {d: A * f**d for d in (20, 24, 28, 32, 36, 40)}
    units = []
    rm = released["points"]["mirror"]
    for i, d in enumerate(depths, 1):
        rf, rs = rm[str(d)]["fidelity"], rm[str(d)]["se"]
        r1, r2 = rel(pooled[d][0], rf), rel(pooled[d][1], rs)
        t = max((tier(r1), tier(r2)), key=["EXACT", "NUMERICAL", "DISCREPANT"].index)
        units.append(
            {
                "unit": f"R{i}",
                "depth": d,
                "mine": list(pooled[d]),
                "released": [rf, rs],
                "rho_fid": r1,
                "rho_se": r2,
                "tier": t,
            }
        )
    rfit = released["fit"]
    extra = [
        ("R15 prefactor", A, rfit["prefactor"]),
        ("R16 per_cycle", f, rfit["fidelity_per_cycle"]),
        ("R17 error_per_qubit_per_cycle", epq, rfit["error_per_qubit_per_cycle"]),
    ]
    extra += [
        (f"R{18 + j} fitted_{d}", fitted[d], rfit["fitted_fidelity"][str(d)])
        for j, d in enumerate((20, 24, 28, 32, 36, 40))
    ]
    for name, mine, rv in extra:
        units.append(
            {
                "unit": name,
                "mine": mine,
                "released": rv,
                "rho": rel(mine, rv),
                "tier": tier(rel(mine, rv)),
            }
        )
    tiers = [u["tier"] for u in units]
    ne, nn, nd = tiers.count("EXACT"), tiers.count("NUMERICAL"), tiers.count("DISCREPANT")
    if ne == 23:
        verdict = "REPRODUCED"
    elif nd == 0 and ne + nn == 23:
        verdict = "REPRODUCED-NUMERICAL"
    elif nd >= 12:
        verdict = "NOT REPRODUCED"
    else:
        verdict = f"PARTIAL ({ne}/23 EXACT, {nd}/23 DISCREPANT)"
    repro = {
        "units": units,
        "counts": {"EXACT": ne, "NUMERICAL": nn, "DISCREPANT": nd},
        "verdict": verdict,
        "max_rho": max(
            max(u.get("rho_fid", 0), u.get("rho_se", 0), u.get("rho", 0)) for u in units
        ),
    }

    # ---------------- patch pooling ----------------
    groups = defaultdict(list)
    for r in records:
        groups[(r["K"], r["depth"])].append(r)
    ppool, pchi = {}, {}
    for key, rs in groups.items():
        m, s, c2 = ivw([r["fidelity"] for r in rs], [r["se"] for r in rs])
        ppool[key] = (m, s)
        pchi[key] = (c2, len(rs) - 1)
    pdepths = sorted({d for (_, d) in groups})

    # ---------------- §4 gap at d36 ----------------
    B_m_raw = math.sqrt(chi2_m / dof_m)
    B_m = max(1.0, B_m_raw)
    Fm, sm = pooled[36]
    fit36 = fitted[36]
    se_fit36_log = math.sqrt(s2) * math.sqrt(1 / len(depths) + (36 - xb) ** 2 / sxx)
    se_fit36 = fit36 * LN10 * se_fit36_log
    gap = {
        "B_mirror_pooled": {"chi2": chi2_m, "dof": dof_m, "B": B_m_raw},
        "fit36": fit36,
        "se_fit36_residual": se_fit36,
    }
    m36 = inst[36]
    dl_m = dersimonian_laird(m36[0], m36[1])
    for K in (3, 4):
        FK, sK = ppool[(K, 36)]
        c2, dof = pchi[(K, 36)]
        BK_raw = math.sqrt(c2 / dof)
        BK = max(1.0, BK_raw)
        G = Fm - FK
        sig = {
            "a_shot": math.hypot(sm, sK),
            "b_patch_inflated": math.hypot(sm, sK * BK),
            "c_both_inflated": math.hypot(sm * B_m, sK * BK),
        }
        z = {k: G / v for k, v in sig.items()}
        rsK = groups[(K, 36)]
        dl_K = dersimonian_laird([r["fidelity"] for r in rsK], [r["se"] for r in rsK])
        Gdl = dl_m[0] - dl_K[0]
        sdl = math.hypot(dl_m[1], dl_K[1])
        fitG = fit36 - FK
        fitsig = {"shot": math.hypot(se_fit36, sK), "patch_inflated": math.hypot(se_fit36, sK * BK)}
        row = {
            "F_mirror": Fm,
            "se_mirror": sm,
            "F_patch": FK,
            "se_patch": sK,
            "B_patch_d36": {"chi2": c2, "dof": dof, "B": BK_raw},
            "gap": G,
            "ln_gap": math.log(Fm / FK),
            "sigma": sig,
            "z": z,
            "p_two_sided": {k: normal_p(v) for k, v in z.items()},
            "DL": {"mirror": dl_m, "patch": dl_K, "gap": Gdl, "se": sdl, "z": Gdl / sdl},
            "fit36_minus_patch": {"gap": fitG, "z": {k: fitG / v for k, v in fitsig.items()}},
        }
        if K == 3:
            row["verdict_primary_c"] = (
                "gap CONSISTENT with observed overdispersion"
                if abs(z["c_both_inflated"]) < 3
                else "gap PERSISTS beyond overdispersion"
            )
        gap[f"mirror_vs_{K}patch"] = row
    gap["fit36_minus_mirror"] = {
        "gap": fit36 - Fm,
        "z_shot": (fit36 - Fm) / math.hypot(se_fit36, sm),
        "z_mirror_inflated": (fit36 - Fm) / math.hypot(se_fit36, sm * B_m),
    }

    # ---------------- E2/E3 depth dependence ----------------
    e23 = {}
    for K in (3, 4):
        c2sum = sum(pchi[(K, d)][0] for d in pdepths)
        dofsum = sum(pchi[(K, d)][1] for d in pdepths)
        BKp_raw = math.sqrt(c2sum / dofsum)
        BKp = max(1.0, BKp_raw)
        ys, xs, ws, perd = [], [], [], {}
        for d in pdepths:
            FK, sK = ppool[(K, d)]
            Fmd, smd = pooled[d]
            y = math.log(Fmd / FK)
            var = (smd * B_m / Fmd) ** 2 + (sK * BKp / FK) ** 2
            var_shot = (smd / Fmd) ** 2 + (sK / FK) ** 2
            ys.append(y)
            xs.append(d - 36)
            ws.append(1 / var)
            perd[d] = {
                "ln_ratio": y,
                "se_infl": math.sqrt(var),
                "z_shot_linear": (Fmd - FK) / math.hypot(smd, sK),
                "z_infl_ln": y / math.sqrt(var),
                "se_shot": math.sqrt(var_shot),
            }
        X = np.column_stack([np.ones(len(xs)), xs])
        beta, cov, chi2r = wls(X, ys, ws)
        infl = max(1.0, math.sqrt(chi2r / (len(xs) - 2)))
        se_slope = math.sqrt(cov[1, 1]) * infl
        se_int = math.sqrt(cov[0, 0]) * infl
        tsl = beta[1] / se_slope
        call = (
            "E3 per-cycle difference SUPPORTED (E2-alone refuted)"
            if abs(tsl) >= 3
            else ("E2 constant offset favoured" if abs(tsl) < 2 else "inconclusive (2-3 sigma)")
        )
        e23[f"K{K}"] = {
            "B_patch_pooled_all_depths": {"chi2": c2sum, "dof": dofsum, "B": BKp_raw},
            "per_depth": perd,
            "intercept_ln_gap_at_36": beta[0],
            "se_intercept": se_int,
            "slope_per_cycle": beta[1],
            "se_slope": se_slope,
            "t_slope": tsl,
            "per_cycle_fidelity_ratio": math.exp(beta[1]),
            "chi2_res": chi2r,
            "dof_res": len(xs) - 2,
            "slope_se_inflation": infl,
            "call": call,
        }
    matched = {}
    for name, series in (
        ("mirror", {d: pooled[d][0] for d in pdepths}),
        ("3-patch", {d: ppool[(3, d)][0] for d in pdepths}),
        ("4-patch", {d: ppool[(4, d)][0] for d in pdepths}),
    ):
        aa, bb, ss2, _, _ = ols(pdepths, np.log10([series[d] for d in pdepths]))
        matched[name] = {
            "prefactor_d0": 10**aa,
            "per_cycle": 10**bb,
            "resid_s_log10": math.sqrt(ss2),
        }
    e23["matched_range_20_40_unweighted_fits_descriptive"] = matched

    # ---------------- E4 gate-count bound ----------------
    cz = {}
    for K in (3, 4):
        for fpath in sorted(
            (DATA / "data" / "circuits" / "patched" / f"K{K}" / "d36").glob("*.qasm")
        ):
            n = sum(1 for line in fpath.read_text().splitlines() if re.match(r"\s*cz\s", line))
            mm = re.match(r"partition(\d)_instance(\d)", fpath.stem)
            cz[(K, int(mm.group(1)), int(mm.group(2)))] = n
    NK3 = float(np.mean([v for k, v in cz.items() if k[0] == 3]))
    NK4 = float(np.mean([v for k, v in cz.items() if k[0] == 4]))
    c_pt = (math.log(ppool[(4, 36)][0]) - math.log(ppool[(3, 36)][0])) / (NK3 - NK4)
    c_max = -36 * math.log(f) / NK3
    lngap = gap["mirror_vs_3patch"]["ln_gap"]
    # CORRECTED after the first run (13:47): the first version used sigma_c / F_3 (0.0506), which is not the
    # delta-method sigma of ln(F_m/F_3) that PREREG §5 E4 specifies. Correct form below. Disclosed in STATUS.
    _B3 = max(1.0, gap["mirror_vs_3patch"]["B_patch_d36"]["B"])
    sig_ln = math.hypot(sm * B_m / Fm, ppool[(3, 36)][1] * _B3 / ppool[(3, 36)][0])
    bound_pt, bound_max = 0.02 * NK3 * c_pt, 0.02 * NK3 * c_max
    # exploratory: per-circuit ln F vs CZ across 15 K3 circuits
    xs = [cz[(3, r["partition"], r["instance"])] for r in groups[(3, 36)]]
    ys = [math.log(r["fidelity"]) for r in groups[(3, 36)]]
    ea, eb, es2, esxx, _ = ols(xs, ys)
    e4 = {
        "cz_counts": {f"K{k[0]}_p{k[1]}_i{k[2]}": v for k, v in sorted(cz.items())},
        "mean_cz_K3": NK3,
        "mean_cz_K4": NK4,
        "c_per_cz_from_K4_vs_K3": c_pt,
        "c_max_all_decay_on_cz": c_max,
        "ln_gap_observed": lngap,
        "sigma_ln_gap_variant_c_approx": sig_ln,
        "bound_2pct_c_point": bound_pt,
        "bound_2pct_c_max": bound_max,
        "call": (
            "a <=2% mismatch cannot alone explain the gap"
            if bound_pt < lngap - 2 * sig_ln
            else "a <=2% mismatch could explain the gap"
        ),
        "call_with_c_max": (
            "cannot alone explain" if bound_max < lngap - 2 * sig_ln else "could explain"
        ),
        "EXPLORATORY_perK3circuit_lnF_vs_cz": {
            "slope_per_cz": eb,
            "se_slope": math.sqrt(es2 / esxx),
            "n": len(xs),
            "note": "confounded by patch geometry",
        },
    }

    # ---------------- E5 fit vs direct, curvature ----------------
    dd = np.array(depths, float)
    Xq = np.column_stack([np.ones_like(dd), dd - dd.mean(), (dd - dd.mean()) ** 2])
    beta_q, *_ = np.linalg.lstsq(Xq, logF, rcond=None)
    resq = logF - Xq @ beta_q
    s2q = (resq**2).sum() / (len(dd) - 3)
    covq = s2q * np.linalg.inv(Xq.T @ Xq)
    t_curv = beta_q[2] / math.sqrt(covq[2, 2])
    wlog = np.array([(pooled[d][0] * LN10 / pooled[d][1]) ** 2 for d in depths])
    bw, _, _ = wls(np.column_stack([np.ones_like(dd), dd]), logF, wlog)
    a2, b2, _, _, _ = ols(pdepths, np.log10([pooled[d][0] for d in pdepths]))
    chi2_fit = float(
        (
            ((logF - (a + b * dd)) * LN10 * np.array([pooled[d][0] / pooled[d][1] for d in depths]))
            ** 2
        ).sum()
    )
    e5 = {
        "quadratic_coef": beta_q[2],
        "t_curvature": t_curv,
        "dof": len(dd) - 3,
        "call": "single exponential MISSPECIFIED"
        if abs(t_curv) >= 3
        else "no significant curvature",
        "unweighted_fit_residuals_log10": dict(zip(depths, (logF - (a + b * dd)).tolist())),
        "chi2_mirror_points_about_unweighted_fit_shot": chi2_fit,
        "chi2_dof": len(dd) - 2,
        "weighted_log_fit_F36": 10 ** (bw[0] + bw[1] * 36),
        "weighted_log_fit": [10 ** bw[0], 10 ** bw[1]],
        "fit_20_40_only_F36": 10 ** (a2 + b2 * 36),
        "fit_20_40_only": [10**a2, 10**b2],
        "fit36_over_3patch": fit36 / ppool[(3, 36)][0],
        "mirror36_over_3patch": Fm / ppool[(3, 36)][0],
    }

    # ---------------- E6 input heterogeneity ----------------
    chi2_in, dof_in, worst = 0.0, 0, []
    for d in depths:
        p, _, _, H, N = inst[d]
        for i in range(H.shape[0]):
            ex = N[i] * p[i]
            c = float(((H[i] - ex) ** 2 / (N[i] * p[i] * (1 - p[i]))).sum())
            chi2_in += c
            dof_in += H.shape[1] - 1
            worst.append((c, d, i))
    from math import lgamma  # noqa: F401  (p-value via Wilson-Hilferty)

    wh = ((chi2_in / dof_in) ** (1 / 3) - (1 - 2 / (9 * dof_in))) / math.sqrt(2 / (9 * dof_in))
    p_in = 0.5 * math.erfc(wh / math.sqrt(2))
    B_in = math.sqrt(chi2_in / dof_in)
    e6 = {
        "chi2": chi2_in,
        "dof": dof_in,
        "B_in": B_in,
        "p_upper_wilson_hilferty": p_in,
        "call": "input-dependent heterogeneity PRESENT"
        if (B_in > 1.2 and p_in < 1e-3)
        else "not established",
        "worst_cells": [
            {"chi2": c, "depth": d, "instance": i} for c, d, i in sorted(worst, reverse=True)[:5]
        ],
        "mirror_instance_B_pooled": B_m_raw,
    }

    # ---------------- E7 partition dependence ----------------
    rs3 = groups[(3, 36)]
    parts = sorted({r["partition"] for r in rs3})
    pmeans = {}
    for pt in parts:
        sub = [r for r in rs3 if r["partition"] == pt]
        pmeans[pt] = ivw([r["fidelity"] for r in sub], [r["se"] for r in sub])[:2]
    _, _, chi2_between = ivw([v[0] for v in pmeans.values()], [v[1] for v in pmeans.values()])
    loo = {}
    for pt in parts:
        sub = [r for r in rs3 if r["partition"] != pt]
        m, s, c2 = ivw([r["fidelity"] for r in sub], [r["se"] for r in sub])
        Bl = max(1.0, math.sqrt(c2 / (len(sub) - 1)))
        loo[pt] = {
            "F3": m,
            "se": s,
            "B": math.sqrt(c2 / (len(sub) - 1)),
            "z_c": (Fm - m) / math.hypot(sm * B_m, s * Bl),
        }
    e7 = {
        "partition_means": pmeans,
        "chi2_between": chi2_between,
        "dof": len(parts) - 1,
        "p_between_approx": None,
        "leave_one_out": loo,
        "call": (
            "primary gap driven by one partition"
            if any(abs(v["z_c"]) < 3 for v in loo.values())
            else "no single partition drives the gap"
        ),
    }

    rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    log.update({"peak_rss_mb": rss_mb, "mem_available_gib_at_end": mem_available_gib()})
    OUT.mkdir(exist_ok=True)
    for name, obj in (
        ("checks", checks),
        ("reproduction", repro),
        ("gap_d36", gap),
        ("depth_dependence", e23),
        ("gate_count_bound", e4),
        ("fit_vs_direct", e5),
        ("input_heterogeneity", e6),
        ("partition_dependence", e7),
        ("run_log", log),
    ):
        (OUT / f"{name}.json").write_text(json.dumps(obj, indent=1, default=float))
    print(
        json.dumps(
            {
                "verdict": verdict,
                "max_rho": repro["max_rho"],
                "checks": {k: v for k, v in checks.items() if k.startswith("C")},
                "rss_mb": rss_mb,
            },
            default=float,
        )
    )


if __name__ == "__main__":
    main()
