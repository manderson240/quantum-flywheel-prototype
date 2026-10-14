# ERRATA — rcs wave 4 (appended 2026-09-25, wave 5; wave-4 PREREG.md / .sha16, STATUS.md and results/ untouched)

Source of findings: teams/verification/verify_rcs_wave4.md (RCS WAVE4: WRONG=0 OVERSTATED=2).

## D57 — "byte-identical" rerun claim is unverifiable and self-contradictory
- STATUS item 8 says the 16:03:51 rerun "gave byte-identical results". DEVIATIONS DV2 says "identical apart from
  rss_mb". Both are unverifiable: the 16:02:50 (non-compliant, MemAvailable 19.49 GiB) output was OVERWRITTEN by the
  16:03:51 run into the same files (results/bias_test.json mtime 16:03:56); no copy of the first output was kept.
  They also contradict each other, because rss_mb is a field inside bias_test.json.
- Correction: WITHDRAW "byte-identical" and "identical apart from rss_mb". Correct statement: "The 16:02:50 run
  breached the 20 GiB floor. Its output was overwritten by an unchanged, compliant rerun at 16:03:51. The two outputs
  cannot be compared. The reported numbers come from the compliant run only. The counts were independently reproduced
  by the verifier."
- Process fix adopted from wave 5 on: every run writes to its own timestamped directory; nothing is overwritten.

## D58 — the application text dropped the executed-circuit caveat
- proposed_application_text.md says, unconditionally, "A gate-count mismatch therefore cannot explain the 4.3σ
  mirror-versus-3-patch gap". The team's own post-hoc variant (posthoc_junction_variant.json) shows that if the
  barrier-protected duplicate middle CZ layer (20 CZ, CZ·CZ = I) were cancelled on hardware (782 CZ), the frozen rule
  would read PARTLY EXPLAINS (G_cmax 0.106, just under thr 0.1074 and above thr' 0.0964).
- Replacement text (supersedes the wave-4 proposed_application_text.md):
  "We counted gates in the released 36-cycle circuits. The mirror circuits have 802 CZ gates and the 3-patch circuits
  792–810, with the same Haar single-qubit and layer counts (plus a 61-gate preparation layer). In the released
  logical circuits a gate-count mismatch cannot explain the 4.3σ mirror-versus-3-patch gap. This assumes the executed
  mirror keeps its repeated middle CZ layer, as its barriers indicate; native compilation was not checked."

## Minor corrections (not counted by the verifier)
- STATUS item 6, "its treatment of this for the 918-CZ star: not found (UNKNOWN)", is imprecise. The paper states the
  treatment in one sentence, math rendered from the HTML alttext: "Direct verification of this set is out of
  reach—each ideal amplitude costs $\sim 10^{22}$ operations, i.e. about two days of the full reference machine, for
  $10^{6}$ amplitudes (Sec. III)—so the fidelity of the advantage configuration is taken from the two proxy
  estimators measured at the same depth, with no depth extrapolation." No gate-count correction is discussed. Wave 5
  tests this transfer.
- Pre-registered K3 min/max sensitivity (PREREG §3), omitted from wave-4 results. Recomputed here from the frozen
  constants in bias_test.json:
  - vs K3 max 810: ΔN_cz +8, G_c 0.00864, G_cmax 0.04949, G_all 0.06221. All are below thr 0.10739 and thr' 0.09636,
    so the result is CANNOT EXPLAIN.
  - vs K3 min 792: ΔN_cz −10, so every ΔN ≤ 0 and the result is CANNOT EXPLAIN (wrong way).
  - The verdict is unchanged.
