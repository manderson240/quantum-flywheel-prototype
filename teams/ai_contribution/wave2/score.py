import sys

m = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1])
sys.exit(f"MemAvailable {m / 2**20:.1f} GiB < 20") if m < 20 * 2**20 else None
"""Scorer for the planted-defect benchmark (frozen rule: PREREG.md sections 5-7).

  python3 score.py --self-test
  python3 score.py --key SEALED/key.json --corpus corpus --reports <dir> [--adjudication adj.json]
                   [--armB <dir>] [--out score.json]

<dir> holds arm-A verifier reports named <LABEL>_run<r>.md (LABEL in A-D).
<armB dir> holds run_armB.py stdout: baseline.txt (originals) and <LABEL>.txt per copy.
Prints plant ids and aggregates only, never plant texts.
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
MIN_QUOTE = 8
# Empirical class counts of text defects in graph/lessons.json, snapshot D01-D71 (2026-09-26), restricted to
# the 9 classes this benchmark plants. Used for the pre-registered post-stratified (class-reweighted) recall.
EMPIRICAL = {"wrong_number": 7, "scope_overreach": 6, "dropped_qualifier": 6, "overgeneralization": 6,
             "favorable_reading": 5, "citation_overreach": 4, "cross_document_inconsistency": 4,
             "stale_count": 3, "hidden_denominator": 2}


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
    """Return (doc->set of best segments, best lcs, ambiguous) for a finding's quote."""
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


def score_run(run_id, text, plants, segs, adj):
    rows, declared = parse_report(text)
    hit, dup, out, non_plant, pending_plants = {}, [], [], [], set()
    overruled = []
    for f in rows:
        fid = f"{run_id}#{f['n']}"
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
        cand = auto
        status = "AUTO_HIT"
        if auto and a.get("verdict") == "MISS":  # independent adjudicator overrules an auto hit (PREREG 5)
            overruled.append(fid)
            auto = []
        if not auto:
            if a.get("verdict") == "HIT" and a.get("plant") in locp:
                cand, status = [a["plant"]], "ADJ_HIT"
            elif a.get("verdict") in ("MISS", "PREEXISTING", "FP", "UNRESOLVED"):
                non_plant.append(
                    (
                        fid,
                        a.get("verdict")
                        if a.get("verdict") != "MISS"
                        else a.get("np_verdict", "PENDING"),
                        a.get("defect_id"),
                    )
                )
                out.append((fid, "ADJ_MISS", locp))
                continue
            else:
                pending_plants.update(locp)
                out.append((fid, "NEEDS_ADJ", locp))
                continue
        new = [pid for pid in cand if pid not in hit]
        if new:
            hit[new[0]] = fid
            out.append((fid, status, new[0]))  # one finding credits at most one plant
        else:
            dup.append(fid)
            out.append((fid, "DUPLICATE", cand[0]))
    miss = [p["id"] for p in plants if p["id"] not in hit and p["id"] not in pending_plants]
    pend = sorted(pending_plants - set(hit))
    return {
        "run": run_id,
        "rows": len(rows),
        "declared": declared,
        "count_mismatch": declared is None or declared != len(rows),
        "auto_hits_overruled": overruled,
        "hits": sorted(hit),
        "misses": sorted(miss),
        "pending_plants": pend,
        "duplicates": dup,
        "non_plant": non_plant,
        "findings": out,
    }


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round((c - r) / d, 3), round((c + r) / d, 3))


def cluster_bootstrap(runsP, plants, B=2000, seed=20260927):
    """Percentile CI for pooled recall, resampling UNIQUE plants (clusters) with replacement; each cluster
    carries all its plant-runs across copies and runs (PREREG 8: plant-runs are not independent)."""
    import random as _r
    cl = {}
    for r in runsP:
        for p in plants[r["label"]]:
            c = cl.setdefault(p["id"], [0, 0]); c[1] += 1; c[0] += p["id"] in r["hits"]
    ids = sorted(cl)
    if not ids:
        return None
    rng = _r.Random(seed); est = []
    for _ in range(B):
        smp = [cl[rng.choice(ids)] for _ in ids]
        est.append(sum(k for k, _ in smp) / sum(n for _, n in smp))
    est.sort()
    return (round(est[int(0.025 * B)], 3), round(est[int(0.975 * B) - 1], 3))


def chapman(n1, n2, m):
    """Chapman's bias-corrected Lincoln-Petersen estimate, Seber variance, normal 95% CI floored at the
    observed distinct count. Assumes equal catchability; heterogeneity biases it LOW (PREREG sec. 8)."""
    N = (n1 + 1) * (n2 + 1) / (m + 1) - 1
    var = (n1 + 1) * (n2 + 1) * (n1 - m) * (n2 - m) / ((m + 1) ** 2 * (m + 2))
    sd = math.sqrt(var)
    seen = n1 + n2 - m
    return {"n1": n1, "n2": n2, "m": m, "observed_distinct": seen, "N_hat": round(N, 2),
            "ci95": (round(max(seen, N - 1.96 * sd), 2), round(N + 1.96 * sd, 2)),
            "unfound_hat": round(N - seen, 2), "m_zero_unstable": m == 0}


def _runno(r):
    d = re.sub(r"\D", "", r["run"].split("run")[-1])
    return int(d) if d else 0


def capture_recapture(res, plants):
    """Two-sample estimate from the first two runs (by run number) of each copy."""
    out = {"placebo": None, "calibration_on_planted": {}}
    byl = {}
    for r in res["A"]:
        byl.setdefault(r["label"], []).append(r)
    for lab, rs in sorted(byl.items()):
        rs = sorted(rs, key=_runno)[:2]
        if len(rs) < 2:
            continue
        if rs[0]["kind"] == "placebo":
            ids = [{d for _, v, d in r["non_plant"] if v == "PREEXISTING" and d} for r in rs]
            out["placebo"] = chapman(len(ids[0]), len(ids[1]), len(ids[0] & ids[1]))
        else:
            h = [set(r["hits"]) for r in rs]
            c = chapman(len(h[0]), len(h[1]), len(h[0] & h[1]))
            c["true_N"] = len(plants[lab])
            out["calibration_on_planted"][lab] = c
    return out


def parse_armB(text):
    res = {}
    for line in text.splitlines():
        mm = re.match(r"^(PASS|FAIL) (.*?)(  -> .*)?$", line)
        if mm:
            res[mm.group(2)] = mm.group(1)
    valid = len(res) >= 100 and ("ALL CLAIMS VERIFIED" in text or "FAILED:" in text)
    return res, valid


def score_armB(base_txt, lab_txt, plants):
    b, vb = parse_armB(base_txt)
    c, vc = parse_armB(lab_txt)
    flips = sorted(n for n, s in c.items() if s == "FAIL" and b.get(n) == "PASS")
    hits = sorted(p["id"] for p in plants if set(p.get("armB_checks", [])) & set(flips))
    credited = {n for p in plants for n in p.get("armB_checks", [])}
    incidental = [n for n in flips if n == "abstract ~350 words"]
    unexpected = [n for n in flips if n not in credited and n not in incidental]
    return {
        "valid": vb and vc,
        "flips": flips,
        "hits": hits,
        "incidental": incidental,
        "unexpected": unexpected,
        "baseline_fails": sorted(n for n, s in b.items() if s == "FAIL"),
    }


def load_segs(copy_dir):
    return {d: segments((copy_dir / p).read_text(), d == "report") for d, p in DOCS.items()}


def run(key, corpus, reports, adj, armB):
    res = {"A": [], "B": {}, "summary": {}}
    for lab, c in sorted(key["copies"].items()):
        segs = load_segs(corpus / f"copy_{lab}")
        for rp in sorted(reports.glob(f"{lab}_run*.md")):
            r = score_run(rp.stem, rp.read_text(), c["plants"], segs, adj)
            r["label"], r["kind"] = lab, c["kind"]
            res["A"].append(r)
        if armB:
            bt = armB / "baseline.txt"
            lt = armB / f"{lab}.txt"
            if bt.exists() and lt.exists():
                res["B"][lab] = score_armB(bt.read_text(), lt.read_text(), c["plants"])
                res["B"][lab]["kind"] = c["kind"]
    plants = {lab: c["plants"] for lab, c in key["copies"].items()}
    runsP = [r for r in res["A"] if r["kind"] == "planted"]
    runsC = [r for r in res["A"] if r["kind"] == "placebo"]
    n = sum(len(plants[r["label"]]) for r in runsP)
    k = sum(len(r["hits"]) for r in runsP)
    pend = sum(len(r["pending_plants"]) for r in runsP)
    S = res["summary"]
    S["A_plant_runs"] = n
    S["A_hits"] = k
    S["A_recall"] = round(k / n, 3) if n else None
    S["A_recall_wilson95"] = wilson(k, n)
    S["A_pending_plant_runs"] = pend
    S["A_recall_upper_if_pending_hit"] = round((k + pend) / n, 3) if n else None
    for fld in ("stratum", "checker_constant", "cross_doc_tell", "cls"):
        agg = {}
        for r in runsP:
            for p in plants[r["label"]]:
                a = agg.setdefault(str(p[fld]), [0, 0])
                a[1] += 1
                a[0] += p["id"] in r["hits"]
        S[f"A_by_{fld}"] = {g: f"{a[0]}/{a[1]}" for g, a in sorted(agg.items())}
    uniq = {}
    for r in runsP:
        for p in plants[r["label"]]:
            uniq.setdefault(p["id"], False)
            uniq[p["id"]] |= p["id"] in r["hits"]
    S["A_unique_plants_caught_any_run"] = f"{sum(uniq.values())}/{len(uniq)}"
    S["A_auto_hits_overruled"] = sum(len(r["auto_hits_overruled"]) for r in runsP)
    S["A_recall_cluster_bootstrap95"] = cluster_bootstrap(runsP, plants)
    cnt = lambda rs, v: sum(1 for r in rs for _, s, _d in r["non_plant"] if s == v)
    for name, rs in (("planted_copies", runsP), ("placebo", runsC)):
        S[f"nonplant_{name}"] = {
            v: cnt(rs, v) for v in ("PREEXISTING", "FP", "UNRESOLVED", "PENDING")
        }
        S[f"runs_{name}"] = len(rs)
    if runsC:
        S["placebo_FP_per_run_lower"] = round(cnt(runsC, "FP") / len(runsC), 2)
        S["placebo_FP_per_run_upper"] = round(
            (cnt(runsC, "FP") + cnt(runsC, "UNRESOLVED")) / len(runsC), 2
        )
    S["count_mismatch_runs"] = [r["run"] for r in res["A"] if r["count_mismatch"]]
    S["capture_recapture"] = capture_recapture(res, plants)
    cls = {}
    for r in runsP:
        for p in plants[r["label"]]:
            c = cls.setdefault(p["cls"], [0, 0]); c[1] += 1; c[0] += p["id"] in r["hits"]
    wsum = sum(EMPIRICAL.get(c, 0) for c in cls)
    S["A_recall_poststratified"] = (round(sum(EMPIRICAL.get(c, 0) / wsum * k_ / n_ for c, (k_, n_) in cls.items()), 3)
                                    if wsum else None)
    if res["B"]:
        bP = [v for v in res["B"].values() if v["kind"] == "planted"]
        nb = sum(len(plants[lab]) for lab, v in res["B"].items() if v["kind"] == "planted")
        kb = sum(len(v["hits"]) for v in bP)
        S["B_hits"] = kb
        S["B_plants"] = nb
        S["B_recall"] = round(kb / nb, 3) if nb else None
        S["B_recall_wilson95"] = wilson(kb, nb)
        S["B_all_valid"] = all(v["valid"] for v in res["B"].values())
        S["B_placebo_flips"] = sum(
            len(v["flips"]) for v in res["B"].values() if v["kind"] == "placebo"
        )
        S["B_unexpected_flips"] = sum(len(v["unexpected"]) for v in res["B"].values())
    return res


# ------------------------------------------------------------------ self-test (synthetic key only)
SYN_REPORT = """<html><body><h2>1. Intro</h2>
<p>The alpha method cuts the error 999× at small size. The beta method runs in 5 s at all sizes.</p>
<p>We saw 12 of 12 points inside the bracket. The gamma result is planned, and gamma oracles exist at scale.</p>
</body></html>
"""
SYN_FORM = (
    "# Form\n\n## Project abstract\n\nThe delta estimate is 0.500 in the tracker.\n\n## Related\n"
)
SYN_KIT = "# Kit\n\nThe delta estimate is 0.500 in the tracker.\n"


def _syn_key():
    def pl(pid, doc, sent, pats, armB=()):
        return {
            "id": pid,
            "stratum": "S",
            "cls": "c",
            "checker_constant": False,
            "cross_doc_tell": False,
            "auto_patterns": pats,
            "armB_checks": list(armB),
            "locations": [{"doc": doc, "sentence_norm": sent}],
        }

    return {
        "copies": {
            "A": {
                "kind": "planted",
                "plants": [
                    pl(
                        "X1",
                        "report",
                        "The alpha method cuts the error 999x at small size.",
                        [r"\b235\b"],
                    ),
                    pl("X2", "report", "The beta method runs in 5 s at all sizes.", [r"\b21 ?s\b"]),
                    pl(
                        "X3",
                        "report",
                        "The gamma result is planned, and gamma oracles exist at scale.",
                        [r"not (yet )?implemented"],
                    ),
                    pl(
                        "X4",
                        "form",
                        "The delta estimate is 0.500 in the tracker.",
                        [r"0\.187"],
                        armB=["disclosure check"],
                    ),
                ],
            },
            "B": {"kind": "placebo", "plants": []},
        }
    }


SYN_A = """| # | file:line | quote | type | what is wrong | source | correct |
|---|---|---|---|---|---|---|
| 1 | report/report.html:2 | "cuts the error 999× at small size" | WRONG | ratio is wrong | results/x.json | 235 |
| 2 | report/report.html:2 | "The beta method runs in 5 s at all sizes" | OVERSTATED | the phrase 'all sizes' is untested | results/y.json | only small sizes |
| 3 | report/report.html:3 | "We saw 12 of 12 points inside the bracket" | WRONG | gamma oracles are not yet implemented | form | planned |
| 4 | report/report.html:2 | "The alpha method cuts the error 999x" | WRONG | duplicate of 1 | results/x.json | 235 |
| 5 | report/report.html:3 | "We saw 12 of 12 points inside the bracket" | WRONG | should be 11 of 12 | results/z.json | 11/12 |
FINDINGS=5
"""
# X1: auto hit (1), duplicate (4). X2: right sentence, wrong problem -> NEEDS_ADJ, adjudicated MISS.
# X3: finding 3 names X3's problem but quotes the WRONG sentence -> must not hit X3 (mutation test).
# X4: never found -> miss. Finding 5: non-plant, adjudicated FP.
SYN_SPAN = """| # | file:line | quote | type | what is wrong | source | correct |
| 1 | report/report.html:2 | "The alpha method cuts the error 999× at small size. The beta method runs in 5 s at all sizes." | WRONG | ratio should be 235 and time 21 s | r | 235, 21 s |
FINDINGS=1
"""


def self_test():
    ok = True

    def expect(name, cond):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name)
        ok &= bool(cond)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for lab in ("A", "B"):
            for d, txt in (("report", SYN_REPORT), ("form", SYN_FORM), ("kit", SYN_KIT)):
                f = td / "corpus" / f"copy_{lab}" / DOCS[d]
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(txt)
        key = _syn_key()
        rep = td / "reports"
        rep.mkdir()
        (rep / "A_run1.md").write_text(SYN_A)
        (rep / "B_run1.md").write_text(SYN_A.replace("| 1 |", "| 9 |", 0))
        segs = load_segs(td / "corpus" / "copy_A")
        expect(
            "synthetic sentences are segments",
            all(
                L["sentence_norm"] in segs[L["doc"]]
                for p in key["copies"]["A"]["plants"]
                for L in p["locations"]
            ),
        )
        r0 = score_run("A_run1", SYN_A, key["copies"]["A"]["plants"], segs, {})
        st = {fid: s for fid, s, _ in r0["findings"]}
        expect(
            "auto hit on X1 (right sentence, right problem)",
            r0["hits"] == ["X1"] and st["A_run1#1"] == "AUTO_HIT",
        )
        expect(
            "duplicate finding credited once, not a false positive",
            st["A_run1#4"] == "DUPLICATE" and "A_run1#4" not in [f for f, _, _d in r0["non_plant"]],
        )
        expect(
            "right sentence, wrong problem -> NEEDS_ADJ (not a hit)",
            st["A_run1#2"] == "NEEDS_ADJ" and "X2" not in r0["hits"],
        )
        expect(
            "MUTATION: correct problem but wrong sentence quoted -> not a hit",
            "X3" not in r0["hits"] and st["A_run1#3"] == "NON_PLANT",
        )
        expect("unfound plant is a miss", "X4" in r0["misses"] and "X3" in r0["misses"])
        expect("FINDINGS count matches rows", not r0["count_mismatch"])
        adj = {
            "A_run1#2": {"verdict": "MISS", "np_verdict": "PREEXISTING"},
            "A_run1#5": {"verdict": "FP"},
            "A_run1#3": {"verdict": "FP"},
        }
        r1 = score_run("A_run1", SYN_A, key["copies"]["A"]["plants"], segs, adj)
        expect(
            "after adjudication: hits={X1}, misses={X2,X3,X4}",
            r1["hits"] == ["X1"]
            and r1["misses"] == ["X2", "X3", "X4"]
            and not r1["pending_plants"],
        )
        expect(
            "non-plant verdicts recorded",
            sorted(v for _, v, _d in r1["non_plant"]) == ["FP", "FP", "PREEXISTING"],
        )
        bad = {"A_run1#3": {"verdict": "HIT", "plant": "X3"}}
        r2 = score_run("A_run1", SYN_A, key["copies"]["A"]["plants"], segs, bad)
        expect("adjudication cannot rescue a wrong-sentence quote", "X3" not in r2["hits"])
        r3 = score_run("A_run1", SYN_SPAN, key["copies"]["A"]["plants"], segs, {})
        expect(
            "one finding spanning two planted sentences credits at most one plant",
            len(r3["hits"]) <= 1,
        )
        r4 = score_run(
            "A_run1",
            SYN_A.replace("FINDINGS=5", "FINDINGS=7"),
            key["copies"]["A"]["plants"],
            segs,
            {},
        )
        expect("FINDINGS mismatch flagged", r4["count_mismatch"])
        base = "\n".join(
            [f"PASS c{i}" for i in range(120)]
            + ["PASS disclosure check", "PASS abstract ~350 words", "", "ALL CLAIMS VERIFIED"]
        )
        lab = (
            base.replace("PASS disclosure check", "FAIL disclosure check")
            .replace("PASS abstract ~350 words", "FAIL abstract ~350 words  -> x")
            .replace("ALL CLAIMS VERIFIED", "2 FAILED: []")
        )
        b = score_armB(base, lab, key["copies"]["A"]["plants"])
        expect("arm B: flip of a credited check is a hit", b["hits"] == ["X4"] and b["valid"])
        expect(
            "arm B: word-count flip is incidental, not a hit",
            b["incidental"] == ["abstract ~350 words"],
        )
        b2 = score_armB(base, base, key["copies"]["A"]["plants"])
        expect("arm B: no flips -> no hits", b2["hits"] == [] and b2["flips"] == [])
        expect(
            "arm B: truncated output is invalid (A6)", not score_armB(base, "PASS c1", [])["valid"]
        )
        full = run(key, td / "corpus", rep, adj, None)
        expect(
            "aggregate recall 1/4 on synthetic key",
            full["summary"]["A_hits"] == 1 and full["summary"]["A_plant_runs"] == 4,
        )
        expect("wilson interval sane", wilson(1, 4)[0] < 0.25 < wilson(1, 4)[1])
        r5 = score_run("A_run1", SYN_A, key["copies"]["A"]["plants"], segs, {"A_run1#1": {"verdict": "MISS"},
                                                                              "A_run1#4": {"verdict": "MISS"}})
        expect("independent adjudicator can overrule an auto hit", "X1" not in r5["hits"]
               and r5["auto_hits_overruled"] == ["A_run1#1", "A_run1#4"])
        cb = full["summary"]["A_recall_cluster_bootstrap95"]
        expect("cluster bootstrap interval brackets the point estimate", cb[0] <= 0.25 <= cb[1])
        c = chapman(10, 10, 5)
        expect("chapman estimator arithmetic (10,10,5 -> 19.17)", c["N_hat"] == 19.17 and c["observed_distinct"] == 15)
        adj2 = {"B_run1#5": {"verdict": "PREEXISTING", "defect_id": "E1"}, "B_run2#5": {"verdict": "PREEXISTING",
                "defect_id": "E1"}, "B_run2#1": {"verdict": "PREEXISTING", "defect_id": "E2"}}
        (rep / "B_run2.md").write_text(SYN_A)
        cr = run(key, td / "corpus", rep, adj2, None)["summary"]["capture_recapture"]["placebo"]
        expect("placebo capture-recapture uses adjudicated defect ids (n1=1,n2=2,m=1)",
               (cr["n1"], cr["n2"], cr["m"]) == (1, 2, 1))
    print("SELF-TEST " + ("OK" if ok else "FAILED"))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--key")
    ap.add_argument("--corpus")
    ap.add_argument("--reports")
    ap.add_argument("--adjudication")
    ap.add_argument("--armB")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(0 if self_test() else 1)
    key = json.loads(Path(a.key).read_text())
    adj = json.loads(Path(a.adjudication).read_text()) if a.adjudication else {}
    res = run(key, Path(a.corpus), Path(a.reports), adj, Path(a.armB) if a.armB else None)
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
    for lab, v in sorted(res["B"].items()):
        print(
            f"armB {lab} ({v['kind']}): valid={v['valid']} hits={v['hits']} incidental={v['incidental']} "
            f"unexpected={v['unexpected']}"
        )
    print(json.dumps(res["summary"], indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
