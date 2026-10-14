# Verdict — SemIf 0.8B claim-entailment pilot (PREREG sha16 6d6f55e2f01e3389): DROP
Run 2026-09-25 (interpreter .cache/kev-venv, transformers 5.17 — the cohezion venv's 4.57 cannot load qwen3_5; first attempt
failed at load, no scores). Sanity control passed (0.993 vs 0.001). Pairwise 8/10 (< 9 required); AUROC 0.740 vs length 0.525.
Misses fall on the error classes that matter most here: p3 filled a gap the premise leaves open (0.94 on "the pre-registration
specifies that missing points are excluded" — it says nothing about missing points); p10 inverted a numeric ordering (0.88 that
0.5583 fell below 0.541). Near-misses on numeric ranges (p4 0.969 vs 0.929) and containment (p9 0.804 for a false exclusion).
Reading: good on gross contradictions (counts, 45/45 vs 72/72), unreliable on numeric comparison and omission. Numbers are
already covered deterministically by check_claims.py; omissions need an independent reviewer. Not used; not cited.
Caveat: n=10 pairs, items and labels written by the author.
