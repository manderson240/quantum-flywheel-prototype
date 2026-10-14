# Independent verification — rcs wave 2 (d36 patch-XEB reproduction), 2026-09-25

Verifier: fresh context, told to assume "REPRODUCED" is wrong. Wrote own recomputation
(`scratchpad/myxeb.py`, own regex parser + project `qasm_angle.angle`, own numpy statevector with fused
1q gates, own estimator transcribed from `rcs/estimators.py` / `rcs/io.py` read-only) BEFORE reading
`teams/rcs/wave2/reproduce.py`. Author code never executed. Counts via `np.load(..., allow_pickle=False)`.
Resources: MemAvailable 35–42 GiB at every run (floor 20 GiB never approached), `nice -n 10`,
`ulimit -v 2.5 GB`, peak RSS 219 MB. No jobs, downloads, posts, .env reads. Only this file written.

## Results table

| # | Claim | Team | Verifier | Verdict |
|---|---|---|---|---|
| 1 | sha256(PREREG.md)[:16] == PREREG.sha16 | 9102a014cee43c2c | 9102a014cee43c2c2adea15f… → match | CONFIRMED |
| 2a | Frozen before any d36 patch probability / patch XEB | frozen 12:09:18 | Data dir created 12:04:06 (counts 12:04:39, patch_xeb.json 12:04:40); between 12:04 and 12:09 only precheck.py ran (hashes/structure/np.load, no simulation); reproduce.py 12:10:34; one run 12:13:06–12:24:39. mtime/log evidence only (teams/rcs untracked in git) | CONFIRMED |
| 2b | PREREG text: "Frozen before any XEB value, ideal probability, or collision ratio was computed by this team"; "The only computation before freezing is precheck.py" | as quoted | False as written: wave-1 `teams/rcs/analysis/final_layer_control.py` (11:28) computed an exact statevector of a 15-qubit sub-circuit of the FULL d36 circuit and a collision ratio 2^m Σp² − 1 = 0.9976 (`results/final_layer_control.json`), and fixed the rz/rx sign conventions later used in PREREG §3. Not a patch of the patched circuits, no counts existed yet, so it cannot have tuned the comparison | OVERSTATED (false sentence, harmless to the result) |
| 3 | Criteria applied as written (32 units, EXACT ρ ≤ 1e-6, worst field sets unit tier) | yes | reproduce.py tier() and unit-worst logic match PREREG §5; pooled units compared to fidelity_vs_depth.json | CONFIRMED |
| 4 | K3 p0 i0 F | 1.6348946571526522e-3 | 1.6348946571526522e-3 (ρ vs released 7.2e-15; se ρ 1.6e-15; patch F ρ ≤ 1.0e-14; I_r ρ ≤ 4.0e-15) | CONFIRMED |
| 5 | K3 p3 i2 F | 2.081212835334243e-3 | 2.0812128353342525e-3 (ρ 5.8e-15; se 1.6e-16; patch ≤ 1.5e-14) | CONFIRMED |
| 6 | K4 p2 i1 F | 2.0162971121145574e-3 | 2.0162971121145574e-3 (ρ 1.7e-15) | CONFIRMED |
| 7 | K4 p4 i0 F | 1.7565449237083753e-3 | 1.756544923708375e-3 (ρ 6.2e-15) | CONFIRMED |
| 8 | Shots per circuit | 36,000 | 36,000 (= released `shots`) | CONFIRMED |
| 9 | Pooled 3-patch d36 | 1.839052397648685e-3 ± 4.085052970054307e-5 | IVW of the 15 released records: 1.8390523976486784e-3 ± 4.085052970054307e-5 = fidelity_vs_depth.json (1.8390523976486782e-3 ± 4.0850529700543075e-5) | CONFIRMED |
| 10 | Pooled 4-patch d36 | 1.999385896123155e-3 ± 3.216069760032845e-5 | 1.999385896123157e-3 ± 3.216069760032846e-5 | CONFIRMED |
| 11 | N2 (reversed within-patch bit order, K3 p0 i0) | F = −4.98174e-9 | −4.981739920334e-9 (reversing extraction only) | CONFIRMED |
| 12 | N1 wrong-circuit null | \|F\| ≤ 4.2e-8 | band reproduced with a different pairing (counts i1 vs circuit i0): F = 1.34e-8 | CONFIRMED |
| 13 | Bit-order assumption confirmed | yes | yes — the evidence is the 1e-14 per-patch match (STATUS §4); the controls alone could not show it (problem 2) | CONFIRMED |
| 14 | "relative error ≤ 5e-14" (application text) | max ρ 4.4e-14 | my 4 circuits ≤ 1.5e-14; team comparison.json max 4.43e-14 | CONFIRMED |
| 15 | Scope limited to d36 patch path | yes | STATUS §6 and application text exclude other depths, mirror, hardware provenance, hardness | CONFIRMED |
| 16 | "BlueQubit's released 36-cycle data" | stated | arxiv.org/html/2609.28657: all six authors list BlueQubit, San Francisco; data/code at github.com/BlueQubitDev/rcs-nighthawk (hardware: IBM ibm_phoenix) | CONFIRMED |
| 18 | All used files match git blob SHA-1 at b9dd86b0 | match | recomputed sha1("blob <len>\\0"+bytes): patch_xeb.json 9cc84438…, patched_K3_d36.npz 49645c0b… = precheck.json values (2 files spot-checked), both present in wave-1 repo_tree_b9dd86b0.json (fetched 11:25, before download) | CONFIRMED |
| 19 | 5.8σ mirror-vs-3-patch gap "unchanged" (STATUS §6) | unqualified | arithmetic 5.81σ reproduced, but the σ is shot-noise-only while the 15 d36 records scatter beyond it (problem 3) | OVERSTATED |
| 17 | 76-word application text | 76 | 76 body words (83 incl. heading) | CONFIRMED |

## Ranked problems (none changes the verdict)

0. **(pre-registration wording) PREREG's freeze sentence is literally false** (row 2b). A wave-1 script
   had already computed an ideal statevector distribution and a collision ratio (full-d36 sub-circuit,
   15 q) and settled the gate-sign conventions. It could not bias this reproduction (no counts, not a
   patch, tolerance tiers are fixed and the match is at 1e-14), but PREREG should say "no d36 PATCH
   probability or patch XEB" and cite the wave-1 control instead of claiming no computation.
1. **(minor, reasoning) The null controls do not test the bit-order assumption; the exact match does.**
   N2 shows that ONE wrong permutation (full reversal) kills the signal, and N1 that wrong circuits do.
   They cannot show the chosen order is the authors'. That is shown only by the per-patch agreement at
   ρ ~1e-14 with the released `patch_fidelity` values, since any other within-patch permutation drives F_r
   to ≈0. A side note found by accident: a CONSISTENT relabelling (reverse both simulator order and
   extraction) is exactly invariant (reproduced released values at 1e-14), so "bit order" only matters as
   the relative map between simulated qubit index and shot bit. STATUS §3 "The assumed bit order is
   confirmed" is true; the sentence placement implies the controls confirm it.
2. **(minor, pre-registered rule is weak) `|F| ≤ 5·se` null rule is near-vacuous.** The delta-method se
   collapses with F near 0 (se ~2e-7), so the rule only says "≈0". The team discloses this and adds a
   post-hoc descriptive band (|F| ≤ 4.2e-8 vs smallest real F 1.44e-3). Honest, correctly labelled post-hoc.
3. **(context for the 5.8σ statement) Pooled se is shot-noise only; instance scatter exceeds it.**
   χ² of the 15 d36 records around their IVW mean: K3 26.8/14 (p ≈ 0.02, Birge 1.38), K4 29.3/14
   (p ≈ 0.01, Birge 1.45).
   The 5.8σ mirror-vs-3-patch gap (I recompute 5.81σ) becomes ≈5.1σ if only the 3-patch se is inflated
   by its Birge ratio. The team does not claim a new σ value; it says the wave-1 finding is "unchanged"
   and the 3-patch side is "independently reproduced". That is justified only in the narrow sense:
   the gap is not an arithmetic/implementation error in the patch path GIVEN the released counts and
   circuits. It does not exclude circuit/count mismatch smaller than gross (a gross mismatch would give
   F≈0), estimator bias, or instance-level systematics. Wording should keep to the narrow sense.
4. **(process) Pre-freeze ordering rests on mtimes + one log.** teams/rcs/ is untracked in git; no
   independent timestamp authority. Consistent, not provable.
5. **(rules) Self-reported deviation confirmed and nothing larger found.** precheck.py ran at 18.3 GiB
   (< 20 GiB floor); reproduce.py also read JSON/hash at 18.4 GiB before its first wait (light, logged).
   All heavy steps waited correctly (60+120+240 s, then ≥20 GiB). Peak RSS 317 MB < 0.9 GB. Qiskit used
   only in control P1 (gate calls, not its QASM loader) — within PREREG. Wave-1 file
   `teams/rcs/prereg_amendments.md` was edited in place at 12:26:56 with "[Corrected wave 2, D3x]"
   markers — allowed (inside teams/rcs/, not a forbidden file), disclosed, but it is in-place editing of
   an amendments document rather than an appended amendment.
6. **(instrument note, not load-bearing)** P1 reports the identical max |Δp| = 2.5587e-17 against both
   the dense-kron and the Qiskit comparators; plausible (same worst amplitude, float rounding) but not
   independent evidence of two checks. The real instrument check is the 1e-14 XEB match.
7. Application-text attribution "BlueQubit's released data" is correct (row 16).

## Bottom line

The reproduction is real: an independent implementation matches the released per-circuit fidelity, se,
per-patch fidelities and ideal-XEB values for 4 circuits (2×K3, 2×K4, different partitions/instances)
at ρ ≤ 1.5e-14, the pooled K3/K4 values follow from the released records by the IVW rule to the last
digit, and one null control each (N2 exact, N1 different pairing) reproduces. Scope claims are honest.
Only reasoning/wording nits.

Counted: WRONG = 0 (no numerical or scope claim is false). OVERSTATED = 2: row 2b (PREREG freeze
sentence; harmless to the result) and row 19 (5.8σ restated without the excess-scatter caveat).

RCS WAVE2: WRONG=0 OVERSTATED=2
