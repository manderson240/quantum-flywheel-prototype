# ERRATA — rcs wave 2 (appended 2026-09-25, wave 3). Append-only. PREREG.md / PREREG.sha16 left untouched (hash-frozen).

D50 (PREREG freeze sentence false). PREREG.md says: "Frozen before any XEB value, ideal probability, or collision ratio
was computed by this team. The only computation before freezing is `precheck.py`". Wrong. Wave-1
`teams/rcs/analysis/final_layer_control.py` (11:28) had already computed an exact statevector of a 15-qubit sub-circuit
of the FULL d36 circuit and its collision ratio 2^m Σp² − 1 = 0.9976 (`teams/rcs/results/final_layer_control.json`),
and it fixed the rz/rx sign conventions used in PREREG §3. Correct statement: no d36 PATCH probability, patch XEB
value or count-based quantity was computed before the freeze. The reproduction result (32/32 EXACT) is unaffected.

D51 (5.8σ understated as unqualified). STATUS §6 repeats "mirror vs 3-patch 5.8σ" (also in teams/rcs/STATUS.md line 4
and prereg_amendments.md). That σ is shot noise only. The 15 d36 records scatter beyond shot noise (K3 χ² 26.8/14,
K4 29.3/14). The verifier's figure with only the 3-patch se Birge-inflated is ≈5.1σ. Wave 3 (pre-registered,
teams/rcs/wave3/) computes 5.81σ (shot), 5.06σ (3-patch inflated), 4.32σ (both sides inflated; mirror Birge 1.33
from 28 instance dof). (A post-hoc depth-scatter reading in wave 3 depends on whether d20 is included; see
teams/rcs/wave3/STATUS.md line 7 — not carried here.)
The d36 gap should be cited with the σ convention stated, never as a bare "5.8σ".
