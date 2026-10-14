# Result — site-based NLCE feasibility (frozen PREREG.md, sha16 8cc7cc4f71c11fdc)
Author-scored by the team's own score.py; pending the orchestrator's independent verifier (A1/P1).
Instrument controls C1–C4 all passed before scoring (results/controls.json): same-constructor match 1e-14; full-order
identity on a 14-site loop subgraph 5e-14; oracle19 reproduction 5e-14; ESU = brute force (316 = 316).
Run: 22,668 clusters (all connected induced subgraphs ≤16 sites of patch(33); patch(27)'s are a subset), 0 failed,
0 retries, local only, 4 single-thread workers, ~16 min; $0; no BlueQubit use.

**Verdict: FAIL** (gate i: 0/6 late points within 0.02; gate ii: NLCE mean late |err| 11.4 vs baseline 0.041).
- Exact-to-±0.0002 at c = 1, 2, 4 for both n (c = 4 is already beyond the order-16 cone guarantee).
- Diverges by c = 8: S_16 = −0.171 (27q, exact 0.263), −0.577 (33q, exact 0.309); late values reach |S| ≈ 1–33,
  the kind of divergence 1701.02758 documents for site-based expansions (there: 1D, diagonal ensemble). Tracking horizon C* = 4 (both n; no exact targets at c = 5–7).
- δ16 = |S16−S15| by cycle (27q): 0, 0, 0, 0.0004, 0.006, 0.058, 0.23, 0.95 — the diagnostic grows with the error.
  False-confidence points: 0 of 16 → the diagnostic is CALIBRATED: it flags its own failure (descriptive: from c ≈ 6).
- Baseline (exact 16-site BFS ball) is within 0.02 at only 2/6 late points (mean 0.041); it is not a usable estimator either.
- It held one target cycle longer than the cone guarantee (c ≈ 2), then diverged by c = 8: consistent with the cone argument.
- 51q×30c: nothing can be said. Site-based NLCE at order ≤16 is reliable only to about cycle 4–5 here, far below 30
  (max cone at 51q: 44 sites at c = 4, all 51 by c = 10).
- Scope of the negative: THIS VARIANT fails. Maximally-connected and rectangular-cluster NLCEs (1701.02758, 2005.03104)
  and resummations were NOT tested (the prereg forbade rescue variants). The cone argument makes it unlikely they reach
  30 cycles, but they are untested, not excluded.
