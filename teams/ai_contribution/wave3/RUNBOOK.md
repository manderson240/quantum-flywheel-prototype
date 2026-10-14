# Orchestrator runbook: wave-3 qualifier-procedure benchmark (PREREG sha16 b20ba288605a1338)

Run every command from `~/cohezion-labs/bluequbit-flywheel/teams/ai_contribution/wave3` with the system `python3`.
Do not open, grep or diff `corpus/` or `SEALED/` until all 12 verifier runs are complete (PREREG sec. 2:
blindness is procedural). `stage_runs.py` only copies; it never opens a copy's contents.

## 0. Integrity (all must pass; otherwise stop: PREREG sec. 9)

```bash
python3 score.py --self-test                 # 30 PASS, SELF-TEST OK
python3 score.py --mutation-test             # 5 KILLED, MUTATION TEST OK
python3 adjudication/merge.py --self-test    # MERGE SELF-TEST OK
python3 -c "import hashlib;b=open('PREREG.md','rb').read();m=b'## Addendum (written after freeze; excluded from PREREG.sha16)';i=b.find(m);print(hashlib.sha256(b[:i+len(m)]).hexdigest()[:16])"   # = b20ba288605a1338
sha256sum SEALED/key.json SEALED/assignment.json SEALED/pool.json build.py score.py VERIFIER_BRIEF.md QUALIFIER_BRIEF.md HARNESS_NOTE.md   # = PREREG sec. 2/4/5 and Addendum
```

## 1. Stage the 12 runs

```bash
python3 stage_runs.py     # 12 dirs ~/cohezion-labs/review_pkg_<hex>/ (each with _scratch/); prompts in briefs_sent/;
                          # runs/staging.tsv (run -> dir); runs/launch_order.txt (random, interleaves arms and copies)
```

## 2. Run the verifiers (in `runs/launch_order.txt` order; up to all 12 concurrently)

For each run id `R` (e.g. `B_Q_run1`), with `d` = its directory in `runs/staging.tsv`:

1. Spawn a NEW fresh-context agent (read, shell and Python tools; no network), with the SAME model for every run. Its entire prompt is the text of `briefs_sent/R.md`, verbatim. Say nothing else.
2. Append `R<TAB>model-id` to `runs/models.tsv`.
3. Audit the transcript (PREREG sec. 4). The run is VOID if it did any of these:
   - read, listed or searched outside `d`;
   - wrote outside `d/_scratch/` and `d/VERIFICATION.md`;
   - made any web or network call.
4. If it succeeded, run `cp "$d/VERIFICATION.md" runs/R.md`, then `rm -rf "$d"`.
5. If it crashed, timed out, was VOID, or its file has no `FINDINGS=` line: run `python3 stage_runs.py --one R`. This makes a fresh directory with the same prompt text, and the new directory is appended to `staging.tsv`. Re-run it ONCE with a new agent.
6. If the re-run also fails, run `touch runs/R.MISSING`. Never impute; never re-run after any score has been seen.
7. Record each VOID or MISSING run, with its reason, in `runs/run_log.md`.

## 3. Preliminary scoring (lists the items to adjudicate; no verdict is final yet)

```bash
python3 score.py --key SEALED/key.json --corpus corpus --reports runs > runs/prescore.txt
```

## 4. Independent adjudication (two adjudicators; PREREG sec. 6)

```bash
python3 adjudication/make_packet.py          # adjudication/packet.jsonl + adjudication/SEALED/map.json (arm stripped)
for N in adj1 adj2; do
  a=~/cohezion-labs/adj_pkg_$(openssl rand -hex 4)
  cp -a SEALED/originals "$a"; mkdir "$a/_adjudication" "$a/_scratch"
  cp adjudication/packet.jsonl "$a/_adjudication/"
  sed "s#{ADJ}#$a#g; s#{NAME}#$N#g" adjudication/ADJUDICATOR_BRIEF.md > "$a/_adjudication/BRIEF.md"
  echo "$N $a" >> adjudication/staging.txt
done
```

For each adjudicator:
1. Spawn a NEW fresh-context agent. It must not be the orchestrator, this team, or any verifier. Its prompt is the text of `$a/_adjudication/BRIEF.md`.
2. Audit it as in step 2.
3. Copy `$a/_adjudication/adjN.json` to `adjudication/A1.json` (or `A2.json`).

```bash
python3 adjudication/merge.py --packet adjudication/packet.jsonl --map adjudication/SEALED/map.json \
  --a1 adjudication/A1.json --a2 adjudication/A2.json --out adj.json --third-packet adjudication/third_packet.jsonl
```

Exit code 2 means there are disagreements:
1. Stage a third adjudicator the same way, with `third_packet.jsonl` copied in as `packet.jsonl`, and save its output as `adjudication/A3.json`.
2. Re-run the merge with `--a3 adjudication/A3.json`.
3. Record κ overall and κ located-only from the merge output.

## 5. Final score and result

```bash
python3 score.py --key SEALED/key.json --corpus corpus --reports runs --adjudication adj.json --out score.json
```

Write `RESULT.md` from `score.json` → `summary`:
- `verdict` and `verdict_text`, **verbatim** (PREREG sec. 7), whatever the numbers are;
- the headline numbers: `qual_counts`, `qual_recall`, `qual_diff` with `qual_diff_ci`, `qual_ci` per arm, `other_counts`, `fp_upper` and `fp_lower`, `by_cross_doc_tell`, `runs_missing_*`;
- κ overall and κ located-only.

Label anything else as post hoc. Any departure from this runbook goes to `DEVIATIONS.md` with a timestamp and a
note of whether any score had been seen.
