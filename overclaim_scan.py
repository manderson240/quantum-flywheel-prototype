"""Deterministic scan for universal/superlative wording in the application text — the class of error that slipped past
check_claims.py three times ("every δ it accepts", "three pre-registered tests", "first"). Prints each hit with context
for a human decision; it does not judge truth. Run: python overclaim_scan.py"""
import re, html
from pathlib import Path
H = Path(__file__).parent
WORDS = r"\b(every|all|always|never|none|only|first|exactly|any|unique(ly)?|guarantee[sd]?|prove[sn]?|proof|certif\w*|bound[s]?|decisive(ly)?|definitive(ly)?|impossible|cannot|will)\b"
def text(p):
    t = p.read_text()
    if p.suffix == ".html":
        t = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<style.*?</style>", "", t, flags=re.S)))
    return re.sub(r"\s+", " ", t)
targets = [H / "report/report.html", H / "SUBMISSION_KIT.md"]
n = 0
for p in targets:
    t = text(p)
    for m in re.finditer(WORDS, t, re.I):
        n += 1
        print(f"{p.name}: …{t[max(0, m.start()-70):m.end()+60]}…")
print(f"\n{n} hits to review (each must be literally true or reworded)")
