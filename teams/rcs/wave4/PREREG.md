# PREREG — rcs wave 4: does a gate-count mismatch explain the d36 mirror-vs-3-patch gap?

Source: arXiv:2609.28657v1 (arxiv.org/html/2609.28657, read-only, fetched once to a scratchpad copy for exact text
search and then deleted); release repo pinned at commit b9dd86b0. Authors' code READ only, never executed
(rcs/circuits.py, rcs/patching.py, analysis/fidelity_vs_depth.py).

## 0. What I had already seen or computed BEFORE freezing this file (lesson D50 — exhaustive)
- K0.1 Wave-3 d36 numbers (teams/rcs/wave3/results/gap_d36.json): F_m = 2.2407541873352317e-3, se_m = 5.572416141157374e-5,
  B_m = 1.3260228091349258; F_3 = 1.8390523976486782e-3, se_3 = 4.0850529700543075e-5, B_3 = 1.3842077369180354;
  F_4 = 1.999385896123157e-3, se_4 = 3.216069760032846e-5, B_4 = 1.4460426427130502; ln gap g = 0.19756206228969023;
  z (both inflated) 4.317. Mirror fit per-cycle f = 0.871674814249307.
- K0.2 Wave-3 CZ counts of the patched d36 circuits (verified by the wave-3 verifier): K3 810×3, 801×6, 792×6
  (mean 799.2); K4 747×3, 720×6, 711×6 (mean 721.8). Wave-3 E4 constants c = 1.0800e-3 per CZ, c_max = 6.186e-3.
- K0.3 Wave-3 post-hoc depth readings (posthoc_depth_scatter.json), incl. K4 all-depth ratio 0.997.
- K0.4 manifest.json (refs/rcs-nighthawk-meta/data/circuits/manifest.json): I printed its first ~3000 characters,
  which show mirror CZ counts d04 = 94, d06 = 150, d08 = 190, d10 = 232 (d12 truncated) for all three instances.
  README states the full 36-cycle circuit has 918 CZ. I have NOT viewed the manifest entries for mirror d36 or for
  the patched circuits. Shallow mirror CZ per cycle (94/4 = 23.5 … 232/10 = 23.2) is above K3's 799.2/36 = 22.2,
  so the SIGN of the d36 mirror-minus-K3 CZ difference is PRIOR-INFORMED (expected: mirror ≥ K3). This test is
  therefore not blind on sign; its informative content is the magnitude and the decision against the bound.
- K0.5 Mirror d36 files: I have seen only the first 900 bytes of d36_instance0.qasm (OPENQASM 3 header and
  `input float[64] _theta_k_;` declarations). No gate line of any mirror file has been read or counted.
  I viewed the first 700 bytes of one K3 d36 file (header + rz/rx/rz lines).
- K0.6 Analytic, from the authors' code (not counted): the mirror d36 is prep RX(θ) layer + forward 18 cycles
  (colours A B C D repeated, pseudo-patch filter drops partition (cycle mod 5) of the five K=3 partitions) + exact
  inverse + measure. Before any removal, 18 forward cycles contain colours A,B ×5 and C,D ×4; doubled
  (A,B ×10; C,D ×8) with |A| = |C| = 29, |B| = |D| = 22 this gives 918 couplings, identical to 36 unpatched cycles
  (918). Differences in CZ count therefore come only from which boundary edges are removed in which colour.
- K0.7 Paper text (exact quotes, §1). No per-gate error model is stated in the paper.

## 1. Paper statements (exact quotes from the HTML text)
- "we run a mirror benchmark [38], consisting of a state-preparation layer, a forward random circuit U of d/2
  cycles, its exact inverse U†, and a readout. The survival probability—the probability of recovering the prepared
  bitstring—is a direct fidelity estimate for the d-cycle sequence U​U† and requires no simulation."
- "we mirror a pseudo-patched circuit constructed to match the K=3 patched family gate-for-gate within ∼2% while
  remaining connected: the forward circuit cycles through the five K=3 boundary-edge sets, omitting in each cycle
  only the currently active partition’s boundary gates"
- App. C: "the number of omitted gates per four-cycle period matches a K=3 patched circuit" and "the “cycle
  picture” and “gate-count picture” coincide on the x-axis by construction."
- "Coherent-error cancellation between the two mirror halves is suppressed by randomized compiling with 64
  Pauli-frame randomizations per circuit"
- Conversion: the mirror fit gives "a factor 0.872 per cycle [the fit of Fig. 2]" and "ε_q ≃ 2.3×10^-3 the
  per-qubit per-cycle error" (alttext `\epsilon_{q}\simeq 2.3\times 10^{-3}`). So the mirror survival at d = 36 is
  used directly as the fidelity of a 36-cycle circuit; the per-qubit error is −ln f / n. Any gate-count difference
  per cycle between the mirror and the circuit it stands for enters the comparison 1:1 in ln F.

## 2. What is counted (script count_gates.py, own line parser; angles via qasm_angle.angle(), never eval)
Circuits: mirror d36 instance 0,1,2 (PRIMARY); K3 d36 15 files, K4 d36 15 files (recount); full d36_logical and
d40_logical (secondary).
Parser: strip comments; one statement per `;`. Skip `OPENQASM`, `include`, `bit[..]`, `qubit[..]`,
`input float[64] …`. Recognised: `rz`, `rx`, `sx`, `x`, `cz`, `barrier`, `measure` / `c[..] = measure q[..]`.
Numeric parameters go through `angle()`. A parameter that is a declared `_theta_k_` name is counted by NAME as a
prep RX and never bound or evaluated. Any other statement or any `ValueError` → that circuit is MISSING.
Per circuit: N_cz; N_rx (noisy 1q: each Haar gate rz·rx·rz compiles to 2 SX + virtual RZ in both families —
this logical-to-native equivalence is ASSUMED, not tested); N_prep (rx with a _theta_ parameter); N_rz;
CZ layers = maximal runs of consecutive `cz` statements not interrupted by any other statement (barrier or gate);
number of CZ layers L; idle qubit-layers = Σ_layers (61 − 2·|layer|); per-qubit CZ exposure (61-vector);
per-coupler usage count.
Structural checks (reported; failure is reported, does not change counts):
- S1 mirror: the gate list after the prep layer is a palindrome under inversion — op k from the end is the inverse
  of op k (cz same pair; rz(a)↔rz(−a), rx(a)↔rx(−a), |Δ| ≤ 1e-9 mod 2π).
- S2 mirror forward half: CZ layer j (j = 0..17) as an edge set equals matchings[schedule[j mod 4]] minus
  layout.json partitions["3"][j mod 5].boundary_edges.
- S3 junction: the last forward CZ layer and the first inverse CZ layer are the same edge set (duplicate, CZ·CZ = I).
- S4 cross-check: manifest.json `cz` for mirror d36 and all 30 patched d36 files vs my count; my count is primary,
  any disagreement reported.

## 3. Model mapping counts to a fidelity bias
Comparator: N̄_K3 = plain mean of the 15 K3 d36 CZ counts (PRIMARY); sensitivity: min and max of the 15.
N_m = mean over the 3 mirror instances (executed variant: all CZ counted, junction duplicate included).
ΔN_cz = N̄_K3 − N_m (> 0 means the mirror has FEWER CZ, which would bias it HIGH, i.e. toward the observed gap).
Predicted ln-gap from CZ counts: G_c = c·ΔN_cz, c = ln(F_4/F_3)/(N̄_K3 − N̄_K4) = 1.0800e-3 (K0.2),
  se_c = sqrt((se_4·B_4/F_4)² + (se_3·B_3/F_3)²)/(N̄_K3 − N̄_K4) = 4.981e-4. G_c at c ± 2 se_c reported (exploratory;
  the verdict uses the point c).
Upper bounds:
- G_cmax = c_max·ΔN_cz, c_max = 36·(−ln f)/N̄_K3 = 6.186e-3 (all per-cycle decay on CZ).
- G_all = D·max(0, max_k ΔN_k/N_k^K3) over k ∈ {CZ, noisy 1q (N_rx, prep EXCLUDED — the allocation most favourable
  to the explanation), CZ layers L}, D = −ln F_3 = 6.2985 (all decay incl. SPAM attributed to gates). This is the
  maximum of Σ c_k ΔN_k over non-negative c_k with Σ c_k N_k^K3 ≤ D.
Variants reported (not verdict-setting): junction duplicate cancelled (N_m minus the duplicated layer);
prep counted as 61 RX or as the π half (30.5 on average) in the 1q category.
Uncertainty of the observed gap (FIXED here, D53): σ_ln = sqrt((se_m·B_m/F_m)² + (se_3·B_3/F_3)²) = 0.045087;
thr = g − 2σ_ln = 0.19756 − 0.09017 = 0.10739. BORDERLINE convention: σ_ln' = 0.0506 (wave-3 run-1 form),
thr' = 0.0964.

## 4. Decision rule (primary: mirror d36 vs K3 d36)
1. WRONG SIGN: if ΔN_k ≤ 0 for every k in G_all (mirror has as many or more noisy ops in every category) →
   "CANNOT EXPLAIN (count difference goes the wrong way)"; report the count-corrected gap g + c·|ΔN_cz| (and with c_max).
2. Else if G_c ≥ thr → "EXPLAINS".
3. Else if G_all < thr → "CANNOT EXPLAIN".
4. Else → "PARTLY EXPLAINS"; report G_c/g.
5. BORDERLINE: re-run steps 1–4 with thr'; if the verdict differs, the reported verdict is "BORDERLINE (flips with
   σ convention)", choosing neither side.
Also reported: whether N_m lies inside the K3 range [min, max]; |N_m − N̄_K3|/N̄_K3 against the paper's "∼2%"
(a larger value is a text/data comparison, not described as an error).
Secondary, no verdict weight: (a) same rule vs K4; (b) transfer to the full 918-CZ circuit (the fitted-star value):
G_full = c·(N_full − N_m) and c_max·(…) — the expected ln-difference between mirror-derived and full-circuit
fidelity from CZ counts alone; (c) per-qubit exposure and per-coupler usage, mirror vs K3 family mean
(descriptive; error heterogeneity per coupler is UNTESTABLE without calibration data).
Named, untestable here: coherent-error echo between halves (twirling efficacy), readout, drift, native compilation.

## 5. Missing / retry / resource rules
- Check MemAvailable before each Python run; if < 20 GiB wait 60,120,240,480,600,600… s up to 60 min, then the step
  is MISSING (floor never lowered). `nice -n 10`; RSS guard 0.9 GB (abort → MISSING).
- A run that raises may be retried once unchanged; a second failure → affected circuits MISSING.
- ≥ 2 of 3 mirror instances and ≥ 12 of 15 K3 circuits are required for a verdict; else verdict MISSING.
- Any convention change after results are seen is labelled POST-HOC and cannot change the verdict.
- No BlueQubit jobs, downloads, posting; json/qasm text only; nothing unpickled.
