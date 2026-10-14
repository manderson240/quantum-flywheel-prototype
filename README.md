# Verifier-gated classical tests of quantum-advantage candidates — prototype

Prototype code, results and pre-registrations behind an application to BlueQubit's Quantum Flywheel program
(Track 02: AI for breaking quantum-advantage claims). Author: Michael Anderson (independent). Published 2026-10-14,
after all results below were obtained; the pre-registrations were hash-frozen locally, not publicly filed in advance.

**Design principle:** an AI agent proposes classical simulation strategies (method × truncation × bond dimension);
an external verifier decides what counts: exact answers at small sizes, and at scale, agreement between independent
method families under a pre-registered criterion.

## What is here
| Path | Contents |
|---|---|
| `results/` | BlueQubit job outputs (JSON) for the Floquet-Ising oracle points (19–33 qubits), the 51-qubit tracker sweep, OTOC echoes and the MPS ordering sweep; also 2026-09-23 snapshots of the tracker's submission/model lists (`tracker_*_2026-09-23.json`, third party, Apache-2.0) |
| `PATCH_PREREG*.md`, `PREREG_MPSGPU*.md`, `RESULT_*.md` | pre-registered 27/33-qubit bracket tests and MPS scaling runs, with outcomes |
| `pilot/`, `pilot2/`, `pilot_nli/` | the pre-registered AI-agent pilots (frozen prompts and hashes, runs, analysis) |
| `rgs/` | exact graph-state / cut-rank method for IBM's 70-qubit random-graph sampling candidates, validated against statevector on slices; GPU runbook (`rgs/README.md`) |
| `teams/rcs/` | BlueQubit 61-qubit random-circuit claim: patch-XEB reproduction, mirror-proxy waves 2–7 with pre-registrations and deviations |
| `teams/floquet/`, `teams/qpu/` | Floquet NLCE study; QPU mirror-calibration waves 8/8b |
| `teams/verification/` | independent verifier reports on the research waves (one per wave) |
| `teams/ai_contribution/` | sealed-key verifier benchmark: pre-registrations, builder, scores and adjudication tables (the planted-defect corpora and the adjudication packets, which quote application drafts, are omitted) |
| `tracker/` | circuits and data files from the Quantum Advantage Tracker (third party, Apache-2.0; see `tracker/NOTICE.md`) |
| `check_claims.py` | recomputes the numbers in the application from raw files |

## Reproduce
```bash
pip install qiskit numpy scipy quimb cotengra bluequbit   # Python ≥ 3.10
python check_claims.py
```
`check_claims.py` never submits jobs. In this public copy it runs the first **82 of 153 checks (all PASS)**, recomputed
from `results/`, the pilots and the tracker circuits, and then exits with a `FileNotFoundError` (exit code 1) at the
first check that reads the application text or third-party paper excerpts, which are not redistributed here. The full
run on the private tree (153/153 PASS) is in `CHECK_CLAIMS_FULL_RUN_20261014.txt`. Scripts that submit BlueQubit jobs
read `BLUEQUBIT_API_TOKEN` from the environment.

## Pre-registration hashes (first 16 hex digits of SHA-256 of the file as shipped)
| File | SHA-256 prefix |
|---|---|
| `PATCH_PREREG.md` | `ad33761e66880b43` |
| `PATCH_PREREG_27CYC.md` | `037116030b0d9dc4` |
| `PREREG_MPSGPU.md` | `6c7c99f8d1508af6` |
| `PREREG_MPSGPU_ADDENDUM1.md` | `951581ccf2fee151` |
| `pilot_nli/PREREG.md` | `6d6f55e2f01e3389` |
| `rgs/PREREG_UNDOPED_XEB_LOCAL.md` | `3e7bf7dd9a22d2d6` |
| `teams/qpu/wave8/PREREG.md` | `c29f1ce2d3ca4d2c` |
| `teams/qpu/wave8b/PREREG.md` | `a9dc195995516c58` |
| `teams/rcs/wave6_v2diag/PREREG.md` | `bd0b051e5df63034` |
| `teams/rcs/wave6_rep224/PREREG.md` | `4829ad8d514ea995` |
| `teams/rcs/wave7/ADDENDUM_POSTDEADLINE.md` | `9cfffd32ce2bcd1d` |

Further frozen files carry their own `*.sha16` (or `*.sha256`) next to them. These hashes were recorded locally at
freeze time; they show the files have not changed since, not when they were frozen.

## Notes for readers
- Several pre-registrations and drafts carry an internal header such as "Private; not to be posted". These labels
  date from before 2026-10-14, when the author decided to publish the prototype. Frozen files are left unedited
  because editing them would break their hashes; the drafts are left as written.
- Two pre-registrations are unfrozen drafts for the program period and have not been run:
  `teams/rcs/DRAFT_PREREG_RCS.md` (finite-fidelity MPS sampling of arXiv:2609.28657) and `rgs/PREREG_UNDOPED_XEB.md`
  (parked GPU scoring of IBM's undoped samples). Each will be revised and hash-frozen before any program compute.
- `teams/rcs/wave6_rep224/` is a post-hoc, pre-registered replication of the 224.08 figure; its verdict is
  INCONCLUSIVE (one cell not run), as recorded in its RESULT.md.
- Some frozen files cite paths that are not shipped here (internal notes, the application text).

## Not included
- The application text itself, the planted-defect copies of it used by the sealed-key benchmark, and the adjudication
  packets that quote application drafts.
- Third-party data: Manabe, Gu & Pan (doi:10.5281/zenodo.21912448, CC-BY-4.0); IBM doped-Clifford circuits
  (doi:10.5281/zenodo.22233383, CC-BY-4.0; never unpickle the `.pkl`); IBM's undoped samples (tracker issue #151).
- Literature captures and paper excerpts, the internal review rounds of the application, and GitHub issue comments.

Some logs contain absolute paths from the machine the runs were made on; they are informational only.

## Provenance
Code and analysis were designed, run and checked by AI agents under the author's direction, 2026-09-23 to 2026-10-13.
Deviations from pre-registrations are recorded next to them (`DEVIATIONS.md`, addenda).

## License
Our code and derived data: Apache License 2.0 (`LICENSE`). Third-party files keep their own licences.
