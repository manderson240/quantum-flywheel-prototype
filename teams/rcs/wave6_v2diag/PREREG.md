# V2 diagnostic: why BlueQubit mps.cpu and our own MPS disagreed on the 16-qubit analogue (pre-registered 2026-10-06)

POST HOC relative to wave 6. The original V2 stays **INCONSISTENT** as pre-registered (wave6 PREREG §9), and nothing here changes the wave-6 or wave-7 verdicts or factors. This file is frozen (sha256[:16] in PREREG.sha16) **before any job below is submitted**. Private; not to be posted.

## Background (already known before freeze)
- **V2 (wave 6):** 16q analogue (inst 0, derived d36 mirror = 18 forward cycles + inverse, restricted to qubits 0–15, input INPUT16), BlueQubit mps.cpu, 1e5 shots. Survival 0.199 / 0.028 / 0.618 at χ = 4 / 8 / 16. Exact survival = 1.
- **Own MPS** (teams/rcs/wave6/own_mps.py, swap-back routing, renormalised): 0.0046 / 0.0062 / 0.0244 at the same χ.
- Post hoc, the own no-swap-back variant gave 0.024 / 0.173 / 0.465 (results/posthoc_v2_routing.json).
- **D6:** at 61q, BlueQubit cancels U·U† at compile time (mirror build ≈ 1/200 of the forward build). Whether partial cancellation affected the 16q V2 is unknown.

## Hypotheses
- **H_cancel:** the V2 gap comes from compile-time (partial) U·U† cancellation, not from better truncation.
- **H_trunc:** BlueQubit's mps.cpu truncation (routing, ordering or truncation rule) yields higher fidelity than our own MPS on circuits that cannot be cancelled.

The two are not exclusive; both, one or neither may be supported.

## Cells
All cells are BlueQubit `mps.cpu`, 16 qubits, instance 0, input INPUT16 (wave6 plan.py), χ ∈ {4, 8, 16}, 1e5 shots, `mps_bond_dimension` = χ, force_run.
1. **F_χ:** forward only, the first 18 forward cycles (wave6 `load_instance(0)` forward segments [0:36], restricted to qubits 0–15). Cannot be cancelled.
2. **B_χ:** the V2 mirror with rx(π) on qubit 0 inserted between U and U† (blocks cancellation at the seam; the circuit is no longer the identity).
3. **R_χ** (χ ∈ {4, 8} only): an exact resubmission of the original V2 cell. This is a reproducibility check of the non-monotone 0.199 → 0.028.

That makes 8 jobs, $0 expected. Before submitting, every job goes through cost_ledger.ok_to_spend(0.0). If any job bills > $0, stop and report.

## Measures (local, exact 16q statevector as reference)
- **Instrument:** linear cross-entropy F̂ = 2^16 · mean_i p(x_i) − 1, where p is the exact output distribution of that cell's circuit. Keys use the q0-leftmost convention (V3 control).
- **BlueQubit:** F̂_BQ from its samples. The 95% CI is a nonparametric bootstrap over shots (2,000 resamples, seed 0).
- **Own MPS:** F_own = 2^16 Σ_x q(x) p(x) − 1, exact from the contracted own-MPS state q (swap-back routing, the wave-6 implementation unchanged). Also reported: the own fidelity |⟨ψ_exact|ψ_own⟩|² and the no-swap-back variant (descriptive only).
- **Control C0:** if F̂ computed on 1e5 samples drawn locally from p itself is not within [0.9, 1.1], the instrument is broken; stop.

## Decision rules
- **H_trunc SUPPORTED** if, at ≥ 2 of the 3 χ for F_χ, F̂_BQ > 2·F_own **and** the bootstrap CI lower bound of F̂_BQ exceeds F_own. **REFUTED** if at ≥ 2 of 3 χ the CI contains F_own or lies below it. Otherwise INCONCLUSIVE.
- **H_cancel SUPPORTED** if H_trunc is REFUTED on F_χ **and** on B_χ (same rule), while the original V2 survival exceeded own survival by > 2× at ≥ 2 of 3 χ (already true). **REFUTED** if H_trunc is SUPPORTED on both F_χ and B_χ (a truncation advantage then suffices). Otherwise INCONCLUSIVE.
- **R_χ:** report whether the resubmitted survival lies within the binomial 99% interval of the original. If not, V2 is not reproducible, and that is itself the finding.

## Consequences
- Whichever way it falls, the result is recorded in teams/rcs/wave6_v2diag/RESULT.md.
- The application text changes only if (a) a hypothesis is SUPPORTED, (b) the change fits field 4 as at most one clause labelled post hoc, and (c) two verifier families come back clean before the freeze. Otherwise it is Stage-1 work.
- If H_trunc is supported, it bears on the own-arm factors (2418 / 312.6): a better simulator would shrink them. That would be disclosed, not hidden.
