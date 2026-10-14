# floquet team — wave 1 STATUS (2026-09-25)
- Deliverable: pre-registered site-based NLCE feasibility test (PREREG.md, sha16 8cc7cc4f71c11fdc, frozen before any prediction).
- Controls C1–C4 passed (≤5e-14). 22,668 clusters ≤16 sites, 0 failures, local, $0, no BlueQubit/ledger use.
- Verdict FAIL: NLCE exact (±0.0002) at c = 1, 2, 4 on 27q/33q, diverges by c = 8 (errors 0.43/0.89, late |S| up to 33).
- Tracking horizon C* = 4 cycles; late-point gate 0/6; beaten by the plain 16-site-ball baseline (0.041 mean err).
- Diagnostic δ = |S16−S15| is calibrated (0 false-confidence points) — the method reports its own failure.
- Implication: site-based NLCE at order ≤16 cannot reach 51q×30c / 74q×27c depths; maximally-connected/rectangular NLCE untested.
- Author-scored (team score.py); pending the orchestrator's independent verifier (A1/P1).
- 74q×27c χ=1024 value: not read or interpreted by this team.
- Recommendation: redirect floquet effort to the IF-BP oracle gate (row 1); cite this as a documented negative; maximally-connected NLCE is the one untested variant.
