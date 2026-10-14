# PREREG_UNDOPED_XEB_LOCAL (frozen 3e7bf7dd9a22d2d6): probe outcome, 2026-10-09

## Steps completed
- **§C(0) timing probe:** GO.
  - The synthetic 2^27 message at 4 threads ran at 7.55 ns/entry, which projects to 114 s per 70-qubit amplitude. The threshold was ≤ 300 s.
  - Single-threaded it ran at 23.8 ns/entry (358 s).
  - See timing_probe.json.
- **P1, complex64 validation on slices:** PASS. Max relative error 6.7e-7, against a threshold of ≤ 1e-5 (P1.json).
- **Second order:** a deterministic greedy order over cut-ranks gives peak 2^31 and work 2^34.02. The annealed order gives 2^33.81 (greedy_order.json).

## P2, two-order 70-qubit check: NOT COMPLETED
- **What happened:** both attempts were SIGKILLed (exit 137) during the first full 70q amplitude.
- **Cause, measured:** the agent shell's cgroup has `memory.max` = 24 GiB. The amplitude needs about 32 GiB (F_old plus F_new, at 2^31 entries × 8 B each).
  - `memory.events` shows oom_kill 2.
  - The journal shows "The kernel OOM killer killed some processes in this unit" at 21:15:53.
- **Why the script's own guard missed it:** the guard read system-wide MemAvailable, not the cgroup limit. That is a guard defect.
- **Side effect on the shared machine:** at 21:11:18 the local inference fleet's admission gate refused a model load ("46.8 GB available < 48.0 GB").

## Status
- The run cannot be completed from the agent sandbox. Running outside the 24 GiB cap would hold about 32 GiB for 1–2 days on a machine shared with other workloads. That is Mike's decision.
- If it is not resumed by 2026-10-10 22:00Z, stop rule (a) applies: abandoned, and the application text is unchanged.
- No amplitude result exists. No application text changed.

## Options if resumed
1. Run in Mike's own terminal, outside the agent cgroup, with the guard fixed to read the cgroup or system limit, ideally when the fleet is quiet.
2. Keep F_new as a disk-backed memmap. Peak RAM would be about 16 GiB plus chunks, but performance is unknown and would need another probe.
3. Leave it for Stage 1 on a rented GPU, as the parent pre-registration originally planned.

## Decision (Mike, 2026-10-09): ABANDONED
Mike chose to abandon the local run to keep the shared machine light. It stays Stage-1 work, as the parent pre-registration planned (rented GPU). The application text is unchanged. Lesson: an in-script memory guard must read the process's cgroup `memory.max` as well as system-wide MemAvailable.
