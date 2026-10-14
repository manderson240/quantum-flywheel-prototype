import sys

m = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1])
sys.exit(f"MemAvailable {m / 2**20:.1f} GiB < 20") if m < 20 * 2**20 else None
"""Planted-defect benchmark builder (team ai_contribution, wave 2).

Modes:
  --validate    check every pool entry against its source files and build all planted copies IN MEMORY
                (nothing is written). Run before PREREG freeze.
  --write-pool  write SEALED/pool.json (the catalogue; its sha256 goes into PREREG).
  --build       requires PREREG.sha16 to match the frozen PREREG prefix; writes corpus/copy_{A..D},
                SEALED/key.json and SEALED/assignment.json. Refuses to overwrite an existing corpus.
Never prints key contents (plant texts); prints ids and counts only.
"""
import hashlib
import json
import os
import random
import re
import shutil
import statistics as st
from pathlib import Path


ROOT = Path.home() / "cohezion-labs" / "bluequbit-flywheel"
WAVE = ROOT / "teams" / "ai_contribution" / "wave2"
SEALED = WAVE / "SEALED"
CORPUS = WAVE / "corpus"
SEED_BASE = 20260927
FIXED_MTIME = 1790000000  # one fixed epoch for every file and dir in every copy
DOCS = {"report": "report/report.html", "form": "FORM_ANSWERS.md", "kit": "SUBMISSION_KIT.md"}
FREEZE_MARKER = "## Addendum (written after freeze; excluded from PREREG.sha16)"

# Files a verifier may consult (copied into every corpus copy, byte-identical except the plants).
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

# Strata and per-copy quotas (sum = 12).
QUOTA = [
    ("S01_armB_control", 1),
    ("S02_number_checker_constant", 1),
    ("S03_number_no_constant", 1),
    ("S04_qualifier_deleted", 1),
    ("S05_overgeneralization", 2),
    ("S06_scope_overreach", 1),
    ("S07_favorable_reading", 1),
    ("S08_reference_swap", 1),
    ("S09_direction_flip", 1),
    ("S10_cross_document", 1),
    ("S11_hidden_denominator", 1),
]

COAUTH_CHECK = "report + form disclose BlueQubit co-authorship of the Floquet candidate"


def P(
    pid,
    stratum,
    cls,
    rule,
    doc,
    orig,
    planted,
    source,
    checker_constant,
    auto,
    adj,
    tell,
    mirror=(),
    armB=(),
):
    return dict(
        id=pid,
        stratum=stratum,
        cls=cls,
        rule=rule,
        doc=doc,
        orig=orig,
        planted=planted,
        mirror=list(mirror),
        source=list(source),
        checker_constant=checker_constant,
        auto_patterns=list(auto),
        adj_right_problem=adj,
        cross_doc_tell=tell,
        armB_checks=list(armB),
    )


POOL = [
    P(
        "P01",
        "S02_number_checker_constant",
        "wrong_number",
        "change a number check_claims has a constant for",
        "report",
        "RCM cuts the error 235× at",
        "RCM cuts the error 325× at",
        ["results/mps_ordering_hh3_s5.json"],
        True,
        [r"\b23[56]\b"],
        "states the improvement factor is wrong (0.085/3.6e-4 = 236, i.e. ~235x)",
        False,
    ),
    P(
        "P02",
        "S02_number_checker_constant",
        "wrong_number",
        "change a number check_claims has a constant for",
        "report",
        "(5 s vs 21 s)",
        "(5 s vs 41 s)",
        ["results/mps_ordering_hh3_s5.json"],
        True,
        [r"\b2[01](\.\d)? ?s\b", r"\b20\.8\b", r"\b19\.9\b"],
        "states the index-order wall time is wrong (~21 s), or that 41 s contradicts '~4x faster'",
        False,
    ),
    P(
        "P13",
        "S02_number_checker_constant",
        "stale_count",
        "change a job count check_claims has a constant for",
        "report",
        "96 BlueQubit jobs, 0 failures, $0",
        "84 BlueQubit jobs, 0 failures, $0",
        ["results/tracker_floquet51_sweep.json"],
        True,
        [r"\b96\b"],
        "states the 51-qubit sweep has 96 jobs, not 84",
        False,
    ),
    P(
        "P22",
        "S02_number_checker_constant",
        "wrong_number",
        "change a number check_claims has a constant for",
        "form",
        "(2.8σ against the 4-patch estimate)",
        "(1.8σ against the 4-patch estimate)",
        ["teams/rcs/wave3/results/gap_d36.json"],
        True,
        [r"\b2\.8\b", r"\b2\.7\d"],
        "states the mirror vs 4-patch separation is ~2.8 sigma, not 1.8",
        False,
    ),
    P(
        "P14",
        "S03_number_no_constant",
        "wrong_number",
        "change a number check_claims has no constant for",
        "report",
        "(5,900–8,400 at 13 cycles)",
        "(2,900–4,400 at 13 cycles)",
        [
            "results/tracker_floquet51_sweep.json",
            "results/tracker_floquet51_chi512.json",
            "tracker/README.md",
        ],
        False,
        [r"5[, ]?[89]\d\d", r"8[, ]?4\d\d", r"\b5858\b", r"\b8426\b"],
        "states the 13-cycle re-extrapolated chi range is ~5,900-8,400, not 2,900-4,400",
        False,
    ),
    P(
        "P36",
        "S03_number_no_constant",
        "wrong_number",
        "change a number check_claims has no constant for",
        "report",
        "(3 beyond the 0.005 tolerance)",
        "(1 beyond the 0.005 tolerance)",
        ["results/floquet_oracle19_tx2.4_tz0.9_c5.json"],
        False,
        [
            r"\b3\b.{0,40}(beyond|exceed|toleran|outside)",
            r"(beyond|exceed|toleran|outside).{0,40}\b3\b",
            r"\bthree\b",
        ],
        "states that 3 (not 1) of the 4 MPS-below-truth points exceed the 0.005 tolerance",
        False,
    ),
    P(
        "P53",
        "S03_number_no_constant",
        "wrong_number",
        "change a number check_claims has no constant for",
        "form",
        "4-patch (1.999e-3",
        "4-patch (1.899e-3",
        ["teams/rcs/wave2/results/pooled.json"],
        False,
        [r"1\.999", r"0\.001999", r"1\.9994"],
        "states the pooled 4-patch fidelity is 1.999e-3, not 1.899e-3",
        False,
    ),
    P(
        "P08",
        "S04_qualifier_deleted",
        "dropped_qualifier",
        "delete a scoping qualifier",
        "report",
        "(planned, not yet implemented) near-Clifford oracles at scale",
        "near-Clifford oracles at scale",
        ["FORM_ANSWERS.md"],
        False,
        [
            r"not yet implemented",
            r"\bplanned\b",
            r"not (yet )?(built|implemented|exist)",
            r"(does not|doesn't) (yet )?exist",
        ],
        "states the near-Clifford oracles are planned / not implemented (text now implies they exist)",
        True,
    ),
    P(
        "P20",
        "S04_qualifier_deleted",
        "dropped_qualifier",
        "delete a scoping qualifier",
        "report",
        ", which tests the analysis, not hardness",
        "",
        ["FORM_ANSWERS.md", "SUBMISSION_KIT.md", "teams/rcs/wave2/results/comparison.json"],
        False,
        [r"not hardness", r"hardness", r"analysis pipeline", r"only (tests|checks) the analysis"],
        "states the reproduction tests the analysis pipeline only, not hardness (qualifier missing)",
        True,
    ),
    P(
        "P24",
        "S04_qualifier_deleted",
        "dropped_qualifier",
        "delete a scoping qualifier",
        "form",
        " (not in every regime; see the stress test)",
        "",
        ["results/floquet_oracle19_tx2.4_tz0.9_c5.json", "report/report.html"],
        False,
        [r"not in every regime", r"stress", r"2\.4", r"below (the )?(truth|exact)", r"regime"],
        "states that MPS does not err high in every regime (stress test: MPS below truth at 4 points)",
        False,
    ),
    P(
        "P06",
        "S05_overgeneralization",
        "overgeneralization",
        "generalise a result from 2 of 3 settings",
        "report",
        "removes 83% of it at 27 qubits and 67% at 33 qubits (≤16 cycles), only 39% at 33 qubits and 20–27 cycles.",
        "removes 67–83% of it at both 27 and 33 qubits, at every depth tested.",
        [
            "results/floquet_patch27.json",
            "results/floquet_patch33.json",
            "results/floquet_patch33_27cyc.json",
        ],
        False,
        [r"39\s*%", r"0\.39", r"20.{0,3}27[- ]cycle", r"(not|n't) (at )?every depth", r"deeper"],
        "states the reduction is only ~39% at 33 qubits and 20-27 cycles (not 'every depth')",
        False,
    ),
    P(
        "P21",
        "S05_overgeneralization",
        "overgeneralization",
        "generalise a result beyond the tested depth",
        "form",
        "at 36 cycles only; it does not test other\n  depths, the hardware origin",
        "at every released depth; it does not test\n  the hardware origin",
        ["teams/rcs/wave2/results/per_circuit.json", "teams/rcs/wave2/results/comparison.json"],
        False,
        [
            r"36[- ]cycles? only",
            r"only (at )?(depth|d) ?36",
            r"\bd ?36\b",
            r"only 36",
            r"36 cycles",
        ],
        "states the reproduction covers 36 cycles only, not every released depth",
        False,
    ),
    P(
        "P07",
        "S06_scope_overreach",
        "scope_overreach",
        "extend a result to a target it was shown not to apply to",
        "report",
        "Fig. 1's gain applies to badly ordered layouts, not that target",
        "Fig. 1's gain carries over to that target as well",
        ["pilot2/calibration.json", "FORM_ANSWERS.md"],
        False,
        [
            r"cutwidth",
            r"(does not|doesn't|not|cannot) (apply|carry|transfer)",
            r"badly ordered",
            r"already (has|have)",
        ],
        "states the ordering gain does not transfer: the 51q labels already have RCM's cutwidth (4)",
        True,
    ),
    P(
        "P30",
        "S06_scope_overreach",
        "scope_overreach",
        "extend a small-n result to full scale",
        "report",
        "and nothing above says MPS will hold at the experiment's full scale",
        "and this indicates MPS will hold at the experiment's full scale",
        ["results/tracker_floquet51_chi512.json", "results/otoc2_echo_4x4_seeds7-11-13.json"],
        False,
        [
            r"nothing .{0,30}says",
            r"(does not|doesn't|cannot|not) (indicate|show|support|imply|establish)",
            r"unsupported",
            r"extrapolat",
        ],
        "states a 16-qubit result does not indicate MPS holds at full scale (overreach)",
        False,
    ),
    P(
        "P09",
        "S07_favorable_reading",
        "favorable_reading",
        "turn a failed pre-registered test into a pass",
        "report",
        "below 95%, so the pre-registered hypothesis is not supported; it passes only if missing points are excluded",
        "and since the 3 misses are server terminations rather than bracket failures, the pre-registered hypothesis is supported",
        ["PATCH_PREREG.md", "results/floquet_patch33.json"],
        False,
        [
            r"missing[- ]point rule",
            r"no missing",
            r"not supported",
            r"below 95",
            r"\b83\s*%",
            r"95\s*%",
        ],
        "states that with no pre-registered missing-point rule 15/18 (83%) is below 95%, so not supported",
        False,
    ),
    P(
        "P19",
        "S07_favorable_reading",
        "favorable_reading",
        "misread a confidence interval in the author's favour",
        "report",
        "positive net and still lost to the rule (CI",
        "positive net and was statistically tied with the rule (CI",
        ["pilot/results/score_tol0.02_B40.0.json", "pilot/results/verdict_tol0.02_B40.0.txt"],
        False,
        [
            r"exclud\w* (zero|0)",
            r"-0\.005",
            r"(lost|loses|worse|below) (to )?the rule",
            r"not (statistically )?tied",
            r"significant",
        ],
        "states the CI [-0.200,-0.005] excludes zero, so the agent lost to the rule (not tied)",
        False,
    ),
    P(
        "P29",
        "S07_favorable_reading",
        "favorable_reading",
        "read closeness as convergence",
        "report",
        "0.003 below PEPS-BP's 0.541, a gap we do not interpret",
        "0.003 below PEPS-BP's 0.541, i.e. converged to PEPS-BP",
        ["results/floquet_big_51qx30c.json"],
        False,
        [
            r"closeness is not convergence",
            r"not (evidence of )?converge",
            r"(no|without) pre-?registered",
            r"(does|do) not interpret",
            r"contradict",
        ],
        "states the closeness to PEPS-BP is not evidence of convergence (text contradicts itself)",
        False,
    ),
    P(
        "P11",
        "S08_reference_swap",
        "citation_overreach",
        "swap a section reference",
        "report",
        "from §5's exact-oracle table",
        "from §3's exact-oracle table",
        ["pilot/table.json", "report/report.html"],
        False,
        [r"§ ?5", r"section 5", r"\bs5\b", r"(§ ?3|section 3).{0,60}(ordering|no exact|not)"],
        "states that section 3 has no exact-oracle table; the table is in section 5",
        False,
    ),
    P(
        "P31",
        "S08_reference_swap",
        "citation_overreach",
        "swap a section reference",
        "report",
        "consistent with the bias toward zero in §4.",
        "consistent with the bias toward zero in §6.",
        ["report/report.html"],
        False,
        [r"§ ?4", r"section 4", r"otoc", r"(§ ?6|section 6).{0,60}(pilot|agent|not)"],
        "states section 6 (AI pilot) shows no Pauli-path bias toward zero; the reference should be section 4",
        False,
    ),
    P(
        "P10",
        "S09_direction_flip",
        "wrong_number",
        "flip a comparison direction",
        "report",
        "truncated MPS overestimates in 52 of 53 (one job terminated) and never underestimates",
        "truncated MPS underestimates in 52 of 53 (one job terminated) and never overestimates",
        ["results/floquet_oracle19.json"],
        True,
        [
            r"mps\W+(\w+\W+){0,4}overestimat",
            r"too high",
            r"above (the )?(truth|exact)",
            r"upper (edge|bound)",
            r"(direction|sign) .{0,20}(reversed|flipped|wrong)",
        ],
        "states MPS overestimates (errs high), not underestimates",
        False,
    ),
    P(
        "P32",
        "S09_direction_flip",
        "wrong_number",
        "flip a comparison direction",
        "report",
        "so ⟨M⟩ is underestimated",
        "so ⟨M⟩ is overestimated",
        ["results/kicked_ising_hh3_s5.json"],
        True,
        [
            r"underestimat",
            r"(below|lower than|<=?) (the )?exact",
            r"(direction|sign) .{0,20}(reversed|flipped|wrong)",
        ],
        "states Pauli-path truncation underestimates <M> (pp <= exact), not overestimates",
        False,
    ),
    P(
        "P15",
        "S10_cross_document",
        "cross_document_inconsistency",
        "make form and report disagree",
        "form",
        "(~160 H100-hours, arXiv:2608.13110)",
        "(~260 H100-hours, arXiv:2608.13110)",
        ["refs/arXiv2608.13110_abstract.txt", "report/report.html", "SUBMISSION_KIT.md"],
        True,
        [r"\b160\b", r"\b159\b", r"37\.3"],
        "states ~260 H100-hours disagrees with the report/kit/paper (~160 = 37.3 min x 32 nodes x 8 GPUs)",
        True,
    ),
    P(
        "P16",
        "S10_cross_document",
        "cross_document_inconsistency",
        "make form and report disagree",
        "report",
        "Pauli Monte Carlo 0.187, issues",
        "Pauli Monte Carlo 0.178, issues",
        ["refs/tracker_issues_20260924.txt", "FORM_ANSWERS.md"],
        True,
        [r"0\.187\b", r"0\.1867"],
        "states the pending Pauli Monte Carlo value is 0.187 (issue #204: 0.1867), not 0.178",
        True,
    ),
    P(
        "P12",
        "S11_hidden_denominator",
        "hidden_denominator",
        "drop the words that restrict the denominator",
        "form",
        "19–33-qubit points with a result (BlueQubit statevector above 19)",
        "19–33-qubit points (BlueQubit statevector above 19)",
        ["results/floquet_patch33.json", "PATCH_PREREG.md"],
        False,
        [
            r"with a result",
            r"missing",
            r"\b75\b",
            r"\b3\b.{0,30}(server|terminat|lost|missing|jobs)",
            r"exclud",
        ],
        "states 72 counts only points with a result; 3 lost 33q jobs are excluded (75 attempted)",
        False,
        mirror=["kit"],
    ),
    P(
        "P17",
        "S01_armB_control",
        "dropped_qualifier",
        "delete the one text string check_claims reads",
        "report",
        "arXiv:2607.24937, <b>co-authored by BlueQubit</b>; its own",
        "arXiv:2607.24937; its own",
        ["FORM_ANSWERS.md", "SUBMISSION_KIT.md"],
        False,
        [r"co-?author", r"disclos", r"conflict of interest", r"bluequbit('s)? (own|staff|ceo|cto)"],
        "states the report no longer discloses that the Floquet candidate is co-authored by BlueQubit",
        True,
        armB=[COAUTH_CHECK],
    ),
]


# ---------- source validation: each returns (orig_consistent, planted_contradicted, note) ----------
def J(rel):
    return json.loads((ROOT / rel).read_text())


def _sweep():
    return {
        (r["obs"], r["cycles"], r["method"][:3], r["setting"]): r["value"]
        for r in J("results/tracker_floquet51_sweep.json")
    }


def v_P01():
    d = J("results/mps_ordering_hh3_s5.json")["runs"]
    g = lambda o: next(
        r["abs_err"] for r in d if r["theta"] == "pi4" and r["order"] == o and r["chi"] == 128
    )
    x = g("native") / g("rcm")
    return round(x) in (235, 236), abs(x - 325) > 50, f"ratio {x:.1f}"


def v_P02():
    d = J("results/mps_ordering_hh3_s5.json")["runs"]
    w = next(
        r["wall_s"]
        for r in d
        if r["theta"] == "3pi8" and r["order"] == "native" and r["chi"] == 128
    )
    return abs(w - 21) < 0.5, abs(w - 41) > 5, f"native wall {w}"


def v_P13():
    n = len(J("results/tracker_floquet51_sweep.json"))
    return n == 96, n != 84, f"n={n}"


def v_P22():
    z = J("teams/rcs/wave3/results/gap_d36.json")["mirror_vs_4patch"]["z"]["c_both_inflated"]
    return round(z, 1) == 2.8, abs(z - 1.8) > 0.5, f"z={z:.3f}"


def v_P14():
    V = _sweep()
    c = {(r["obs"], r["cycles"]): r["value"] for r in J("results/tracker_floquet51_chi512.json")}
    q = {
        "mag": 0.396,
        "zzd2": 0.2916,
        "zzd3": 0.2278,
    }  # 13-cycle hardware values, tracker/README.md
    readme = (ROOT / "tracker/README.md").read_text()
    assert all(str(v) in readme for v in q.values())
    x = [512 * 2 ** ((c[(o, 13)] - q[o]) / (V[(o, 13, "mps", 256)] - c[(o, 13)])) for o in q]
    return min(x) >= 5500 and max(x) <= 8500, max(x) > 4400 * 1.2, f"{min(x):.0f}-{max(x):.0f}"


def v_P36():
    rr = [r for r in J("results/floquet_oracle19_tx2.4_tz0.9_c5.json") if abs(r["exact"]) > 0.02]
    b = [abs(r["exact"]) - abs(r["mps_64"]) for r in rr if abs(r["mps_64"]) < abs(r["exact"])]
    k = sum(x > 0.005 for x in b)
    return (len(b), k) == (4, 3), k != 1, f"below={len(b)} beyond={k}"


def v_P53():
    f = J("teams/rcs/wave2/results/pooled.json")["4-patch"]["mine"]["fidelity"]["mine"]
    return round(f, 6) == 0.001999, abs(f - 1.899e-3) > 5e-5, f"F4={f:.6e}"


def v_P06():
    def t(f):
        rs = [r for r in J(f) if r.get("exact") is not None and r.get("mps_256") is not None]
        return round(
            1
            - st.median(r["mps_256"] - r["exact"] for r in rs)
            / st.median(r["mps_64"] - r["exact"] for r in rs),
            2,
        )

    a, b, c = (
        t("results/floquet_patch27.json"),
        t("results/floquet_patch33.json"),
        t("results/floquet_patch33_27cyc.json"),
    )
    return (a, b, c) == (0.83, 0.67, 0.39), c < 0.67, f"{a}/{b}/{c}"


def v_P21():
    ds = {r["depth"] for r in J("teams/rcs/wave2/results/per_circuit.json")}
    return ds == {36}, ds == {36}, f"depths={sorted(ds)}"


def v_P09():
    rs = J("results/floquet_patch33.json")
    ok = sum(
        r.get("exact") is not None and r["pau_0.0001"] - 0.005 <= r["exact"] <= r["mps_64"] + 0.005
        for r in rs
    )
    pre = (ROOT / "PATCH_PREREG.md").read_text()
    return (
        (ok, len(rs)) == (15, 18) and ">= 95%" in pre and "missing" not in pre.lower(),
        ok / len(rs) < 0.95,
        f"{ok}/{len(rs)}",
    )


def v_P19():
    txt = (ROOT / "report/report.html").read_text()
    return (
        "[−0.200, −0.005]" in txt,
        True,
        "CI upper bound -0.005 < 0 (text itself); pilot/results score file",
    )


def v_P29():
    b = J("results/floquet_big_51qx30c.json")[0]
    g = 0.541 - b["mps_1024"]
    return (
        round(g, 3) == 0.003,
        True,
        f"gap {g:.4f}; same sentence says closeness is not convergence",
    )


def v_P10():
    o = [r for r in J("results/floquet_oracle19.json") if abs(r["exact"]) > 0.02]
    hi = sum(
        1
        for r in o
        for k in ("mps_16", "mps_64")
        if r.get(k) is not None and abs(r[k]) > abs(r["exact"]) + 0.005
    )
    lo = sum(
        1
        for r in o
        for k in ("mps_16", "mps_64")
        if r.get(k) is not None and abs(r[k]) < abs(r["exact"]) - 0.005
    )
    return (hi, lo) == (52, 0), hi > lo, f"hi={hi} lo={lo}"


def v_P32():
    ki = J("results/kicked_ising_hh3_s5.json")
    return (
        all(r["pp_0.0001"] <= r["exact_local"] + 1e-12 for r in ki),
        True,
        "pp <= exact at every theta",
    )


def v_P15():
    a = (ROOT / "refs/arXiv2608.13110_abstract.txt").read_text()
    h = 37.3 / 60 * 32 * 8
    return (
        "37.3 minutes" in a and "32 nodes" in a and 150 <= h <= 165,
        abs(h - 260) > 50,
        f"{h:.1f} H100-h",
    )


def v_P16():
    t = (ROOT / "refs/tracker_issues_20260924.txt").read_text()
    return "#204 0.1867" in t, True, "#204 0.1867"


def v_P12():
    rs = J("results/floquet_patch33.json")
    miss = sum(r.get("exact") is None for r in rs)
    return miss == 3, miss > 0, f"33q missing={miss}"


def v_P17():
    f = (ROOT / "FORM_ANSWERS.md").read_text()
    return "co-authored by BlueQubit" in f, True, "form discloses"


def v_text(pid):  # qualitative plants whose contradiction is in the corpus text itself
    need = {
        "P08": ("FORM_ANSWERS.md", "planned near-Clifford oracles"),
        "P20": ("FORM_ANSWERS.md", "does not test other"),
        "P24": ("results/floquet_oracle19_tx2.4_tz0.9_c5.json", "exact"),
        "P07": ("FORM_ANSWERS.md", "already have cutwidth 4"),
        "P30": ("results/tracker_floquet51_chi512.json", "value"),
        "P11": ("report/report.html", "exact-oracle table"),
        "P31": ("report/report.html", "returns <i>exactly</i> 0.0000"),
    }[pid]
    return need[1] in (ROOT / need[0]).read_text(), True, f"{need[0]} contains '{need[1]}'"


VALIDATORS = {k: v for k, v in globals().items() if k.startswith("v_P")}


def validate_entry(p):
    fn = VALIDATORS.get("v_" + p["id"])
    ok_o, ok_p, note = fn() if fn else v_text(p["id"])
    for s in p["source"]:
        assert (ROOT / s).exists(), (p["id"], s)
        assert any(s == i or s.startswith(i + "/") for i in INCLUDE), (
            p["id"],
            "source not in corpus",
            s,
        )
    assert ok_o and ok_p, (p["id"], note)
    assert p["orig"].count("\n") == p["planted"].count("\n"), (p["id"], "line count")
    return note


# ---------- text normalisation and segmentation (shared with score.py) ----------
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
        (" ", " "),
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
    hits = [i for i, s in enumerate(segs) if span_clean and span_clean in s]
    return hits


# ---------- planting ----------
def plant_docs(originals, plants):
    docs = dict(originals)
    for p in plants:
        for d in [p["doc"]] + p["mirror"]:
            assert docs[d].count(p["orig"]) == 1, (p["id"], d, "orig not unique")
            docs[d] = docs[d].replace(p["orig"], p["planted"])
            if p["planted"]:
                assert docs[d].count(p["planted"]) == 1, (p["id"], d, "planted not unique")
    return docs


def plant_sentence(doc_text, html, p, which):
    """Normalised segment containing the plant (which='orig' in original, 'planted' in planted doc)."""
    segs = segments(doc_text, html)
    span = p[which]
    if which == "planted" and not span:  # deletion: locate by the text just after the deleted span
        return None
    c = clean(norm_doc(span, html))
    idx = seg_index(segs, c)
    assert len(idx) == 1, (p["id"], which, len(idx))
    return segs[idx[0]]


def locate_deletion(orig_doc, planted_doc, html, p):
    so = plant_sentence(orig_doc, html, p, "orig")
    ps = segments(planted_doc, html)
    target = clean(
        norm_doc(so, False).replace(
            clean(norm_doc(p["orig"], html)), clean(norm_doc(p["planted"], html))
        )
    )
    target = re.sub(r"\s+", " ", target).strip()
    idx = [i for i, s in enumerate(ps) if s == target]
    assert len(idx) == 1, (p["id"], "deletion sentence", len(idx))
    return ps[idx[0]]


def abstract_words(form):
    return len(form[form.find("## Project abstract") : form.find("## Related")].split()) - 12


def select(copy_k):
    rng = random.Random(SEED_BASE + copy_k)
    chosen = []
    orig_segs = {d: segments((ROOT / DOCS[d]).read_text(), d == "report") for d in DOCS}

    def seg_of(p):
        return (
            p["doc"],
            seg_index(orig_segs[p["doc"]], clean(norm_doc(p["orig"], p["doc"] == "report")))[0],
        )

    for stratum, n in QUOTA:
        cands = sorted([p for p in POOL if p["stratum"] == stratum], key=lambda p: p["id"])
        rng.shuffle(cands)
        got = 0
        for p in cands:
            if got == n:
                break
            if seg_of(p) in {seg_of(q) for q in chosen}:
                continue
            chosen.append(p)
            got += 1
        assert got == n, (copy_k, stratum)
    return chosen


def build_copy_texts(copy_k):
    originals = {d: (ROOT / DOCS[d]).read_text() for d in DOCS}
    plants = select(copy_k)
    docs = plant_docs(originals, plants)
    recs = []
    for p in plants:
        locs = []
        for d in [p["doc"]] + p["mirror"]:
            html = d == "report"
            if p["planted"]:
                sent = plant_sentence(docs[d], html, p, "planted")
                pos = docs[d].index(p["planted"])
            else:
                sent = locate_deletion(originals[d], docs[d], html, p)
                pos = originals[d].index(p["orig"])
            line = docs[d][:pos].count("\n") + 1
            locs.append({"doc": d, "path": DOCS[d], "line": line, "sentence_norm": sent})
        r = {k: v for k, v in p.items() if k != "mirror"}
        r["mirror"] = p["mirror"]
        r["locations"] = locs
        recs.append(r)
    # every non-plant byte identical; line counts preserved; changed lines only where plants are
    for d in DOCS:
        assert docs[d].count("\n") == originals[d].count("\n"), (copy_k, d, "line count")
        assert (ROOT / DOCS[d]).read_bytes() == originals[d].encode("utf-8"), (d, "original not plain utf-8/LF")
        allowed = {L["line"] + i for r in recs for L in r["locations"] if L["doc"] == d
                   for i in range(r["orig"].count("\n") + 1)}
        changed = {i + 1 for i, (a, b) in enumerate(zip(originals[d].split("\n"), docs[d].split("\n"))) if a != b}
        assert changed <= allowed, (copy_k, d, "unexpected changed lines", sorted(changed - allowed))
        assert {L["line"] for r in recs for L in r["locations"] if L["doc"] == d} <= changed, (copy_k, d)
    for r in recs:  # supporting-file tells: does any non-document corpus file contain the original span?
        needle = clean(norm_doc(r["orig"], r["doc"] == "report"))
        r["support_file_tell"] = sorted(f for f in support_texts() if needle and needle in support_texts()[f])
    rep, frm = docs["report"], docs["form"]
    pred = {
        "hits": [p["id"] for p in plants if p["armB_checks"]],
        "coauth_check_fails": not (
            "co-authored by BlueQubit" in rep and "co-authored by BlueQubit" in frm
        ),
        "abstract_words": abstract_words(frm),
        "abstract_check_fails": not (330 <= abstract_words(frm) <= 360),
    }
    return docs, recs, pred


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
    paths = sorted(dst.rglob("*"), key=lambda p: -len(p.parts))
    for p in paths + [dst]:
        os.utime(p, (FIXED_MTIME, FIXED_MTIME), follow_symlinks=False)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--validate"
    for p in POOL:
        note = validate_entry(p)
        print(f"pool {p['id']} {p['stratum']}: source OK")
    assert len({p["id"] for p in POOL}) == len(POOL)
    base_words = abstract_words((ROOT / DOCS["form"]).read_text())
    print(f"original abstract words (checker formula): {base_words}")
    for k in (1, 2, 3):
        docs, recs, pred = build_copy_texts(k)
        print(
            f"planted copy {k}: {len(recs)} plants, ids {sorted(r['id'] for r in recs)}; "
            f"armB predicted hits {pred['hits']}, abstract words {pred['abstract_words']}, "
            f"word-count check predicted to fail: {pred['abstract_check_fails']}"
        )
    if mode == "--validate":
        print("VALIDATE OK (nothing written)")
        return
    if mode == "--write-pool":
        SEALED.mkdir(exist_ok=True)
        (SEALED / "pool.json").write_text(
            json.dumps(
                {"seed_base": SEED_BASE, "quota": QUOTA, "pool": POOL, "include": INCLUDE},
                indent=1,
                ensure_ascii=False,
            )
            + "\n"
        )
        print("pool sha256", hashlib.sha256((SEALED / "pool.json").read_bytes()).hexdigest())
        return
    if mode == "--build":
        sha16 = (WAVE / "PREREG.sha16").read_text().strip()
        assert frozen_prefix_sha16() == sha16, "PREREG prefix does not match PREREG.sha16"
        pool_sha = hashlib.sha256((SEALED / "pool.json").read_bytes()).hexdigest()
        prereg = (WAVE / "PREREG.md").read_text()
        assert pool_sha in prereg, "pool.json hash not in PREREG"
        for f in ("build.py", "score.py", "run_armB.py", "VERIFIER_BRIEF.md"):
            assert hashlib.sha256((WAVE / f).read_bytes()).hexdigest() in prereg, f"{f} hash not in PREREG"
        frozen = json.loads((SEALED / "pool.json").read_text())
        assert frozen == json.loads(json.dumps({"seed_base": SEED_BASE, "quota": QUOTA, "pool": POOL,
                                                "include": INCLUDE}, ensure_ascii=False)), "POOL != pool.json"
        assert not CORPUS.exists(), "corpus exists; refusing to overwrite"
        secret = os.urandom(16).hex()
        labels = ["A", "B", "C", "D"]
        random.Random(secret).shuffle(labels)
        mapping = {
            labels[0]: "planted_1",
            labels[1]: "planted_2",
            labels[2]: "planted_3",
            labels[3]: "placebo",
        }
        key = {"prereg_sha16": sha16, "seed_base": SEED_BASE, "copies": {}}
        originals = {d: (ROOT / DOCS[d]).read_text() for d in DOCS}
        for lab in sorted(mapping):
            dst = CORPUS / f"copy_{lab}"
            copy_tree(dst)
            if mapping[lab] == "placebo":
                key["copies"][lab] = {
                    "kind": "placebo",
                    "plants": [],
                    "armB_predicted": {
                        "hits": [],
                        "coauth_check_fails": False,
                        "abstract_words": base_words,
                        "abstract_check_fails": not (330 <= base_words <= 360),
                    },
                }
                for d in DOCS:
                    assert (dst / DOCS[d]).read_bytes() == (ROOT / DOCS[d]).read_bytes()
            else:
                k = int(mapping[lab].split("_")[1])
                docs, recs, pred = build_copy_texts(k)
                for d in DOCS:
                    (dst / DOCS[d]).write_bytes(docs[d].encode("utf-8"))
                    assert (dst / DOCS[d]).read_bytes() == docs[d].encode("utf-8")
                key["copies"][lab] = {
                    "kind": "planted",
                    "copy_index": k,
                    "selection_seed": SEED_BASE + k,
                    "plants": recs,
                    "armB_predicted": pred,
                }
            normalise_mtimes(dst)
        normalise_mtimes(CORPUS)
        (SEALED / "key.json").write_text(json.dumps(key, indent=1, ensure_ascii=False) + "\n")
        (SEALED / "assignment.json").write_text(
            json.dumps({"secret_seed_hex": secret, "labels": mapping}, indent=1) + "\n"
        )
        n = sum(len(c["plants"]) for c in key["copies"].values())
        print(
            f"BUILT copies={sum(c['kind'] == 'planted' for c in key['copies'].values())} planted_total={n}"
        )
        for f in ("key.json", "assignment.json"):
            print(f, hashlib.sha256((SEALED / f).read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
