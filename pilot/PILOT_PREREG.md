---
title: Pre-registration — agent vs grid/random search for classical simulation strategy selection
frozen: 2026-09-23, after table build + calibration, BEFORE any searcher (baseline or agent) was run
agent_prompt_sha256_prefix: a975e23078dd79f9
---

# Question
Does an LLM agent choosing classical-simulation strategies (method × setting) under a compute budget produce
more **verified-correct reports per instance, net of confident wrong reports**, than grid search, random search,
and a hand-written rule — and does it do so by *using* the query results (beats its own blind twin)?

# Instances (fixed)
`table.json`: 81 instances = 3 Floquet mixed-field Ising configurations on a 19-qubit heavy-hex patch
(tracker parameters θx=1.56567, θz=0.33879; (4.7, 0.3) colouring 5; (2.4, 0.9) colouring 5) × 9 depths × 3
observables. 9 strategies each (Pauli-path δ ∈ {1e-2, 1e-3, 3e-4, 1e-4}; MPS χ ∈ {4, 16, 32, 64, 128}), all run on
BlueQubit, 0 failures. Exact values from local statevector. Searchers never see exact values.

# Fixed parameters (chosen by calibration, before any searcher ran)
- Tolerance **TOL = 0.02**. Primary set = **non-trivial instances**, |exact| ≥ 0.02 (n = 60).
- Budget **B = 40** cost units per instance. Cost of a strategy = its median BlueQubit wall-seconds over all 81
  instances (fixed table, removes queue noise). Calibration: 29/60 (48%) non-trivial instances are solvable by at
  least one affordable strategy (inside the 30–70% band).

# Outcomes and metrics
Each episode ends in: report (estimate) | abstain | invalid (unparseable reply, unaffordable/unknown strategy,
transport failure). Scoring: success = report within ±TOL (+1); certified-wrong = report outside ±TOL (−1);
**invalid = −1**; abstain = 0. **Primary metric: net = (success − certified_wrong − invalid) / n.**
Secondary: success, certified-wrong, abstain, invalid counts; mean compute spent; everything per configuration;
all-instance (incl. trivial) results.

# Arms
- grid: strategies in fixed interleaved cost order; report when two successive same-family queries agree within TOL.
- random: same stopping rule, random order, 50 seeds (reported as the median seed's net and the distribution).
- rule: best affordable strategy of each family; report their mean if they agree within TOL, else abstain.
- agent (local): Qwen3.6-35B-A3B-MTP-GGUF via Lemonade, frozen prompt, thinking off, ≤ 8 steps, 3 repeats.
- blind agent (placebo): same model/prompt, query values hidden; 1 repeat.
- agent (cloud) + blind: deepseek-v4-flash:cloud via Ollama; same protocol.
- References (NOT searchers, chosen with hindsight of exact values): best single strategy; most expensive
  affordable strategy. Reported, excluded from the verdict.

# Verdict (per agent back end; the local agent is primary)
SUPPORTED only if ALL hold on the non-trivial set:
1. net(agent, mean of repeats) − max(net(grid), net(random, median seed), net(rule)) > noise floor, where
   noise floor = max − min of the agent's net across its repeats;
2. the hierarchical bootstrap 95% CI (resample configurations, then instances) of net(agent) − net(best baseline)
   excludes 0;
3. net(agent) − net(blind agent) > noise floor.
Otherwise **NOT SUPPORTED**. A null or negative result is reported unchanged in the application; no prompt, TOL,
budget or instance change after the first agent run.
