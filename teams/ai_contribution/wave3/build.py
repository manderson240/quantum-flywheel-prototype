import sys


m = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1])
sys.exit(f"MemAvailable {m / 2**20:.1f} GiB < 20") if m < 20 * 2**20 else None
"""Qualifier-procedure benchmark builder (team ai_contribution, wave 3).

Question: does a verifier given a qualifier-focused procedure (arm Q) catch deleted qualifiers that the generic
wave-2 brief (arm G) misses? Fresh held-out plants from the CURRENT live application; no wave-2 plant sentence.

Modes:
  --validate    check every pool entry against its source files, the wave-2 exclusion and the brief hashes, and
                build both planted copies IN MEMORY (nothing is written). Run before the PREREG freeze.
  --write-pool  write SEALED/pool.json (its sha256 goes into PREREG).
  --build       requires PREREG.sha16 == frozen PREREG prefix and every frozen hash present in PREREG; writes
                corpus/copy_{A,B,C}, SEALED/key.json, SEALED/assignment.json and SEALED/originals/ (a byte-identical
                snapshot of the unmodified package, for the adjudicators). Refuses to overwrite.
Never prints plant texts; prints ids and counts only.
"""
import difflib
import hashlib
import json
import os
import random
import re
import shutil
from pathlib import Path


ROOT = Path.home() / "cohezion-labs" / "bluequbit-flywheel"
WAVE = ROOT / "teams" / "ai_contribution" / "wave3"
WAVE2 = ROOT / "teams" / "ai_contribution" / "wave2"
SEALED = WAVE / "SEALED"
CORPUS = WAVE / "corpus"
SEED_BASE = 30260927  # new seed family (wave 2 used 20260927 + k)
FIXED_MTIME = 1790000000
DOCS = {"report": "report/report.html", "form": "FORM_ANSWERS.md", "kit": "SUBMISSION_KIT.md"}
FREEZE_MARKER = "## Addendum (written after freeze; excluded from PREREG.sha16)"
WAVE2_BRIEF_SHA256 = "3608302a02c936efedbae79eca4b67aa38c65f699203b31db948193448b1acf6"
N_PLANTED = 2  # planted copies; plus 1 placebo

# Identical to wave 2 (same verifier-visible package layout).
INCLUDE = [
    "report/report.html",
    "FORM_ANSWERS.md",
    "SUBMISSION_KIT.md",
    "results",
    "figures",
    "pilot",
    "pilot2",
    "tracker",
    "teams/rcs/wave2/results",
    "teams/rcs/wave3/results",
    "refs/arXiv2607.24937_excerpts.txt",
    "refs/arXiv2608.13110_abstract.txt",
    "refs/tracker_issue151_excerpt.txt",
    "refs/tracker_issues_20260924.txt",
    "refs/arxiv2607.24937/p.txt",
    "PATCH_PREREG.md",
    "PATCH_PREREG_27CYC.md",
    "RESULT_27CYC.md",
    "RESULT_BIG_INTERIM.md",
    "RESULT_CHI1024.md",
    "DRAFT_PREREG_RCS.md",
    "research/20260925-floquet-decision-path.md",
]
EXCLUDE_NAMES = {"__pycache__"}

# Wave-2 plant spans (the `orig` field of wave-2 build.py POOL, P01..P17 in pool order). Frozen here so this
# file's hash freezes the exclusion set; --validate asserts equality with wave 2's POOL once.
WAVE2_ORIG = [
    "RCM cuts the error 235× at",
    "(5 s vs 21 s)",
    "96 BlueQubit jobs, 0 failures, $0",
    "(2.8σ against the 4-patch estimate)",
    "(5,900–8,400 at 13 cycles)",
    "(3 beyond the 0.005 tolerance)",
    "4-patch (1.999e-3",
    "(planned, not yet implemented) near-Clifford oracles at scale",
    ", which tests the analysis, not hardness",
    " (not in every regime; see the stress test)",
    "removes 83% of it at 27 qubits and 67% at 33 qubits (≤16 cycles), only 39% at 33 qubits and 20–27 cycles.",
    "at 36 cycles only; it does not test other\n  depths, the hardware origin",
    "Fig. 1's gain applies to badly ordered layouts, not that target",
    "and nothing above says MPS will hold at the experiment's full scale",
    "below 95%, so the pre-registered hypothesis is not supported; it passes only if missing points are excluded",
    "positive net and still lost to the rule (CI",
    "0.003 below PEPS-BP's 0.541, a gap we do not interpret",
    "from §5's exact-oracle table",
    "consistent with the bias toward zero in §4.",
    "truncated MPS overestimates in 52 of 53 (one job terminated) and never underestimates",
    "so ⟨M⟩ is underestimated",
    "(~160 H100-hours, arXiv:2608.13110)",
    "Pauli Monte Carlo 0.187, issues",
    "19–33-qubit points with a result (BlueQubit statevector above 19)",
    "arXiv:2607.24937, <b>co-authored by BlueQubit</b>; its own",
]
WAVE2_OVERLAP = (
    20  # a candidate sentence sharing >= min(20, len(span)) chars with any wave-2 span is excluded
)


def P(pid, group, cls, restriction, doc, orig, planted, source, auto, adj, tell, mirror=()):
    return dict(
        id=pid,
        group=group,
        cls=cls,
        restriction=restriction,
        doc=doc,
        orig=orig,
        planted=planted,
        mirror=list(mirror),
        source=list(source),
        auto_patterns=list(auto),
        adj_right_problem=adj,
        cross_doc_tell=tell,
    )


QUAL, OTHER = "qualifier", "other"

POOL = [
    # ---------------- qualifier deletions (primary). Each deletion makes the sentence false or overstated.
    P(
        "Q02",
        QUAL,
        "dropped_qualifier",
        "parameter regime",
        "report",
        "(max error 0.029 at χ = 64)",
        "(max error 0.029)",
        ["results/otoc2_echo_4x4_seeds7-11-13.json"],
        [r"only (at )?(χ|chi) ?= ?64", r"at (χ|chi) ?= ?64", r"0\.8[45]\d?", r"0\.399", r"0\.40\b"],
        "states the 0.029 maximum MPS error holds only at χ = 64 (the maximum over all bond dimensions is ~0.85, at χ = 4); the χ qualifier is missing",
        False,
    ),
    P(
        "Q05",
        QUAL,
        "dropped_qualifier",
        "depth",
        "report",
        "At 1 cycle the bracket is already tight",
        "The bracket is already tight",
        ["results/tracker_floquet51_sweep.json"],
        [r"\b(1|one|first|single) cycle", r"cycle ?1\b", r"0\.35", r"0\.45"],
        "states the bracket is tight only at 1 cycle (at 13-16 cycles it is 0.35-0.45 wide); the depth qualifier is missing",
        False,
    ),
    P(
        "Q07",
        QUAL,
        "dropped_qualifier",
        "post-hoc status",
        "report",
        "<i>Exploratory, post hoc:</i> letting the verifier gate",
        "Letting the verifier gate",
        ["pilot/PILOT_PREREG.md", "pilot/PILOT_PREREG_ADDENDUM.md"],
        [
            r"post[- ]?hoc",
            r"exploratory",
            r"not (part of |in )?(the )?pre-?regist",
            r"not pre-?specified",
        ],
        "states the verifier-gate re-analysis is exploratory / post hoc (it is not in the pilot pre-registration); the status label is missing",
        False,
    ),
    P(
        "Q08",
        QUAL,
        "dropped_qualifier",
        "conditions",
        "report",
        "(Heron; Nighthawk if the program confirms access)",
        "(Heron; Nighthawk)",
        ["FORM_ANSWERS.md"],
        [
            r"confirm",
            r"(unconfirmed|not (yet )?(confirmed|assured|guaranteed))",
            r"defaults? to heron",
            r"if (the program|available)",
            r"premium",
            r"\bflex\b",
        ],
        "states Nighthawk use depends on the program confirming access (availability unconfirmed; the plan defaults to Heron); the condition is missing",
        True,
    ),
    P(
        "Q09",
        QUAL,
        "dropped_qualifier",
        "conditions",
        "form",
        "differ by 4.3σ allowing for circuit scatter;",
        "differ by 4.3σ;",
        ["teams/rcs/wave3/results/gap_d36.json"],
        [
            r"circuit[- ]?(to[- ]circuit )?scatter",
            r"\b5\.8",
            r"shot[- ]noise",
            r"overdispers",
            r"inflat",
        ],
        "states the 4.3σ figure holds only when circuit-to-circuit scatter is allowed for (shot noise alone gives ~5.8σ); the qualifier is missing",
        True,
        mirror=["kit"],
    ),
    P(
        "Q10",
        QUAL,
        "dropped_qualifier",
        "scope",
        "form",
        "2×10⁻⁵, sharing the circuit and observable definitions); above that",
        "2×10⁻⁵); above that",
        ["report/report.html"],
        [
            r"shar\w*.{0,40}definition",
            r"same circuit",
            r"(circuit|observable) definition",
            r"not (fully |completely )?independent",
        ],
        "states the local simulator shares the circuit and observable definitions with BlueQubit's, so it is not fully independent; the qualifier is missing",
        True,
    ),
    P(
        "Q11",
        QUAL,
        "dropped_qualifier",
        "conditions",
        "form",
        "on the current subscription except one approved $0.72 QPU job.",
        "on the current subscription.",
        ["results/bq_jobs.jsonl", "report/report.html"],
        [r"0\.72", r"qpu job", r"not (every|all) .{0,30}\$?0(\.00)?"],
        "states not every prototype run cost $0.00: one approved QPU job cost $0.72; the exception is missing",
        True,
    ),
    P(
        "Q15",
        QUAL,
        "dropped_qualifier",
        "scope",
        "report",
        "3×10<sup>−15</sup> on slices.",
        "3×10<sup>−15</sup>.",
        ["FORM_ANSWERS.md", "SUBMISSION_KIT.md"],
        [r"\bslices?\b", r"not (on )?the full", r"only (on )?(part|small|subset)"],
        "states the agreement with exact simulation was shown only on slices, not on the full instance; the qualifier is missing",
        True,
    ),
    P(
        "Q16",
        QUAL,
        "dropped_qualifier",
        "scope",
        "report",
        "from the raw results (it does not read this text; that the text matches is checked by independent review).</div>",
        "from the raw results.</div>",
        ["SUBMISSION_KIT.md", "FORM_ANSWERS.md"],
        [
            r"(does not|doesn't|never|not) (read|check|verif\w*|parse) (the |this )?(report )?text",
            r"independent review",
            r"text.{0,40}(not|never) (read|checked)",
        ],
        "states check_claims.py does not read the text (text-to-number agreement rests on independent review); the qualifier is missing",
        True,
    ),
    # ---------------- other classes (sanity control): wrong numbers and reference swaps
    P(
        "N01",
        OTHER,
        "wrong_number",
        "-",
        "report",
        "(89 times: 38 right, 51 wrong)",
        "(89 times: 38 right, 57 wrong)",
        ["pilot/results/agents_ollama_tol0.02_B40.0.jsonl"],
        [r"\b51\b", r"38 ?\+ ?57", r"95\b"],
        "states the count is wrong: 38 + 57 != 89; 51 of the 89 disagreement reports were wrong",
        False,
    ),
    P(
        "N02",
        OTHER,
        "wrong_number",
        "-",
        "form",
        "~76× slower than",
        "~67× slower than",
        ["refs/tracker_issues_20260924.txt"],
        [r"\b76\b", r"76\.2", r"66,?325 ?/ ?870"],
        "states the ratio is wrong: 66,325 s / 870 s = ~76x, not ~67x",
        False,
    ),
    P(
        "N03",
        OTHER,
        "wrong_number",
        "-",
        "report",
        "span <b>0.62–0.94</b>",
        "span <b>0.62–0.84</b>",
        ["results/tracker_submissions_2026-09-23.json"],
        [r"0\.94", r"0\.943", r"0\.88\d?"],
        "states the 49x1296 estimates span 0.62-0.94 (BP-TN rescaled 0.943), not 0.62-0.84",
        False,
    ),
    P(
        "C01",
        OTHER,
        "citation_overreach",
        "-",
        "form",
        "(draft\n  pre-registration: DRAFT_PREREG_RCS.md)",
        "(draft\n  pre-registration: PATCH_PREREG.md)",
        ["DRAFT_PREREG_RCS.md", "PATCH_PREREG.md"],
        [r"draft_prereg_rcs", r"patch_prereg.{0,80}(floquet|patch|bracket|not (the )?rcs|wrong)"],
        "states the reference points to the wrong file: the RCS draft pre-registration is DRAFT_PREREG_RCS.md; PATCH_PREREG.md is the Floquet patch pre-registration",
        False,
    ),
    P(
        "C02",
        OTHER,
        "citation_overreach",
        "-",
        "report",
        "Tensor-network Monte Carlo (arXiv:2609.12466;",
        "Tensor-network Monte Carlo (arXiv:2609.05598;",
        ["FORM_ANSWERS.md", "SUBMISSION_KIT.md"],
        [r"2609\.12466", r"2609\.05598.{0,80}(belief|mpbp|matrix-product|\bbp\b|wrong)"],
        "states the arXiv id is wrong: tensor-network Monte Carlo is arXiv:2609.12466; 2609.05598 is matrix-product belief propagation",
        True,
    ),
    P(
        "C03",
        OTHER,
        "citation_overreach",
        "-",
        "report",
        "more accuracy (arXiv:2507.10771);",
        "more accuracy (arXiv:2510.25838);",
        ["FORM_ANSWERS.md"],
        [r"2507\.10771", r"2510\.25838.{0,80}(peaked|wrong)"],
        "states the arXiv id is wrong: the Pauli-path convergence caution is Gharibyan et al., arXiv:2507.10771; 2510.25838 is the peaked-circuits paper",
        True,
    ),
]


# ---------- source validation: each returns (orig_consistent, planted_contradicted, note)
def J(rel):
    return json.loads((ROOT / rel).read_text())


def T(rel):
    return (ROOT / rel).read_text()


def v_Q02():
    d = J("results/otoc2_echo_4x4_seeds7-11-13.json")
    mx = {k: max(abs(r[k] - r["exact"]) for r in d) for k in ("mps_4", "mps_16", "mps_64")}
    return round(mx["mps_64"], 3) == 0.029, max(mx.values()) > 0.1, f"max err {mx}"


def v_Q05():
    w = {}
    for r in J("results/tracker_floquet51_sweep.json"):
        w.setdefault((r["obs"], r["cycles"]), {})[(r["method"][:3], r["setting"])] = r["value"]
    wid = lambda c: max(
        w[(o, c)][("mps", 256)] - w[(o, c)][("pau", 0.0001)] for o in ("mag", "zzd2", "zzd3")
    )
    return (
        wid(1) < 0.02,
        min(wid(13), wid(16)) > 0.3,
        f"width c1={wid(1):.4f} c13={wid(13):.3f} c16={wid(16):.3f}",
    )


def v_Q07():
    pre = T("pilot/PILOT_PREREG.md").lower()
    add = T("pilot/PILOT_PREREG_ADDENDUM.md")
    return (
        "gate" not in pre,
        add.startswith("EXPLORATORY"),
        "gate re-analysis absent from pilot pre-registration",
    )


def v_Q08():
    f = T("FORM_ANSWERS.md")
    return (
        "Nighthawk availability to be confirmed with the program" in f,
        "defaults to Heron" in f,
        "form",
    )


def v_Q09():
    z = J("teams/rcs/wave3/results/gap_d36.json")["mirror_vs_3patch"]["z"]
    return round(z["c_both_inflated"], 1) == 4.3, round(z["a_shot"], 1) != 4.3, f"z {z}"


def v_Q10():
    return (
        "same circuit and observable definitions" in T("report/report.html"),
        True,
        "report states shared definitions",
    )


def v_Q11():
    costs = [
        json.loads(l).get("cost") or 0 for l in T("results/bq_jobs.jsonl").splitlines() if l.strip()
    ]
    nz = [c for c in costs if c]
    return nz == [0.72], sum(nz) > 0, f"nonzero costs {nz}"


def v_Q15():
    return (
        "(validated on slices)" in T("FORM_ANSWERS.md"),
        "(validated on slices)" in T("SUBMISSION_KIT.md"),
        "form+kit",
    )


def v_Q16():
    k = T("SUBMISSION_KIT.md")
    return "it does not read this text" in k, True, "kit states the checker does not read the text"


def v_N01():
    return 38 + 51 == 89, 38 + 57 != 89, "internal sum"


def v_N02():
    t = T("refs/tracker_issues_20260924.txt")
    x = 66325 / 870
    return (
        "#249 66325" in t and "#245 870" in t and round(x) == 76,
        abs(x - 67) > 5,
        f"ratio {x:.1f}",
    )


def v_N03():
    v = [
        s["observableValue"]
        for s in J("results/tracker_submissions_2026-09-23.json")
        if "1296" in s["circuit"]
    ]
    return (round(min(v), 2), round(max(v), 2)) == (0.62, 0.94), max(v) > 0.9, f"{min(v)}-{max(v)}"


def v_C01():
    d, p = T("DRAFT_PREREG_RCS.md"), T("PATCH_PREREG.md")
    return "2609.28657" in d or "RCS" in d, "Floquet" in p or "patch" in p.lower(), "file topics"


def v_C02():
    f = T("FORM_ANSWERS.md")
    return (
        "Goto, Suwa & Todo, arXiv:2609.12466" in f,
        "arXiv:2609.05598) as the BP" in f.replace("\n", " "),
        "form",
    )


def v_C03():
    f = T("FORM_ANSWERS.md")
    return (
        "Gharibyan et al., arXiv:2507.10771 classify Pauli-path" in f,
        "Peaked circuits (arXiv:2510.25838)" in f,
        "form",
    )


VALIDATORS = {k[2:]: v for k, v in globals().items() if k.startswith("v_")}


def validate_entry(p):
    ok_o, ok_p, note = VALIDATORS[p["id"]]()
    for s in p["source"]:
        assert (ROOT / s).exists(), (p["id"], s)
        assert any(s == i or s.startswith(i + "/") for i in INCLUDE), (
            p["id"],
            "source not in corpus",
            s,
        )
    assert ok_o and ok_p, (p["id"], note)
    assert p["orig"].count("\n") == p["planted"].count("\n"), (p["id"], "line count")
    assert p["planted"], (p["id"], "every wave-3 plant has a non-empty planted span")
    return note


# ---------- text normalisation and segmentation (identical to wave 2; shared with score.py)
BLOCK = re.compile(
    r"</?(p|div|td|th|tr|li|br|h1|h2|h3|figcaption|table|ul|figure|title)\b[^>]*>", re.I
)


def norm_doc(text, html):
    if html:
        text = re.sub(r"<(style|script)\b.*?</\1>", " ", text, flags=re.S | re.I)
        text = BLOCK.sub("\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        import html as _h

        text = _h.unescape(text)
    return text


def clean(s):
    import unicodedata

    s = unicodedata.normalize("NFKC", s)
    for a, b in (
        ("−", "-"),
        ("–", "-"),
        ("—", "-"),
        ("×", "x"),
        (" ", " "),
        ("\xa0", " "),
        ("**", ""),
        ("`", ""),
    ):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def segments(text, html):
    t = norm_doc(text, html)
    out = []
    for chunk in re.split(r"\n\s*\n|\n(?=\s*(?:[-*>#|]|\d+\.)\s)", t):
        c = clean(chunk)
        out += [x for x in re.split(r"(?<=[.!?])\s+(?=[A-Z(\[\"“‘])", c) if x.strip()]
    return out


def seg_index(segs, span_clean):
    return [i for i, s in enumerate(segs) if span_clean and span_clean in s]


def lcs(a, b):
    return (
        difflib.SequenceMatcher(None, a, b, autojunk=False)
        .find_longest_match(0, len(a), 0, len(b))
        .size
    )


# ---------- wave-2 exclusion
def check_wave2_constant():
    import importlib.util

    spec = importlib.util.spec_from_file_location("wave2_build", WAVE2 / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert [p["orig"] for p in mod.POOL] == WAVE2_ORIG, "WAVE2_ORIG differs from wave-2 POOL"


def orig_sentence(p):
    html = p["doc"] == "report"
    segs = segments(T(DOCS[p["doc"]]), html)
    idx = seg_index(segs, clean(norm_doc(p["orig"], html)))
    assert len(idx) == 1, (p["id"], "orig sentence count", len(idx))
    return segs[idx[0]]


def wave2_overlap(sentence):
    s = sentence.lower()
    worst = 0
    for w in WAVE2_ORIG:
        wc = clean(norm_doc(w, "<" in w)).lower()
        need = min(WAVE2_OVERLAP, len(wc))
        v = lcs(wc, s)
        if v >= need:
            worst = max(worst, v)
    return worst


# ---------- planting
def plant_docs(originals, plants):
    docs = dict(originals)
    for p in plants:
        for d in [p["doc"]] + p["mirror"]:
            assert docs[d].count(p["orig"]) == 1, (p["id"], d, "orig not unique")
            docs[d] = docs[d].replace(p["orig"], p["planted"])
            assert docs[d].count(p["planted"]) == 1, (p["id"], d, "planted not unique")
    return docs


def plant_sentence(doc_text, html, p):
    segs = segments(doc_text, html)
    idx = seg_index(segs, clean(norm_doc(p["planted"], html)))
    assert len(idx) == 1, (p["id"], "planted sentence count", len(idx))
    return segs[idx[0]]


def select():
    """Deterministic split of the pool into N_PLANTED disjoint planted copies (seed SEED_BASE).
    Qualifier plants are shuffled and dealt round-robin; wrong_number and citation plants likewise, so every copy
    gets at least one of each other class."""
    rng = random.Random(SEED_BASE)
    copies = [[] for _ in range(N_PLANTED)]
    for grp in ("dropped_qualifier", "wrong_number", "citation_overreach"):
        c = sorted([p for p in POOL if p["cls"] == grp], key=lambda p: p["id"])
        rng.shuffle(c)
        start = rng.randrange(N_PLANTED)
        for i, p in enumerate(c):
            copies[(start + i) % N_PLANTED].append(p)
    return copies


def build_copy_texts(plants):
    originals = {d: T(DOCS[d]) for d in DOCS}
    docs = plant_docs(originals, plants)
    recs = []
    for p in plants:
        locs = []
        for d in [p["doc"]] + p["mirror"]:
            html = d == "report"
            sent = plant_sentence(docs[d], html, p)
            pos = docs[d].index(p["planted"])
            line = docs[d][:pos].count("\n") + 1
            locs.append({"doc": d, "path": DOCS[d], "line": line, "sentence_norm": sent})
        r = dict(p)
        r["locations"] = locs
        recs.append(r)
    for d in DOCS:
        assert docs[d].count("\n") == originals[d].count("\n"), (d, "line count")
        assert (ROOT / DOCS[d]).read_bytes() == originals[d].encode("utf-8"), (
            d,
            "original not plain utf-8/LF",
        )
        allowed = {
            L["line"] + i
            for r in recs
            for L in r["locations"]
            if L["doc"] == d
            for i in range(r["orig"].count("\n") + 1)
        }
        changed = {
            i + 1
            for i, (a, b) in enumerate(zip(originals[d].split("\n"), docs[d].split("\n")))
            if a != b
        }
        assert changed <= allowed, (d, "unexpected changed lines", sorted(changed - allowed))
    for r in recs:
        needle = clean(norm_doc(r["orig"], r["doc"] == "report"))
        r["support_file_tell"] = sorted(
            f for f, t in support_texts().items() if needle and needle in t
        )
    return docs, recs


_SUPPORT = {}


def support_texts():
    if not _SUPPORT:
        for inc in INCLUDE:
            src = ROOT / inc
            files = [src] if src.is_file() else [f for f in sorted(src.rglob("*")) if f.is_file()]
            for f in files:
                rel = str(f.relative_to(ROOT))
                if rel in DOCS.values() or any(x in EXCLUDE_NAMES for x in f.parts):
                    continue
                try:
                    t = f.read_text()
                except UnicodeDecodeError:
                    continue
                _SUPPORT[rel] = clean(norm_doc(t, f.suffix == ".html"))
    return _SUPPORT


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frozen_prefix_sha16():
    t = (WAVE / "PREREG.md").read_bytes()
    marker = FREEZE_MARKER.encode()
    i = t.find(marker)
    assert i >= 0, "freeze marker missing"
    return hashlib.sha256(t[: i + len(marker)]).hexdigest()[:16]


def copy_tree(dst):
    for inc in INCLUDE:
        src = ROOT / inc
        if src.is_dir():
            for f in sorted(src.rglob("*")):
                if (
                    any(part in EXCLUDE_NAMES for part in f.relative_to(ROOT).parts)
                    or not f.is_file()
                ):
                    continue
                out = dst / f.relative_to(ROOT)
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(f, out)
        else:
            out = dst / inc
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, out)


def normalise_mtimes(dst):
    for p in sorted(dst.rglob("*"), key=lambda p: -len(p.parts)) + [dst]:
        os.utime(p, (FIXED_MTIME, FIXED_MTIME), follow_symlinks=False)


def pool_payload():
    return {
        "seed_base": SEED_BASE,
        "n_planted": N_PLANTED,
        "pool": POOL,
        "include": INCLUDE,
        "wave2_orig": WAVE2_ORIG,
    }


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--validate"
    check_wave2_constant()
    assert (
        sha(WAVE / "VERIFIER_BRIEF.md") == WAVE2_BRIEF_SHA256 == sha(WAVE2 / "VERIFIER_BRIEF.md")
    ), "G brief not verbatim"
    g, q = (WAVE / "VERIFIER_BRIEF.md").read_text(), (WAVE / "QUALIFIER_BRIEF.md").read_text()
    a, b = q.index("## Required procedure"), q.index("## What counts as a finding")
    assert q[:a] + q[b:] == g, "Q brief must be G plus exactly one inserted section"
    assert len({p["id"] for p in POOL}) == len(POOL)
    sents = {}
    for p in POOL:
        validate_entry(p)
        s = orig_sentence(p)
        ov = wave2_overlap(s)
        assert ov == 0, (p["id"], "shares a sentence with a wave-2 plant", ov)
        for d in p["mirror"]:
            assert T(DOCS[d]).count(p["orig"]) == 1, (p["id"], "mirror", d)
        for d in DOCS:  # any verbatim duplicate of the span must be listed as a mirror
            if d != p["doc"] and d not in p["mirror"]:
                assert p["orig"] not in T(DOCS[d]), (p["id"], "unlisted duplicate in", d)
        key = (p["doc"], s)
        assert key not in sents, (p["id"], "shares a sentence with", sents.get(key))
        sents[key] = p["id"]
        print(f"pool {p['id']} {p['cls']}: source OK, wave-2 overlap 0")
    nq = sum(p["group"] == QUAL for p in POOL)
    print(f"pool: {nq} qualifier plants, {len(POOL) - nq} other plants, all sentences distinct")
    copies = select()
    for k, plants in enumerate(copies, 1):
        docs, recs = build_copy_texts(plants)
        print(f"planted copy {k}: {len(recs)} plants, ids {sorted(r['id'] for r in recs)}")
    if mode == "--validate":
        print("VALIDATE OK (nothing written)")
        return
    if mode == "--write-pool":
        SEALED.mkdir(exist_ok=True)
        (SEALED / "pool.json").write_text(
            json.dumps(pool_payload(), indent=1, ensure_ascii=False) + "\n"
        )
        print("pool sha256", sha(SEALED / "pool.json"))
        return
    if mode == "--build":
        sha16 = (WAVE / "PREREG.sha16").read_text().strip()
        assert frozen_prefix_sha16() == sha16, "PREREG prefix does not match PREREG.sha16"
        prereg = (WAVE / "PREREG.md").read_text()
        for f in (
            "build.py",
            "score.py",
            "VERIFIER_BRIEF.md",
            "QUALIFIER_BRIEF.md",
            "HARNESS_NOTE.md",
            "SEALED/pool.json",
        ):
            assert sha(WAVE / f) in prereg, f"{f} hash not in PREREG"
        assert json.loads((SEALED / "pool.json").read_text()) == json.loads(
            json.dumps(pool_payload(), ensure_ascii=False)
        ), "POOL != pool.json"
        assert not CORPUS.exists(), "corpus exists; refusing to overwrite"
        secret = os.urandom(16).hex()
        labels = ["A", "B", "C"]
        random.Random(secret).shuffle(labels)
        mapping = {labels[i]: f"planted_{i + 1}" for i in range(N_PLANTED)}
        mapping[labels[N_PLANTED]] = "placebo"
        key = {"prereg_sha16": sha16, "seed_base": SEED_BASE, "copies": {}}
        for lab in sorted(mapping):
            dst = CORPUS / f"copy_{lab}"
            copy_tree(dst)
            if mapping[lab] == "placebo":
                key["copies"][lab] = {"kind": "placebo", "plants": []}
                for d in DOCS:
                    assert (dst / DOCS[d]).read_bytes() == (ROOT / DOCS[d]).read_bytes()
            else:
                k = int(mapping[lab].split("_")[1])
                docs, recs = build_copy_texts(copies[k - 1])
                for d in DOCS:
                    (dst / DOCS[d]).write_bytes(docs[d].encode("utf-8"))
                key["copies"][lab] = {"kind": "planted", "copy_index": k, "plants": recs}
            normalise_mtimes(dst)
        normalise_mtimes(CORPUS)
        orig_dst = SEALED / "originals"
        assert not orig_dst.exists()
        copy_tree(orig_dst)
        normalise_mtimes(orig_dst)
        (SEALED / "key.json").write_text(json.dumps(key, indent=1, ensure_ascii=False) + "\n")
        (SEALED / "assignment.json").write_text(
            json.dumps({"secret_seed_hex": secret, "labels": mapping}, indent=1) + "\n"
        )
        n = sum(len(c["plants"]) for c in key["copies"].values())
        print(f"BUILT copies={len(mapping)} planted_total={n}")
        for f in ("key.json", "assignment.json"):
            print(f, sha(SEALED / f))


if __name__ == "__main__":
    main()
