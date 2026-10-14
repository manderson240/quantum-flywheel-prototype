# Independent verification: floquet wave 1 (site-based NLCE feasibility)

Verifier: independent adversarial pass on 2026-09-25, with fresh context. I wrote my own scorer, cluster enumerator and NLCE, and ran them *before* I read `score.py`. No existing file was modified. I made no BlueQubit, download, post or .env access.
Resources: MemAvailable was 37.6 GiB at the start, above the 20 GiB floor. My heaviest process was an NLCE recompute: 162 MB RSS, `nice -n 10`, 3 min 51 s.

## Claim table

| # | Claim | Team | Mine | Verdict |
|---|---|---|---|---|
| 1 | Hash of PREREG.md | sha16 8cc7cc4f71c11fdc | The sha256 prefix is `8cc7cc4f71c11fdc`. | CONFIRMED |
| 2 | PREREG.md was frozen before any prediction existed | Frozen at 11:26:58 | PREREG.md mtime is 11:26:58, and the file is read-only. `frozen_at` is 11:27:01. `nlce.py` is dated 11:28, `controls.json` 11:29 and `nlce_run.json` 11:51. Only `cone_geometry.*` (11:23, disclosed) and `count_clusters.py` (11:22, geometry only, not disclosed) predate the freeze. `teams/floquet/` is untracked in git, so mtimes are the only evidence, and mtimes can be forged. | CONFIRMED (weak evidence) |
| 3 | Gate, cluster family, order, metric and missing-point rules were fixed in advance and applied as written | Yes | The PREREG fixes all of them. The ≤0.02 gate comes from decision-path §5, a file dated 09:29 that predates the team's work. `score.py` applies the rules as written: raw S_16, 6 late points, gate (ii) as a mean comparison. There were 0 failures, so no missing-point rule fired. | CONFIRMED |
| 4 | The disclosure that the targets were visible beforehand is adequate | Disclosed | Adequate. The free choices were K=16 (compute-bound), the target cycles (the existing grid), the 0.02 gate (pre-existing) and a strong baseline (the 16-site ball). None of these could steer the result toward a PASS, and the outcome is a FAIL. | CONFIRMED |
| 5 | c=1, 2 and 4 are within 0.0002 | ±0.0002 | 27q: 6e-7, 4e-7, **2.26e-4**. 33q: 3e-7, 2e-7, 1.57e-4. The 27q c=4 point exceeds 0.0002 by 13%. | OVERSTATED (trivial; ±0.00023 is correct) |
| 6 | c=8 errors | 0.43 (27q), 0.89 (33q) | 0.4337 and 0.8852. S_16 = −0.1709 and −0.5766. | CONFIRMED |
| 7 | Late points within 0.02 | 0/6 | 0/6. Late errors: 1.93, 1.82, 6.30 (27q) and 11.6, 14.0, 32.5 (33q). | CONFIRMED |
| 8 | NLCE vs baseline late mean error | 11.4 vs 0.041 | 11.3606 vs 0.040969 | CONFIRMED |
| 9 | Baseline within 0.02 at late points | "only 2/6" (RESULT.md) | **1/6**. Baseline errors: 0.0317, 0.0044, 0.0352, 0.0820, 0.0493, 0.0433. | WRONG (minor; the conclusion is unaffected) |
| 10 | δ16 for 27q, c=1..8 | 0, 0, 0, 0.0004, 0.006, 0.058, 0.23, 0.95 | 0, 0, 0, 0.0004, 0.0061, 0.0578, 0.2313, 0.9452 | CONFIRMED |
| 11 | False-confidence points (δ≤0.01 and e>0.02) | 0/16, "CALIBRATED" | 0/16 | CONFIRMED, but see problem 3 |
| 12 | "The diagnostic grows with the error" | Monotone reading | Not monotone at late times. For 27q, δ goes 7.51 → 1.42 → 0.55 at c=16/20/27, while the error goes 1.93 → 1.82 → 6.30. δ under-reports the error 11× at 27q c=27. | OVERSTATED |
| 13 | Horizon C* = 4 (both n); 6/16 = 37.5% of points within 0.02 | 4 / 0.375 | 4 / 6 of 16 | CONFIRMED |
| 14 | Cluster counts: 22,668 (33q) and 7,808 (27q); 27q clusters ⊂ 33q | Stated | I counted independently by level growth with deduplication: 7,808 and 22,668. The subset relation holds, and the union is 22,668. Graph sizes: 27q has 27 edges (1 loop); 33q has 34 edges (2 loops). | CONFIRMED |
| 15 | The NLCE implementation is correct (possible false negative?) | C1–C4 pass | I built an independent NLCE from qiskit `Statevector` on `floquet_patch_oracle.build` circuits, with my own enumeration and inclusion–exclusion. It matches `S_over_n` to **1.8e-13** (27q, all orders ≤10, t≤10) and **1.2e-13** (33q, orders ≤8, t≤10). This covers c=8, where divergence has already begun (e.g. 33q S_8 at t=7 is 2.689). The gate convention is correct: RX→RZ per site, then RZZ(π/3), layer by layer, matching `build`. The c≤2 agreement to 1e-7 with BlueQubit exact values rules out a convention bug. I found no false-negative bug. | CONFIRMED |
| 16 | Divergence is an intrinsic method failure, not a bug | Yes | Consistent with #15. The raw site-based sum is reproduced exactly by an independent implementation. | CONFIRMED |
| 17 | Citation 1701.02758 | Site-based diverges where maximally connected converges; "resummation only partly cures it" | Title, authors and the divergence claim match the abs page. The abstract says only that they "discuss the effectiveness of resummations". "Only partly" is not supported by the abstract. | OVERSTATED (minor) |
| 18 | Citation 1710.07696 | 2D TFIM and XXZ; "dramatically more accurate … at short-to-moderate times" | Exact phrase, title and authors match. | CONFIRMED |
| 19 | Citation 2005.03104 | Rectangular clusters, 2D TFIM, polarized states, "competitive to other state-of-the-art" | Matches. | CONFIRMED |
| 20 | Citation 1907.04261 | NLCE under periodic driving, energy vs time, exponential regime | Matches. | CONFIRMED |
| 21 | Citation 1711.01284 | Real-time NLCE, 1D hard-core bosons, exponential relaxation | Matches. The abs page does not show the phrase "within the accessible times" in the fetched summary. | CONFIRMED (the quoted phrase is unchecked) |
| 22 | Cone geometry: 51q covers all sites by c=10; 44 sites at c=4 | Stated | `cone_geometry.json` agrees. | CONFIRMED |
| 23 | Application text: cones "span the whole lattice by cycle 10–13" | 51q and 74q | 51q at c=10 is confirmed. No 74q cone data exists in the team outputs, so the "13" is unsupported by the team's data. | UNVERIFIABLE |
| 24 | Application text states the negative as a negative and does not overclaim untested variants | Yes | It says "This variant therefore cannot reach…" and "We did not test other cluster families." RESULT.md: "untested, not excluded". Honest. | CONFIRMED |
| 25 | Memory rule: <1 GB per process, nice | 4 single-thread workers | By design, the largest state is 2^16 complex = 1 MB, and P holds 22,668 × 30 floats. Pool(4), with MemAvailable backoff implemented. There is no runtime RSS log, so the claim is based on design only. My re-run of the same kind of work peaked at 162 MB. | CONFIRMED (by design) |

## Ranked problems

1. **WRONG, minor.** RESULT.md says the baseline was within 0.02 at "only 2/6 late points". The correct figure is 1/6 (only 27q c=20, error 0.0044). The FAIL verdict and gate (ii) are unaffected.
2. **OVERSTATED.** "±0.0002 at c = 1, 2, 4" (RESULT, STATUS and application text). The 27q c=4 error is 2.26e-4, so write ±0.00023 or "≤3e-4".
3. **OVERSTATED.** The diagnostic is called "CALIBRATED" and is said to "grow with the error". It is calibrated only in the pre-registered binary sense (no false-confidence points). As a magnitude signal it is not monotone and under-reports the error by up to 11× (27q c=27: δ = 0.55, error = 6.30). Any 51q use of δ should say "flags failure", not "estimates error".
4. **OVERSTATED, minor.** research_nlce.md says resummation "only partly cures it" (1701.02758). The abstract only says the paper discusses effectiveness.
5. **UNVERIFIABLE.** The "10–13" cone-coverage figure in the application text: the 74q figure is not in the team's data.
6. **Process.** The freeze proof rests on mtimes of untracked files (lesson P3: "prove it was pending"). A git commit or external timestamp would be stronger. `count_clusters.py` predates the freeze and is not disclosed; it is geometry only, so this is harmless.

## Bottom line

The core result stands and is independently reproduced. The site-based NLCE at order ≤16 is implemented correctly; my independent implementation agrees to 1e-13. It tracks exactly through c=4 and diverges by c=8. It fails 0/6 late points and loses to the 16-site-ball baseline (11.36 vs 0.041). The fix list is textual: one wrong count and three overstated phrasings.

FLOQUET WAVE1: WRONG=1 OVERSTATED=3
