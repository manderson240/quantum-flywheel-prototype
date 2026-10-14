# Independent verification: rcs team, wave 1 (2026-09-25)

**Verifier:** a fresh-context adversarial agent.

**Method.**
- I wrote my own parser and analysis code (scratchpad only) before opening any of the team's scripts or result JSONs. The team's scripts were never run.
- The circuit is `refs/rcs-nighthawk-meta/data/circuits/full/d36_logical.qasm`. Qubit coordinates come from `data/README.md`: rows 1–8 and columns 2–9, with physical qubits 17, 55 and 62 dropped, numbered row-major.
- The paper, arXiv:2609.28657v1, was read as HTML with the math alttext retained.
- GitHub was accessed only through two metadata calls: the git-tree API and the commits API. No data file was downloaded.

**Environment.**
- MemAvailable was 31 GiB at the start, above the 20 GiB floor.
- All processes were under 100 MB and ran at `nice -n 10`.

**Phase-0 controls (each must return a result, or the instrument is broken).**

| Source | Control | Result |
|---|---|---|
| arXiv abs pages | 1910.11333 | 200, correct title |
| Paper HTML | 280 KB fetched | 200 |
| GitHub tree API | pinned commit | 200, not truncated, 552 blobs |

## Results table

### 1. Circuit facts

| Claim | Team value | My value / source | Verdict |
|---|---|---|---|
| Qubits, cycles | 61, 36 | 61 qubits; 36 CZ layers, each preceded by one rz-rx-rz layer (4392 rz, 2196 rx) | CONFIRMED |
| CZ count, pattern | 918; 29/22 per cycle | 918; alternating 29, 22; every layer is a matching | CONFIRMED |
| Couplers | 102 × 9 uses; 51 horizontal + 51 vertical | 102 distinct, each used exactly 9 times; 51/51; all nearest-neighbour. This equals every lattice edge among the 61 qubits. | CONFIRMED |
| Final 22-CZ layer leaves the output distribution unchanged | TVD 0.0; negative control 0.50 | Exact. The circuit ends CZ, barrier, Z-measurement. A diagonal unitary D gives \|⟨x\|DU\|0⟩\|² = \|d_x\|²\|⟨x\|U\|0⟩\|² with \|d_x\|=1. My own 15-qubit statevector (logical 8–22, 7 final-layer CZ inside) gives TVD 0.0. Dropping CZ layer 20 gives TVD 0.50020, which matches the team's 0.500195. | CONFIRMED |
| 896 effective CZ | 896 | 918 − 22 = 896 | CONFIRMED |
| Collision ratio of the 15-qubit subcircuit | 0.998 | 0.99764 | CONFIRMED |

### 2. Cut widths and the MPS bound

| Claim | Team value | My value / source | Verdict |
|---|---|---|---|
| Maximum CZ crossings at a bond, row-major | 80 | 80 over the 896 effective CZ; 81 if all 918 are counted. Total crossings 3,806 (896) and 3,978 (918). | CONFIRMED (80 is the 896-CZ count) |
| Bound logic | ≤ 1 ebit per crossing CZ, capped at min(sides) | Correct: CZ has operator Schmidt rank 2, so each crossing adds at most 1 ebit per bond. The cap at bond k is min(k+1, 60−k). | CONFIRMED |
| Central cut reaches 30 ebits | by cycle 16 | Bond 29 cumulative crossings: 26 at cycle 15, 32 at cycle 16. The maximum over bonds first hits 30 at cycle 16. | CONFIRMED |
| χ=2048 (11 ebits) guaranteed exact | through cycle 6 | Maximum bound per cycle is 0,1,1,8,9,10,10,**17**,…, so exact through cycle 6. The same is true at χ=1024 and χ=4000. | CONFIRMED |
| χ 1024→4000 shifts saturation | by < 1 cycle | By 0 cycles, for both the first bond and the mid-bond (cycle 8) | CONFIRMED |
| Bonds needing more than 2^11, with caps up to 2^30 | 38/60 | 38; all 60 bonds saturate their cap by cycle 36 | CONFIRMED (wording is loose) |
| RCM is worse | max 141 (896) | scipy RCM: 141 (896) / 144 (918); χ=2048 exact only through cycle 2; cap reached at cycle 9 | CONFIRMED |
| Other orderings (A4 table) | row-snake 80/3823; col-major 81/3938; anti-diagonal 114/4563 | Identical | CONFIRMED |
| Column-major | cap at cycle 18; χ=2048 exact through cycle 4 | 18; 4 | CONFIRMED |
| Draft lossy-event model (A1, A3), draft's definition (§F) | 2523 (χ=512), 2353 (χ=1024), 2189 (χ=2048) on 896 CZ; 2516/2345 on 918 | Identical | CONFIRMED |
| F̃ table (A1d) | e.g. 5.4e-11 at ε=1%, χ=1024 | 0.99^2353 = 5.4e-11; the other five cells also match | CONFIRMED |
| "T2 gap at χ=512 ≥ 2.9 decades even at ε=0.5%" | ≥ 2.9 | 0.995^2523 = 3.22e-6. The T2 threshold (draft l.53) is 2.3e-3, so the gap is log10(2.3e-3/3.22e-6) = **2.85** | OVERSTATED (nit) |
| Saturation cycles | 5 at χ=512; 7 at χ=1024/2048/4000; χ=256 exact through cycle 3; mid-bond exceeds log2 χ at cycle 8 | Same | CONFIRMED |

### 3. Paper vs release

| Claim | Team value | My value / source | Verdict |
|---|---|---|---|
| Table 1 times vs JSON | 108/99 yr vs 115.8/107.3 yr, ≤ 0.035 decades | Paper Table 1 row: "36 918 64 21.82 108 yr 40 1020 65 22.03 99 yr". The JSON gives 3.6552e9 s and 3.3851e9 s, i.e. 115.83 and 107.27 yr (365.25 d); the gaps are 0.030 and 0.035 decades. The text also says "t≈110 Frontier years" and "t≈100 years". | CONFIRMED |
| W | 1.23e27 | JSON work_flops 1.2318e27; the paper says "W≈1.2×10^27 machine FLOPs" | CONFIRMED |
| Mirror fit | 0.326·0.872^d, unweighted | Unweighted log-LS: 0.3257140, 0.8716748 (exact match to the JSON). SE-weighted fit: 0.34996·0.86815^d, giving F(36) = 2.155e-3. | CONFIRMED |
| Mirror vs 3-patch at 36 cycles | 5.8σ | (2.2408−1.8391)e-3 / hypot(5.57e-5, 4.09e-5) = 5.81σ. The paper says the estimators "agree at every depth from 20 to 40 cycles", and its Fig. 2 note says "Error bars are ±5σ". | CONFIRMED |
| Pairwise extremes (release doc D-2) | 6.0σ at d20 (m–4p); 5.0/5.5 (3p–4p); 5.4 at d32 | −6.01, −4.99, −5.53, +5.41 | CONFIRMED |
| Fitted value vs measured at d36 | +1.4 / +11.8 / +10.0 σ | 1.43 / 11.79 / 9.99 | CONFIRMED |
| min_cuts.json computed on d32 | "circuit": "data/r2/r2_circuits/full/d32_logical.qpy" | Confirmed from the file. severed_2q_gates_total = 8 per coupler for all 28 cuts, which is d32. All 28 cut sizes and side sizes reproduce on my coupler graph. The README command names d36. | CONFIRMED |
| Manifest hashes .qpy only | sha256 2bb17672 is the .qpy hash; the .qasm hash is e2e72760 | All 233 entries carry one sha256, attached to `file` (.qpy). My sha256 of the .qasm is e2e72760. | CONFIRMED |
| Degree-2 qubits | {0,4,5,6,31,45,53,60} | Same; the paper says "eight degree-2 qubits" | CONFIRMED |
| Local copy integrity | 14/14 git blob SHA-1 match; b9dd86b0 is HEAD | 14/14 match (computed as blob-header SHA-1, not with the LFS-filtered `git hash-object`). The commits API HEAD is b9dd86b0 (2026-09-23T17:44Z). | CONFIRMED |
| Paper quotes in the release doc | "29/22/29/22", "0.326×10^{-0.0596d}", "w=64≈n", "unlimited-memory cost floors", "terminal measurement" | All found verbatim in the HTML. "Corrections point both ways" is supported by: "the corrections do not all point the same way". | CONFIRMED |

### 4. Download request

| Claim | Team value | My value / source | Verdict |
|---|---|---|---|
| Paths and sizes | 15 named files plus the per-depth qasm groups | Every byte count matches the pinned tree, e.g. K3/d36 ×15 = 3,586,672; K4/d36 ×15 = 3,567,097; npz 4,154,392 / 4,154,247; d40_logical 267,806. | CONFIRMED |
| Set sizes | A-min 42 / 15.61 MB; B 63 / 12.31 MB; union 93 / 25.43 MB; repo 552 blobs / 167.19 MB | 42 / 15.613; 63 / 12.308; 93 / 25.434; 552 / 167.186 | CONFIRMED |
| 93-file set is sufficient to reproduce patch_xeb from counts | at d36 | The inventory is complete for the **d36 point only**: counts npz, all 30 patched circuits (5 partitions × 3 instances × K3/K4; the manifest's 180 patched = 2 K × 6 depths × 5 × 3), layout.json, and the reference patch_xeb.json. Reproducing the whole patch_xeb.json needs A-full (202 files). `rcs/__init__.py` (and placement.py and viz.py) are not listed, which matters only if package imports must be read. Whether these files suffice depends on `compute_patch_xeb.py`, which I may not fetch. | UNVERIFIABLE (the inventory itself is CONFIRMED) |

### 5. Literature spot-check

Ten cited IDs were checked on their arXiv abs pages, all HTTP 200.

| ID | Team description | Abs page | Verdict |
|---|---|---|---|
| 2406.18889 | Zhao, Zhong, Pan et al., 2024; 1432 GPUs; 7× faster; "first unambiguous experimental evidence to refute" | Title "Leapfrogging Sycamore: Harnessing 1432 GPUs…"; 2024-06-27; the quote is in the abstract | CONFIRMED |
| 2504.09186 | Chen et al., 2025, SW-TNC; eliminates slicing overhead; >10× on Zuchongzhi-60-24 using >1024 Sunway nodes | Matches (Chen, Sun, Qiu…; 2025-04-12) | CONFIRMED |
| 2504.16718 | Dubey et al., 2025; DMRG on tree tensor networks | Dubey, Zeybek, Schmelcher; 2025-04-23 | CONFIRMED |
| 2603.20400 | Wei, Rajakumar, Nelson et al., 2026; 1D; MPO truncation errors contract | Matches; "1D noisy random circuits" | CONFIRMED |
| 2607.04054 | S. Oh, 2026; hardness lies in "identifying a specific circuit realization" | Matches verbatim | CONFIRMED |
| 2607.20804 | Go, Oh, Jeong, 2026; hard at γ=O(log n/(nd)), easy at ω(…) | Matches | CONFIRMED |
| 2512.07311 | Wold, Kasirajan; XEB 0.549 at 14 cycles; at 20 cycles only a time is given | Matches | CONFIRMED |
| 2509.04401 | Raab, 2025; Porter–Thomas-like sampling "without noise", not a given circuit | Matches | CONFIRMED |
| 2508.14975 | Saulière, Lami et al., 2025; late-time XEB tracks fidelity | Matches (Sauliere, Lami, Boyer, De Nardis, De Luca; 2025-08-20) | CONFIRMED |
| 2510.06346 | Nelson, Rajakumar, Gullans; d* = Θ(p⁻¹ log n); conjectured Θ̃(p⁻¹) | Matches | CONFIRMED |
| 2112.01657 | Gao et al.; 2–12% of experimental XEB, 2 s on 1 GPU | Matches | CONFIRMED |

No fabricated or misdated citation was found.

Count note: the lit doc cites 18 IDs plus the target paper (19 unique). The figure 28 in STATUS is the size of the verified pool (`arxiv_abs_verified_20260925.json`), not the number cited.

### 6. Numeric mappings in the lit doc

| Claim | Team value | My value / source | Verdict |
|---|---|---|---|
| Asymptotic mappings | ε_q = 2.25e-3; p⁻¹ ≈ 440; p⁻¹ ln n ≈ 1,800; ln 61/(61·36) = 1.9e-3 | 0.13734/61 = 2.251e-3; 444; 1,826; 1.87e-3 | CONFIRMED |
| Median CZ error | 1.9e-3 | Paper: "median CZ error of ∼1.9×10^{-3}" | CONFIRMED |

## Ranked problems

1. **WRONG: the lit doc misdescribes App. F on top-k.**
   - The doc says "A top-k-boosted severing attack is not covered by App. F (our inference, unverified)."
   - App. F does address it: "Known top-k postprocessing improves severed scores by O(1) factors [17] and does not change the conclusion." Ref. [17] is Gao et al. (2112.01657), which the team itself cites in the same table.
   - Defensible restatement: "App. F dismisses top-k in one sentence by citation. The O(1) boost is never measured against the ~10× margin of the pendant-arm branch."
   - That is a real open lever. "Not covered" is false.
2. **WRONG: prereg_amendments A11 says the scoping note's size "differs" from the local copy.**
   - The scoping note says "14 small files, about 360 KB **raw**".
   - The raw (apparent) size is 356,218 B, 348 KB by `du --apparent-size`. That matches the note.
   - The team's 265 KB is compressed ZFS on-disk usage (`du -sk`). The comparison mixes the two measures.
   - The file count (14 data files) also agrees. The first half of A11, that `layout.json` and `patch_xeb.json` have no local copy, stands.
3. **OVERSTATED (nit): A1(d) says the "T2 gap at χ=512 is ≥ 2.9 decades even at ε=0.5%".** The computed gap is 2.85 decades. The conclusion does not change.
4. **Imprecision (not counted).**
   - "Estimators agree at the ±5σ level" holds only in the sense that individual ±5σ bars overlap. Combined-σ differences reach 6.0σ, which the team's own D-2 lists. STATUS quotes only the 5.8σ example.
   - "80 crossings" silently uses 896 CZ. With all 918 it is 81, which is the draft's figure.
5. **Rules, TEAMS.md (reported, not counted as defects).**
   - There is no `PREREG.md` or `PREREG.sha16`, although a computational control (the final-layer statevector test) was run. The rcs deliverable is structural, so it is arguable whether one was required.
   - `DOWNLOAD_REQUEST.md`, `prereg_amendments.md`, `research/` and `analysis/` sit outside rule 2's enumerated list. The charter's own deliverable, "list the exact files", implies at least the request, so the charter is ambiguous.
   - No violations found:
     - The 1.6349e-3 value traces to `DRAFT_PREREG_RCS.md` l.72, so there was no illicit fetch of patch_xeb.json.
     - The Ollama brief does not state a conclusion; its three calls were sequential and all failed.
     - Only metadata APIs and abs pages were fetched.
     - Peak RSS recorded was 58 MB.

## Comparison with the team's own outputs (done after my numbers)

- `results/structure_d36.json` matches my values for all 7 orderings: crossings, totals, lossy events and saturation cycles. Its mid-bond cumulative crossings through cycle 35 match mine exactly.
- `results/final_layer_control.json` gives TVD 0.0 and 0.500195144305964, and a collision ratio of 0.99763526. These match mine to printed precision.
- No internal markdown-vs-JSON inconsistency was found.

## Bottom line

The team's substantive numbers all reproduce independently: the circuit structure, the final-layer argument, the cut and MPS bounds, the draft-model event counts, the paper-vs-release discrepancies, the download inventory, and the literature spot-checks. The defects are two misstatements outside the core analysis and one rounding overstatement.

RCS WAVE1: WRONG=2 OVERSTATED=1
