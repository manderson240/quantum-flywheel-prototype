import sys


m = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1])
sys.exit(f"MemAvailable {m / 2**20:.1f} GiB < 20") if m < 20 * 2**20 else None
"""Scorer for the wave-3 qualifier-procedure benchmark (frozen rule: PREREG.md sections 5-8).

  python3 score.py --self-test
  python3 score.py --mutation-test
  python3 score.py --key SEALED/key.json --corpus corpus --reports runs [--adjudication adj.json] [--out score.json]

Reports are named <LABEL>_<ARM>_run<r>.md (LABEL in A-C, ARM in G,Q). A run that failed twice is recorded by the
orchestrator as <LABEL>_<ARM>_run<r>.MISSING (PREREG sec. 4); a report without a FINDINGS= line is also MISSING.
Adapted from wave-2 score.py; every change is listed in PREREG sec. 5.1. Prints plant ids and aggregates only.
"""
import argparse
import difflib
import json
import math
import re
import tempfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
from build import DOCS, clean, norm_doc, segments  # noqa: E402  (same normalisation as the builder)


ROW = re.compile(r"^\s*\|\s*(\d+)\s*\|(.*)\|\s*$")
FIND = re.compile(r"^\s*FINDINGS\s*=\s*(\d+)\s*$", re.M)
RUN = re.compile(r"^([A-Z])_([GQ])_run(\d+)$")
MIN_QUOTE = 8
ARMS = ("G", "Q")
BOOT_B, BOOT_SEED = 2000, 30260927
# Frozen decision thresholds (PREREG sec. 7).
T_RECALL_Q, T_DIFF, T_FP_MARGIN, T_OTHER_DROP, T_G_HIGH = 0.5, 0.3, 5.0, 0.25, 0.5
MIN_PLANTED_RUNS, MIN_PLACEBO_RUNS = 3, 1  # per arm


def lcs(a, b):
    return (
        difflib.SequenceMatcher(None, a, b, autojunk=False)
        .find_longest_match(0, len(a), 0, len(b))
        .size
    )


def parse_report(text):
    rows = []
    for line in text.splitlines():
        mm = ROW.match(line)
        if not mm:
            continue
        cols = [c.strip() for c in mm.group(2).split("|")]
        if len(cols) < 6:
            rows.append(
                {
                    "n": int(mm.group(1)),
                    "malformed": True,
                    "loc": "",
                    "quote": "",
                    "text": " ".join(cols),
                }
            )
            continue
        rows.append(
            {
                "n": int(mm.group(1)),
                "malformed": False,
                "loc": cols[0],
                "quote": "|".join(cols[1:-4]),
                "type": cols[-4],
                "text": " ".join(cols[-4:]),
            }
        )
    fm = FIND.findall(text)
    return rows, (int(fm[-1]) if fm else None)


def doc_of(loc):
    s = loc.lower()
    if "report" in s:
        return "report"
    if "form_answers" in s or "form" in s:
        return "form"
    if "kit" in s:
        return "kit"
    return None


def locate(f, segs):
    """(doc -> set of best segments, best lcs, ambiguous, normalised quote) — wave-2 rule, unchanged."""
    q = clean(norm_doc(f["quote"], "<" in f["quote"])).lower().strip(" \"'“”")
    if len(q) < MIN_QUOTE:
        return {}, 0, False, q
    docs = [doc_of(f["loc"])] if doc_of(f["loc"]) else list(segs)
    best, where = 0, {}
    for d in docs:
        for s in segs[d]:
            v = lcs(q, s.lower())
            if v > best:
                best, where = v, {d: {s}}
            elif v == best and v > 0:
                where.setdefault(d, set()).add(s)
    ambiguous = sum(len(v) for v in where.values()) > 1
    return where, best, ambiguous, q


def located_plants(f, segs, plants):
    where, best, amb, q = locate(f, segs) if not f["malformed"] else ({}, 0, False, "")
    need = min(20, math.ceil(0.8 * len(q))) if q else 10**9
    locp = sorted(
        {
            p["id"]
            for p in plants
            for L in p["locations"]
            if L["doc"] in where and L["sentence_norm"] in where[L["doc"]] and best >= need
        }
    )
    return locp, amb


def score_run(run_id, text, plants, segs, adj):
    rows, declared = parse_report(text)
    hit, dup, out, non_plant, pending_plants, overruled = {}, [], [], [], set(), []
    for f in rows:
        fid = f"{run_id}#{f['n']}"
        locp, amb = located_plants(f, segs, plants)
        a = adj.get(fid, {})
        if not locp:
            non_plant.append((fid, a.get("verdict", "PENDING"), a.get("defect_id")))
            out.append((fid, "NON_PLANT", None))
            continue
        txt = clean(f["text"]).lower()
        auto = [
            pid
            for pid in locp
            if not amb
            and any(
                re.search(pt, txt)
                for pt in next(p for p in plants if p["id"] == pid)["auto_patterns"]
            )
        ]
        cand, status = auto, "AUTO_HIT"
        if auto and a.get("verdict") == "MISS":
            overruled.append(fid)
            auto = []
        if not auto:
            if a.get("verdict") == "HIT" and a.get("plant") in locp:
                cand, status = [a["plant"]], "ADJ_HIT"
            elif a.get("verdict") in ("MISS", "PREEXISTING", "FP", "UNRESOLVED"):
                v = (
                    a.get("verdict")
                    if a.get("verdict") != "MISS"
                    else a.get("np_verdict", "PENDING")
                )
                non_plant.append((fid, v, a.get("defect_id")))
                out.append((fid, "ADJ_MISS", locp))
                continue
            else:
                pending_plants.update(locp)
                out.append((fid, "NEEDS_ADJ", locp))
                continue
        new = [pid for pid in cand if pid not in hit]
        if new:
            hit[new[0]] = fid
            out.append((fid, status, new[0]))
        else:
            dup.append(fid)
            out.append((fid, "DUPLICATE", cand[0]))
    miss = [p["id"] for p in plants if p["id"] not in hit and p["id"] not in pending_plants]
    return {
        "run": run_id,
        "rows": len(rows),
        "declared": declared,
        "count_mismatch": declared is None or declared != len(rows),
        "auto_hits_overruled": overruled,
        "hits": sorted(hit),
        "misses": sorted(miss),
        "pending_plants": sorted(pending_plants - set(hit)),
        "duplicates": dup,
        "non_plant": non_plant,
        "findings": out,
    }


def arm_of(run_id):
    mm = RUN.match(run_id)
    return (mm.group(1), mm.group(2)) if mm else (None, None)


def boot(clusters, B=BOOT_B, seed=BOOT_SEED):
    """Percentile CIs over distinct plants (clusters) resampled with replacement.
    clusters: {plant: {"G": [hits, n], "Q": [hits, n]}}. Returns CIs for recall G, recall Q and the paired
    difference Q - G (both arms use the SAME resampled plants)."""
    import random as _r

    ids = sorted(clusters)
    if not ids:
        return None
    rng = _r.Random(seed)
    est = {"G": [], "Q": [], "diff": []}
    for _ in range(B):
        smp = [clusters[rng.choice(ids)] for _ in ids]
        r = {}
        for a in ARMS:
            n = sum(c[a][1] for c in smp)
            r[a] = sum(c[a][0] for c in smp) / n if n else float("nan")
        est["G"].append(r["G"])
        est["Q"].append(r["Q"])
        est["diff"].append(r["Q"] - r["G"])
    ci = {}
    for k, v in est.items():
        v = sorted(x for x in v if x == x)
        ci[k] = (
            (round(v[int(0.025 * len(v))], 3), round(v[int(0.975 * len(v)) - 1], 3)) if v else None
        )
    return ci


def recall_block(runs, plants, group, pending_as_hit):
    """Per-arm recall on one plant group, and per-plant clusters for the bootstrap."""
    cl, tot = {}, {a: [0, 0] for a in ARMS}
    for r in runs:
        for p in plants[r["label"]]:
            if p["group"] != group:
                continue
            h = p["id"] in r["hits"] or (pending_as_hit and p["id"] in r["pending_plants"])
            c = cl.setdefault(p["id"], {a: [0, 0] for a in ARMS})
            c[r["arm"]][0] += h
            c[r["arm"]][1] += 1
            tot[r["arm"]][0] += h
            tot[r["arm"]][1] += 1
    rec = {a: (round(tot[a][0] / tot[a][1], 3) if tot[a][1] else None) for a in ARMS}
    return rec, tot, cl


def verdict(S):
    """Frozen decision rule (PREREG sec. 7). S holds the computed statistics; returns (code, sentences)."""
    if S["instrument_failure"]:
        return "INSTRUMENT_FAILURE", [
            "The benchmark failed as an instrument ("
            + "; ".join(S["instrument_failure"])
            + "), so no verifier result is reported."
        ]

    def decide(qQ, qG, lb, fpQ, fpG):
        d = qQ - qG
        rec_ok = qQ >= T_RECALL_Q and d >= T_DIFF and lb > 0
        if rec_ok and fpQ <= fpG + T_FP_MARGIN:
            return "CLOSES"
        if rec_ok:
            return "RECALL_GAIN_AT_FP_COST"
        if d >= T_DIFF and lb > 0:
            return "PARTIAL_GAIN"
        if d >= T_DIFF:
            return "GAIN_NOT_DEMONSTRATED"
        return "NO_IMPROVEMENT"

    lo = decide(
        S["qual_recall"]["Q"],
        S["qual_recall"]["G"],
        S["qual_diff_ci"][0],
        S["fp_upper"]["Q"],
        S["fp_upper"]["G"],
    )
    hi = decide(
        S["qual_recall_pending_hit"]["Q"],
        S["qual_recall_pending_hit"]["G"],
        S["qual_diff_ci_pending_hit"][0],
        S["fp_upper"]["Q"],
        S["fp_upper"]["G"],
    )
    code = lo if lo == hi else "UNDECIDED_PENDING_ADJUDICATION"
    return code, VERDICT_TEXT[code]


VERDICT_TEXT = {
    "CLOSES": [
        "The qualifier procedure closes the blind spot on this benchmark: it raised deleted-qualifier recall "
        "by at least 0.3 (bootstrap lower bound above 0) to at least 0.5, without more than 5 extra false "
        "findings per placebo run."
    ],
    "RECALL_GAIN_AT_FP_COST": [
        "The qualifier procedure raised deleted-qualifier recall enough to meet the recall "
        "criteria, but at a cost of more than 5 extra false findings per placebo run, so it "
        "does not close the blind spot as pre-registered."
    ],
    "PARTIAL_GAIN": [
        "The qualifier procedure raised deleted-qualifier recall by at least 0.3 (bootstrap lower "
        "bound above 0), but its recall stayed below 0.5, so it narrows the blind spot without closing it."
    ],
    "GAIN_NOT_DEMONSTRATED": [
        "The qualifier procedure's recall exceeded the generic brief's by at least 0.3, but the "
        "bootstrap interval over distinct plants includes zero, so an improvement is not "
        "demonstrated."
    ],
    "NO_IMPROVEMENT": [
        "No improvement: the qualifier procedure did not raise deleted-qualifier recall by the "
        "pre-registered 0.3 over the generic brief. This does not support adding it to our "
        "verification protocol as a fix for dropped qualifiers."
    ],
    "UNDECIDED_PENDING_ADJUDICATION": [
        "Undecided: the verdict depends on items still pending adjudication "
        "(pending-as-miss and pending-as-hit give different outcomes)."
    ],
}


def run(key, corpus, reports, adj):
    res = {"A": [], "missing": [], "summary": {}}
    plants = {lab: c["plants"] for lab, c in key["copies"].items()}
    for lab, c in sorted(key["copies"].items()):
        segs = {
            d: segments((corpus / f"copy_{lab}" / p).read_text(), d == "report")
            for d, p in DOCS.items()
        }
        for rp in sorted(reports.glob(f"{lab}_*_run*.*")):
            L, arm = arm_of(rp.stem)
            if lab != L or rp.suffix not in (".md", ".MISSING"):
                continue
            text = rp.read_text() if rp.suffix == ".md" else ""
            if rp.suffix == ".MISSING" or FIND.search(text) is None:
                res["missing"].append({"run": rp.stem, "label": lab, "arm": arm, "kind": c["kind"]})
                continue
            r = score_run(rp.stem, text, c["plants"], segs, adj)
            r.update(label=lab, arm=arm, kind=c["kind"])
            res["A"].append(r)
    S = res["summary"]
    runsP = [r for r in res["A"] if r["kind"] == "planted"]
    runsC = [r for r in res["A"] if r["kind"] == "placebo"]
    fail = []
    for a in ARMS:
        nP = sum(r["arm"] == a for r in runsP)
        nC = sum(r["arm"] == a for r in runsC)
        S[f"runs_valid_{a}"] = {"planted": nP, "placebo": nC}
        S[f"runs_missing_{a}"] = [m["run"] for m in res["missing"] if m["arm"] == a]
        if nP < MIN_PLANTED_RUNS:
            fail.append(f"arm {a}: {nP} valid planted-copy runs < {MIN_PLANTED_RUNS}")
        if nC < MIN_PLACEBO_RUNS:
            fail.append(f"arm {a}: {nC} valid placebo runs < {MIN_PLACEBO_RUNS}")
    S["instrument_failure"] = fail
    for tag, ph in (("", False), ("_pending_hit", True)):
        rec, tot, cl = recall_block(runsP, plants, "qualifier", ph)
        S[f"qual_recall{tag}"] = rec
        S[f"qual_counts{tag}"] = {a: f"{tot[a][0]}/{tot[a][1]}" for a in ARMS}
        ci = boot(cl) if cl else None
        S[f"qual_ci{tag}"] = ci
        S[f"qual_diff{tag}"] = round(rec["Q"] - rec["G"], 3) if None not in rec.values() else None
        S[f"qual_diff_ci{tag}"] = ci["diff"] if ci else None
        rec_o, tot_o, cl_o = recall_block(runsP, plants, "other", ph)
        S[f"other_recall{tag}"] = rec_o
        S[f"other_counts{tag}"] = {a: f"{tot_o[a][0]}/{tot_o[a][1]}" for a in ARMS}
    S["qual_distinct_plants"] = len(
        {p["id"] for ps in plants.values() for p in ps if p["group"] == "qualifier"}
    )
    S["other_distinct_plants"] = len(
        {p["id"] for ps in plants.values() for p in ps if p["group"] == "other"}
    )
    for fld in ("cross_doc_tell", "restriction", "cls", "id"):
        agg = {}
        for r in runsP:
            for p in plants[r["label"]]:
                a = agg.setdefault(str(p[fld]), {x: [0, 0] for x in ARMS})
                a[r["arm"]][0] += p["id"] in r["hits"]
                a[r["arm"]][1] += 1
        S[f"by_{fld}"] = {
            g: {x: f"{v[x][0]}/{v[x][1]}" for x in ARMS} for g, v in sorted(agg.items())
        }
    S["unique_qual_caught_any_run"] = {
        a: len({pid for r in runsP if r["arm"] == a for pid in r["hits"] if pid.startswith("Q")})
        for a in ARMS
    }
    S["pending_plant_runs"] = {
        a: sum(len(r["pending_plants"]) for r in runsP if r["arm"] == a) for a in ARMS
    }
    S["auto_hits_overruled"] = {
        a: sum(len(r["auto_hits_overruled"]) for r in runsP if r["arm"] == a) for a in ARMS
    }
    cnt = lambda rs, v: sum(1 for r in rs for _, s, _d in r["non_plant"] if s == v)
    S["fp_upper"], S["fp_lower"] = {}, {}
    for a in ARMS:
        rc = [r for r in runsC if r["arm"] == a]
        rp = [r for r in runsP if r["arm"] == a]
        S[f"nonplant_placebo_{a}"] = {
            v: cnt(rc, v) for v in ("PREEXISTING", "FP", "UNRESOLVED", "MISLOCATED", "PENDING")
        }
        S[f"nonplant_planted_{a}"] = {
            v: cnt(rp, v) for v in ("PREEXISTING", "FP", "UNRESOLVED", "MISLOCATED", "PENDING")
        }
        S["fp_upper"][a] = (
            round((cnt(rc, "FP") + cnt(rc, "UNRESOLVED")) / len(rc), 2) if rc else None
        )
        S["fp_lower"][a] = round(cnt(rc, "FP") / len(rc), 2) if rc else None
        S[f"fp_planted_per_run_{a}"] = round(cnt(rp, "FP") / len(rp), 2) if rp else None
        S[f"rows_per_run_{a}"] = {
            "placebo": [r["rows"] for r in rc],
            "planted": [r["rows"] for r in rp],
        }
        S[f"placebo_pending_{a}"] = cnt(rc, "PENDING")
    S["count_mismatch_runs"] = [r["run"] for r in res["A"] if r["count_mismatch"]]
    if not fail and any(S[f"placebo_pending_{a}"] for a in ARMS):
        fail_fp = "placebo findings still pending adjudication; FP criterion not computable"
        S["verdict"], S["verdict_text"] = "UNDECIDED_PENDING_ADJUDICATION", [fail_fp]
    else:
        S["verdict"], S["verdict_text"] = verdict(S)
    extra = []
    if not fail:
        if S["qual_recall"]["G"] is not None and S["qual_recall"]["G"] >= T_G_HIGH:
            extra.append(
                "The wave-2 blind spot did not reproduce on fresh plants: the generic brief caught "
                f"{S['qual_counts']['G']} deleted qualifiers here (recall {S['qual_recall']['G']}), so the "
                "wave-2 0-of-12 may not generalise beyond that corpus."
            )
        oQ, oG = S["other_recall"]["Q"], S["other_recall"]["G"]
        if oQ is not None and oG is not None and oQ < oG - T_OTHER_DROP:
            extra.append(
                f"The qualifier procedure lost recall on the other defect classes ({oQ} vs {oG})."
            )
        extra.append(
            f"On the unmodified placebo copy, verifiers reported {S['fp_upper']['Q']} (Q) vs "
            f"{S['fp_upper']['G']} (G) false findings per run counting unresolved "
            f"(FP only: {S['fp_lower']['Q']} vs {S['fp_lower']['G']})."
        )
    extra.append(
        f"This tests one procedure on one document set, with {S['qual_distinct_plants']} distinct "
        "deleted-qualifier plants and 2 runs per copy per arm; it is not a general claim about AI verification."
    )
    S["verdict_text"] = S["verdict_text"] + extra
    return res


# ------------------------------------------------------------------ self-test (synthetic key only)
SYN_REPORT = """<html><body><h2>1. Intro</h2>
<p>The alpha method cuts the error 999× at small size. The beta method runs in 5 s at all sizes.</p>
<p>We saw 12 of 12 points inside the bracket. The gamma oracles exist at scale.</p>
<p>The delta error is 0.03 in every setting.</p>
</body></html>
"""
SYN_FORM = (
    "# Form\n\n## Project abstract\n\nThe epsilon estimate is 0.500 in the tracker.\n\n## Related\n"
)
SYN_KIT = "# Kit\n\nThe epsilon estimate is 0.500 in the tracker.\n"


def _syn_key():
    def pl(pid, grp, doc, sent, pats):
        return {
            "id": pid,
            "group": grp,
            "cls": "dropped_qualifier" if grp == "qualifier" else "wrong_number",
            "restriction": "r",
            "cross_doc_tell": False,
            "auto_patterns": pats,
            "locations": [{"doc": doc, "sentence_norm": sent}],
        }

    return {
        "copies": {
            "A": {
                "kind": "planted",
                "plants": [
                    pl(
                        "N1",
                        "other",
                        "report",
                        "The alpha method cuts the error 999x at small size.",
                        [r"\b235\b"],
                    ),
                    pl(
                        "Q1",
                        "qualifier",
                        "report",
                        "The beta method runs in 5 s at all sizes.",
                        [r"small sizes? only"],
                    ),
                    pl(
                        "Q2",
                        "qualifier",
                        "report",
                        "The gamma oracles exist at scale.",
                        [r"planned"],
                    ),
                    pl(
                        "Q3",
                        "qualifier",
                        "report",
                        "The delta error is 0.03 in every setting.",
                        [r"only at (chi|χ) ?= ?64"],
                    ),
                ],
            },
            "B": {
                "kind": "planted",
                "plants": [
                    pl(
                        "Q4",
                        "qualifier",
                        "form",
                        "The epsilon estimate is 0.500 in the tracker.",
                        [r"post[- ]?hoc"],
                    ),
                ],
            },
            "C": {"kind": "placebo", "plants": []},
        }
    }


HDR = "| # | file:line | quote | type | what is wrong | source | correct |\n|---|---|---|---|---|---|---|\n"
SYN_G = (
    HDR
    + """| 1 | report/report.html:2 | "cuts the error 999× at small size" | WRONG | ratio is wrong | results/x.json | 235 |
| 2 | report/report.html:2 | "The beta method runs in 5 s at all sizes" | OVERSTATED | untested claim about timing | y | fine |
| 3 | report/report.html:3 | "We saw 12 of 12 points inside the bracket" | OVERSTATED | gamma oracles are only planned | form | planned |
| 4 | report/report.html:2 | "The alpha method cuts the error 999x" | WRONG | duplicate of 1 | results/x.json | 235 |
| 5 | report/report.html:3 | "We saw 12 of 12 points inside the bracket" | WRONG | should be 11 of 12 | z | 11/12 |
FINDINGS=5
"""
)
SYN_Q = (
    HDR
    + """| 1 | report/report.html:2 | "The beta method runs in 5 s at all sizes" | OVERSTATED | holds for small sizes only | y | small sizes only |
| 2 | report/report.html:3 | "The gamma oracles exist at scale" | OVERSTATED | they are planned, not built | form | planned |
| 3 | report/report.html:4 | "The delta error is 0.03 in every setting" | OVERSTATED | missing restriction: out of how many instances | d | n/a |
| 4 | report/report.html:4 | "The delta error is 0.03 in every setting" | OVERSTATED | holds only at chi = 64 | d | at chi=64 |
FINDINGS=4
"""
)
SYN_QB = (
    HDR
    + """| 1 | FORM_ANSWERS.md:5 | "The epsilon estimate is 0.500 in the tracker" | OVERSTATED | exploratory post hoc label missing | p | post hoc |
FINDINGS=1
"""
)
SYN_PLACEBO = (
    HDR
    + """| 1 | report/report.html:2 | "The beta method runs in 5 s at all sizes" | OVERSTATED | x | y | z |
| 2 | report/report.html:3 | "We saw 12 of 12 points inside the bracket" | WRONG | x | y | z |
FINDINGS=2
"""
)


def _write_corpus(td):
    for lab in ("A", "B", "C"):
        for d, txt in (("report", SYN_REPORT), ("form", SYN_FORM), ("kit", SYN_KIT)):
            f = td / "corpus" / f"copy_{lab}" / DOCS[d]
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(txt)


def _segs(td, lab):
    return {
        d: segments((td / "corpus" / f"copy_{lab}" / p).read_text(), d == "report")
        for d, p in DOCS.items()
    }


def _full_reports(rep, missing_q_planted=0):
    rep.mkdir(exist_ok=True)
    for r in (1, 2):
        (rep / f"A_G_run{r}.md").write_text(SYN_G)
        (rep / f"B_G_run{r}.md").write_text(HDR + "FINDINGS=0\n")
        (rep / f"C_G_run{r}.md").write_text(SYN_PLACEBO)
        (rep / f"C_Q_run{r}.md").write_text(SYN_PLACEBO)
    for i, (lab, r) in enumerate((("A", 1), ("A", 2), ("B", 1), ("B", 2))):
        name = f"{lab}_Q_run{r}"
        if i < missing_q_planted:
            (rep / f"{name}.MISSING").write_text("")
        else:
            (rep / f"{name}.md").write_text(SYN_Q if lab == "A" else SYN_QB)


def self_test(verbose=True):
    ok = True

    def expect(name, cond):
        nonlocal ok
        if verbose:
            print(("PASS " if cond else "FAIL ") + name)
        ok &= bool(cond)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        _write_corpus(td)
        key = _syn_key()
        pA = key["copies"]["A"]["plants"]
        segs = _segs(td, "A")
        expect(
            "synthetic sentences are segments",
            all(
                L["sentence_norm"] in _segs(td, lab)[L["doc"]]
                for lab in ("A", "B")
                for p in key["copies"][lab]["plants"]
                for L in p["locations"]
            ),
        )
        r0 = score_run("A_G_run1", SYN_G, pA, segs, {})
        st = {fid: s for fid, s, _ in r0["findings"]}
        expect(
            "auto hit on N1 (right sentence, right problem)",
            "N1" in r0["hits"] and st["A_G_run1#1"] == "AUTO_HIT",
        )
        expect("duplicate credited once, not a false positive", st["A_G_run1#4"] == "DUPLICATE")
        expect(
            "right sentence, wrong problem -> NEEDS_ADJ, not a hit",
            st["A_G_run1#2"] == "NEEDS_ADJ" and "Q1" not in r0["hits"],
        )
        expect(
            "MUTATION: correct problem, wrong sentence quoted -> not a hit",
            "Q2" not in r0["hits"] and st["A_G_run1#3"] == "NON_PLANT",
        )
        expect(
            "adjudication cannot rescue a wrong-sentence quote",
            "Q2"
            not in score_run(
                "A_G_run1", SYN_G, pA, segs, {"A_G_run1#3": {"verdict": "HIT", "plant": "Q2"}}
            )["hits"],
        )
        rq = score_run("A_Q_run1", SYN_Q, pA, segs, {})
        sq = {fid: s for fid, s, _ in rq["findings"]}
        expect(
            "WRONG-RESTRICTION control: a different restriction on the plant sentence is not an auto hit",
            sq["A_Q_run1#3"] == "NEEDS_ADJ",
        )
        expect(
            "the right restriction on the same sentence is an auto hit (after the wrong one)",
            sq["A_Q_run1#4"] == "AUTO_HIT" and "Q3" in rq["hits"],
        )
        expect("Q-style findings hit Q1, Q2, Q3", rq["hits"] == ["Q1", "Q2", "Q3"])
        r5 = score_run(
            "A_G_run1",
            SYN_G,
            pA,
            segs,
            {"A_G_run1#1": {"verdict": "MISS"}, "A_G_run1#4": {"verdict": "MISS"}},
        )
        expect(
            "independent adjudicator can overrule an auto hit",
            "N1" not in r5["hits"] and len(r5["auto_hits_overruled"]) == 2,
        )
        expect(
            "FINDINGS mismatch flagged",
            score_run("A_G_run1", SYN_G.replace("FINDINGS=5", "FINDINGS=7"), pA, segs, {})[
                "count_mismatch"
            ],
        )
        expect(
            "arm parsed from run id",
            arm_of("B_Q_run2") == ("B", "Q") and arm_of("B_run2") == (None, None),
        )

        rep = td / "reports"
        _full_reports(rep)
        adj = {
            f"A_G_run{r}#{n}": v
            for r in (1, 2)
            for n, v in (
                (2, {"verdict": "MISS", "np_verdict": "FP"}),
                (3, {"verdict": "FP"}),
                (5, {"verdict": "PREEXISTING", "defect_id": "d1"}),
            )
        }
        adj.update(
            {
                f"A_Q_run{r}#3": {"verdict": "MISS", "np_verdict": "PREEXISTING", "defect_id": "d2"}
                for r in (1, 2)
            }
        )
        adj.update(
            {f"C_{a}_run{r}#{n}": {"verdict": "FP"} for a in ARMS for r in (1, 2) for n in (1, 2)}
        )
        full = run(key, td / "corpus", rep, adj)
        S = full["summary"]
        expect(
            "arms scored separately: qualifier recall G 0/8, Q 8/8",
            S["qual_counts"] == {"G": "0/8", "Q": "8/8"},
        )
        expect("other-class recall G 2/2, Q 0/2", S["other_counts"] == {"G": "2/2", "Q": "0/2"})
        expect(
            "paired bootstrap diff CI brackets the point estimate",
            S["qual_diff_ci"] is not None
            and S["qual_diff"] is not None
            and S["qual_diff_ci"][0] <= S["qual_diff"] <= S["qual_diff_ci"][1],
        )
        expect("placebo false findings per run: 2.0 per arm", S["fp_upper"] == {"G": 2.0, "Q": 2.0})
        expect("verdict CLOSES on the synthetic data", S["verdict"] == "CLOSES")
        expect(
            "other-class drop sentence present",
            any("lost recall on the other" in t for t in S["verdict_text"]),
        )
        # pending placebo items block the FP criterion
        adj_p = {k: v for k, v in adj.items() if not k.startswith("C_Q_run1")}
        expect(
            "pending placebo findings -> UNDECIDED",
            run(key, td / "corpus", rep, adj_p)["summary"]["verdict"]
            == "UNDECIDED_PENDING_ADJUDICATION",
        )
        # missing-run rule
        rep2 = td / "reports2"
        _full_reports(rep2, missing_q_planted=2)
        S2 = run(key, td / "corpus", rep2, adj)["summary"]
        expect(
            "MISSING rule: 2 of 4 Q planted runs -> instrument failure",
            S2["verdict"] == "INSTRUMENT_FAILURE"
            and S2["runs_missing_Q"] == ["A_Q_run1", "A_Q_run2"],
        )
        rep3 = td / "reports3"
        _full_reports(rep3, missing_q_planted=1)
        expect(
            "MISSING rule: 3 of 4 Q planted runs is still valid",
            run(key, td / "corpus", rep3, adj)["summary"]["verdict"] != "INSTRUMENT_FAILURE",
        )

    # verdict rule, all branches (synthetic statistics)
    def V(qQ, qG, lb, fpQ, fpG, qQh=None, qGh=None, lbh=None):
        S = {
            "instrument_failure": [],
            "qual_recall": {"Q": qQ, "G": qG},
            "qual_diff_ci": (lb, 1),
            "qual_recall_pending_hit": {
                "Q": qQ if qQh is None else qQh,
                "G": qG if qGh is None else qGh,
            },
            "qual_diff_ci_pending_hit": (lb if lbh is None else lbh, 1),
            "fp_upper": {"Q": fpQ, "G": fpG},
        }
        return verdict(S)[0]

    expect("verdict: closes", V(0.6, 0.1, 0.2, 8, 4) == "CLOSES")
    expect(
        "verdict: FP margin boundary (Q = G + 5) still closes", V(0.6, 0.1, 0.2, 9, 4) == "CLOSES"
    )
    expect("verdict: FP cost", V(0.6, 0.1, 0.2, 9.5, 4) == "RECALL_GAIN_AT_FP_COST")
    expect("verdict: partial gain (Q < 0.5)", V(0.45, 0.1, 0.1, 4, 4) == "PARTIAL_GAIN")
    expect(
        "verdict: gain not demonstrated (LB <= 0)",
        V(0.6, 0.2, 0.0, 4, 4) == "GAIN_NOT_DEMONSTRATED",
    )
    expect("verdict: no improvement (diff < 0.3)", V(0.6, 0.35, 0.05, 4, 4) == "NO_IMPROVEMENT")
    expect("verdict: no improvement when Q is worse", V(0.1, 0.4, -0.5, 4, 4) == "NO_IMPROVEMENT")
    expect(
        "verdict: pending changes outcome -> UNDECIDED",
        V(0.4, 0.1, 0.1, 4, 4, qQh=0.6) == "UNDECIDED_PENDING_ADJUDICATION",
    )
    expect(
        "verdict: instrument failure short-circuits",
        verdict({"instrument_failure": ["x"]})[0] == "INSTRUMENT_FAILURE",
    )
    if verbose:
        print("SELF-TEST " + ("OK" if ok else "FAILED"))
    return ok


def mutation_test():
    """Each mutant neutralises one mechanism; the self-test must turn red for every one."""
    g = globals()
    mutants = {}

    def m_location():  # drop the maximal-match location rule: every finding locates every plant in its doc
        orig = g["located_plants"]
        g["located_plants"] = lambda f, segs, plants: (sorted(p["id"] for p in plants), False)
        return lambda: g.__setitem__("located_plants", orig)

    def m_pool_arms():  # arms not separated
        orig = g["arm_of"]
        g["arm_of"] = lambda rid: (orig(rid)[0], "G" if orig(rid)[0] else None)
        return lambda: g.__setitem__("arm_of", orig)

    def m_ignore_fp():  # FP condition ignored
        orig = g["T_FP_MARGIN"]
        g["T_FP_MARGIN"] = 1e9
        return lambda: g.__setitem__("T_FP_MARGIN", orig)

    def m_ignore_lb():  # bootstrap lower bound ignored
        orig = g["verdict"]

        def v(S):
            S = dict(S)
            S["qual_diff_ci"] = (1, 1)
            S["qual_diff_ci_pending_hit"] = (1, 1)
            return orig(S)

        g["verdict"] = v
        return lambda: g.__setitem__("verdict", orig)

    def m_missing_ignored():  # MISSING runs silently dropped
        orig = g["MIN_PLANTED_RUNS"]
        g["MIN_PLANTED_RUNS"] = 0
        return lambda: g.__setitem__("MIN_PLANTED_RUNS", orig)

    for name, mk in (
        ("location", m_location),
        ("pool_arms", m_pool_arms),
        ("ignore_fp", m_ignore_fp),
        ("ignore_bootstrap_lb", m_ignore_lb),
        ("missing_ignored", m_missing_ignored),
    ):
        undo = mk()
        try:
            red = not self_test(verbose=False)
        except Exception as e:  # a crash also counts as the mutant being detected
            red = True
            name += f" (crashed: {type(e).__name__})"
        finally:
            undo()
        mutants[name] = red
        print(("KILLED " if red else "SURVIVED ") + name)
    clean_ok = self_test(verbose=False)
    print("unmutated self-test:", "OK" if clean_ok else "FAILED")
    ok = clean_ok and all(mutants.values())
    print("MUTATION TEST " + ("OK" if ok else "FAILED"))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--mutation-test", action="store_true")
    ap.add_argument("--key")
    ap.add_argument("--corpus")
    ap.add_argument("--reports")
    ap.add_argument("--adjudication")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(0 if self_test() else 1)
    if a.mutation_test:
        sys.exit(0 if mutation_test() else 1)
    key = json.loads(Path(a.key).read_text())
    adj = json.loads(Path(a.adjudication).read_text()) if a.adjudication else {}
    res = run(key, Path(a.corpus), Path(a.reports), adj)
    for r in res["A"]:
        print(
            f"{r['run']} ({r['kind']}): rows={r['rows']} declared={r['declared']} hits={r['hits']} "
            f"pending={r['pending_plants']} dup={len(r['duplicates'])} nonplant={len(r['non_plant'])}"
        )
        for fid, s, pid in r["findings"]:
            if s in ("NEEDS_ADJ", "NON_PLANT") and not any(
                f == fid and v != "PENDING" for f, v, _d in r["non_plant"]
            ):
                print(f"   ADJUDICATE {fid}: {s} {pid or ''}")
    for mm in res["missing"]:
        print(f"MISSING {mm['run']}")
    print(json.dumps(res["summary"], indent=1, ensure_ascii=False))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
