# Wave 8 deviations (logged before the first QPU job)

D1 (2026-10-05, validation instrument): first builder validation ran mps.cpu at χ = 256. Floquet J1–J4 passed (|z| ≤ 1),
bit order passed, mirrors c = 1, 2 returned s in 1000/1000, but c = 3 gave 950/1000 and c = 4 808/1000. A 19-qubit MPS is
exact only at χ ≥ 2^9 = 512; the mirror doubles circuit depth, so χ = 256 truncates it. Stop rule fired; no QPU job was
run. Fix: validation re-run with χ = 512 (exact for 19 qubits). Circuits, jobs, analysis unchanged. First run kept as
results/validate_mpscpu_chi256.json.

D2 (2026-10-05 14:35 EDT, scheduling only; no result seen yet): J0 (057l763XcQOGI4c7) sat QUEUED > 30 min, and the credit
expires 2026-10-05, so sequential submission could not finish. Sequential runner stopped (J0 left queued, not resubmitted).
J1–J9 submitted at once in prereg order; J10/J11 NOT submitted (their condition, "J0–J9 billed as estimated", cannot be
checked in time). The per-job stop rule becomes a collection rule: if any job bills > $1.08, every job still queued is
cancelled. Max spend 10 × $0.72 = $7.20. Circuits, shots, analysis unchanged.

D3 (2026-10-05, found by council kimi-k3, after results): wave8.py computes the SEs of r_c and ρ as the across-qubit
spread (std over 19 per-qubit values / √19), whereas the PREREG says "binomial SEs". Recomputed with binomial SEs
(√(1 − r²)/√(19 × 1000)): M_pred unchanged; agreement still 0 of 4 depths (|z| 13.6, 4.1, 14.1, 35.8 versus 18.9-based
values in analysis.json). analysis.json is left as produced; both conventions are reported.
