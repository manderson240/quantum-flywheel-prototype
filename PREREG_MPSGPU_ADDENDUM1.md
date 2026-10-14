# Addendum 1 to PREREG_MPSGPU.md: measure GPU cost scaling (frozen 2026-09-28, after step 1, before any further job)

Why an addendum: step 1 passed (mps.gpu 0.5583479436 vs mps.cpu 0.5583479437 at χ = 512 on 51qx30c) and cost $1.89 in
0.551 h. Steps 2–3 were NOT RUN by the frozen rule (χ = 2048 predicted $121 / $176 and 35 / 51 h from an ASSUMED χ³ scaling).
$22.39 of expiring credit remains. This addendum does not rescue steps 2–3; it measures the two scaling factors that the
prediction assumed, so the application's GPU budget rests on measured numbers. It adds no new physics claim.

Jobs, in order (each also a second validation, since mps.cpu values exist):
A. 74qx27c, mps.gpu, χ = 512 (qubit/circuit scaling). mps.cpu reference 0.5435972771734179. Predicted $1.89·74/51 = $2.74.
B. 51qx30c, mps.gpu, χ = 1024 (χ scaling). mps.cpu reference 0.5383666430889399. Predicted $1.89·8 = $15.12, 4.4 h.
Rule: a job runs only if spent + predicted ≤ CAP ($25.00) and predicted time ≤ 7 h, with the predictions updated from
measured cost after A (B's prediction stays $1.89·8). Same backstop as the main pre-registration (cancel if elapsed × rate
would pass CAP, or at 7.5 h; rate = $1.89/0.551 h). No retries.
Validation per job: |mps.gpu − mps.cpu| ≤ 1e-3, else report the disagreement.
Reported quantities: measured cost and wall time per job; the exponent α = log2(C_B / C_1) for χ 512 → 1024; the ratio
C_A / C_1 for 51 → 74 qubits; the re-costed χ = 2048 and χ = 4096 predictions from measured α, labelled as extrapolations.
