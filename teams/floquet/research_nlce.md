# NLCE for real-time and Floquet dynamics: verified literature (floquet team, wave 1, 2026-09-25)

Every citation below was checked against its arXiv abs page on 2026-09-25, fetched from export.arxiv.org. The title, authors and abstract were read; the claims below restate what the abstracts say.

## Verified sources

| arXiv | Authors / title (as on the abs page) | What it establishes (from the abstract) |
|---|---|---|
| cond-mat/0611102 | Rigol, Bryant, Singh, *Numerical Linked-Cluster Approach to Quantum Lattice Models* | Introduces NLCE. The context is equilibrium. |
| 1401.2160 | Rigol, *Quantum Quenches in the Thermodynamic Limit* | NLCE for quenches, for 1D lattices, in the **diagonal ensemble** (infinite-time averages). This is not real-time dynamics. |
| 1701.02758 | Mallayya, Rigol, *NLCEs for quantum quenches in one dimensional lattices* | **The site-based NLCE can diverge where the maximally connected one converges.** The paper attributes this to the exponential number of clusters, and resummation only partly cures it. |
| 1710.07696 | White, Sundar, Hazzard, *Quantum dynamics from a numerical linked cluster expansion* | Real-time magnetization and correlations for the **2D** transverse-field Ising and XXZ models, starting from a product state. NLCE is "dramatically more accurate … at short-to-moderate times" than exact diagonalization. |
| 1711.01284 | Mallayya, Rigol, *Quantum Quenches and Relaxation Dynamics in the Thermodynamic Limit* | Real-time NLCE for hard-core bosons in 1D. Local observables relax exponentially "within the accessible times". |
| 2005.03104 | Richter, Heitmann, Steinigeweg, *…transverse-field Ising model: a numerical expansion in linked rectangular clusters* | 2D square-lattice TFIM quenches from polarized states, using rectangle-only clusters. Converged results reach times "competitive to other state-of-the-art" methods. |
| 1907.04261 | Mallayya, Rigol, *Heating Rates in Periodically Driven Strongly Interacting Quantum Many-Body Systems* | **NLCE used for periodic driving**: energy vs driving time, with an exponential heating regime. The drive here is a Hamiltonian (continuous-time) drive, not a gate circuit. |
| 1810.12320 | Mallayya, Rigol, De Roeck, *Prethermalization and Thermalization in Isolated Quantum Systems* | Title verified only. It is cited as prethermalization context, not as evidence about NLCE. |
| 2607.24937 | *Resolving Structure in Prethermal Floquet Dynamics with Precision Quantum Computation* | The originators' paper. Per the decision-path doc, it has zero hits for linked-cluster methods. |

## What is known
- In 2D, real-time NLCE is accurate only at short-to-moderate times (1710.07696, 2005.03104).
- The time at which it stops converging is set by how far correlations spread relative to the largest cluster.
- For site-based expansions, divergence is a documented failure mode (1701.02758).

## Not found (recorded as UNKNOWN, not ABSENT)
Two things were searched for:
- NLCE applied to kicked-Ising gate circuits or quantum-circuit benchmarks;
- NLCE applied to heavy-hex lattices.

Neither was found. The search used arXiv API abstract queries (`"linked cluster"` combined with kicked / circuit / Floquet / driven). The control query (`"linked cluster"` + quench) returned relevant hits. However, the "driven" query **missed 1907.04261**, even though that paper's title contains "Periodically Driven". This search engine is therefore unreliable for negatives, and I checked no citation chains. Two candidates came up that I did not use:
- 1711.00887 (a 2D Rydberg quench experiment);
- 2306.17839 (classical benchmarking of the IBM kicked-Ising circuit).
Neither abstract mentions NLCE, so neither is cited as NLCE evidence.

## The causal-cone caveat, measured here (geometry only: `results/cone_geometry.json`)
Maximum backward-cone size, in sites:

| Instance | c=1 | c=2 | c=3 | c=4 | Covers every site by |
|---|---|---|---|---|---|
| 27q patch | 7 | 16 | 25 | 27 | c = 6 |
| 33q patch | 7 | 17 | 29 | 33 | c = 7 |
| 51q | 7 | 17 | 33 | 44 | c = 10 |

An order-16 expansion is therefore guaranteed exact only up to c ≈ 2. Any agreement after that would have to come from relaxation or cancellation, not from causality.
