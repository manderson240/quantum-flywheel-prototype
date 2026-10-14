# Orchestrator runbook: planted-defect benchmark (PREREG sha16 04570ab6a4efeb79)

Run all commands from `~/cohezion-labs/bluequbit-flywheel/teams/ai_contribution/wave2`. The interpreter is the
system `python3` (qiskit 2.5.2 imports).

Do not open, grep or diff `corpus/` or `SEALED/` until all 8 arm-A runs are complete (PREREG §2: blindness is
procedural).

## 0. Integrity

```bash
python3 score.py --self-test          # expect 22 PASS, SELF-TEST OK
python3 run_armB.py --dry             # expect DRY OK
python3 -c "import hashlib;b=open('PREREG.md','rb').read();m=b'## Addendum (written after freeze; excluded from PREREG.sha16)';i=b.find(m);print(hashlib.sha256(b[:i+len(m)]).hexdigest()[:16])"   # = PREREG.sha16
sha256sum SEALED/key.json SEALED/assignment.json SEALED/pool.json   # = PREREG Addendum
```

## 1. Arm A: 2 runs per copy, 8 runs; every copy is treated identically

```bash
mkdir -p runs
for L in A B C D; do for r in 1 2; do
  d=~/cohezion-labs/review_pkg_$(openssl rand -hex 4); cp -a corpus/copy_$L "$d"; echo "$L $r $d"
done; done
```

For each staged directory `$d`:

1. Give a NEW fresh-context agent the text of `VERIFIER_BRIEF.md`. Replace `{PKG}` with `$d` and `{OUT}` with `$d/VERIFICATION.md`, and change nothing else.
2. Record the model id.
3. Audit the transcript (PREREG §4). Any access outside `$d`, or any web tool call, makes the run VOID; re-run it once.
4. Copy the output with `cp "$d/VERIFICATION.md" runs/${L}_run${r}.md`, then remove `$d`.

## 2. Arm B

```bash
mkdir -p runs/armB
python3 run_armB.py --original > runs/armB/baseline.txt
for L in A B C D; do python3 run_armB.py --copy corpus/copy_$L > runs/armB/$L.txt; done
```

## 3. Scoring

```bash
python3 score.py --key SEALED/key.json --corpus corpus --reports runs --armB runs/armB      # lists ADJUDICATE ids
```

An independent fresh-context adjudicator (PREREG §5–6, DEVIATIONS D1) writes `adj.json` with these keys:

- `"<L>_run<r>#<n>"` maps to `{"verdict": "HIT"|"MISS"|"PREEXISTING"|"FP"|"UNRESOLVED"|"MISLOCATED", ...}`.
- Add `"plant"` for a HIT.
- Add `"np_verdict"` for a MISS on a located finding.
- Add `"defect_id"` for PREEXISTING.
- It judges every AUTO_HIT too; a MISS overrules it.

```bash
python3 score.py --key SEALED/key.json --corpus corpus --reports runs --armB runs/armB --adjudication adj.json --out score.json
```

Report the result with the PREREG §9 templates, verbatim, whatever the numbers are.
