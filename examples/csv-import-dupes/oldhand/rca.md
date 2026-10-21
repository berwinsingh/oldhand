# RCA: csv-import-dupes

Independence reduced: no sub-agent tool on this host; the lead ran both refuter briefs in turn.

## Symptom (failing case id, input location, environment, expected, observed)
- F1: `IMPORTER_FAULTS=progress:1 /usr/bin/python3 -m importer import samples/products.csv --batch-size 2 --retries 3`,
  local, fresh SQLite file. Expected 5 records (2/2/1). Observed: exit 0, prints `5 rows in 3 batches`,
  stores 7 records (batch 1 twice), and the imports row says `done, 3, 5`: the import reports success (observed,
  rca/baseline-replay.txt).
- No real failing record exists (no ticket, no user database); the case is the user's description replayed with
  the project's own chaos hook, plus probe 1 with a real lock and no hook.

## Ground checks (command -> what it printed)
rca/ground.txt: user berwinsingh; HEAD 4c043ed, clean tree; /usr/bin/python3 3.9.6, SQLite 3.54.0;
IMPORTER_FAULTS unset in the shell; `importer` imports from this repo. No deployed environment, cloud account or
remote config exists for this tool (local CLI), so the deploy and account checks do not apply. Other writers: none;
every replay uses its own temp database.

## Evidence (each item labelled observed / traced / assumed, with its source)
- observed: failed set F1-F5 all fail on baseline, regression G1-G5 all pass (rca/baseline-replay.txt).
- observed: real reader lock during commit, no hook: a 2-row batch stores 4 rows (rca/probe_commit_lock.txt, probe 1).
- observed: Python 3.9.6 `with conn:` does not roll back when its own COMMIT fails; `in_transaction` stays True and a
  later commit on the same connection persists the rows (probe 2).
- traced: importer/batches.py:42 commits the rows before :43-48 bump the counters; importer/retry.py:17 re-calls the
  whole function; importer/db.py:41 `finish_import` commits on the same connection after a failed batch.

## Root cause(s) (mechanism, file:line, confidence, what would prove it wrong)
write_batch (importer/batches.py:35-48) is retried as a unit by with_retries (importer/retry.py:12-24, called at
importer/cli.py:33) but is neither atomic nor rolled back on failure:
1. It commits the batch's rows (batches.py:42) before the progress update (:43-48). A transient failure after :42
   leaves the rows persisted; the retry inserts them again.
2. Any failure inside its open transaction, including the COMMIT itself, leaves that transaction open on the shared
   connection; the retry's INSERTs join it and the next commit (the retry's, or finish_import's at db.py:41) persists
   both copies.
Confidence: high. What would prove it wrong: a duplicate inside one import_id with no "transient error ... retry"
line on stderr for that run.
The user's hypothesis "no idempotency key" is true but not the cause: with an atomic, rolled-back batch a retry is
safe, because a failed SQLite COMMIT means nothing was committed. A key would also need a schema change (forbidden).

## Class and siblings (shape -> sites -> shared fix point; follow-ups outside scope)
Class: a non-idempotent, multi-statement write retried as a unit without a transaction boundary.
- Retried multi-statement writes: write_batch only (`grep -rnE 'with_retries' --include='*.py' importer`: one
  production call, cli.py:33). CSV and TSV share it. Fix point: write_batch.
- Not retried single-statement writes: start_import (db.py:33), finish_import (db.py:39). Not in the class.
- Follow-ups (out of scope): connect/start_import sit outside the try at cli.py:31, so a lock there prints a
  traceback; existing databases may already hold doubled batches (needs a data fix and sign-off).

## Replay sets (failed set, regression set, command, baseline)
- Command: `cd <repo> && /usr/bin/python3 .oldhand/csv-import-dupes/rca/replay.py` (+ `rca/probe_commit_lock.py`).
- Failed set: F1 csv progress:1; F2 tsv progress:1; F3 messy csv (rca/data/messy.csv) progress:2; F4 messy tsv
  progress:1; F5 fault outlasts retries (judgement: visible failure, no doubled or half batch); P1 probe 1.
- Regression set: G1 csv no fault; G2 tsv no fault; G3 fault before the insert; G4 dry run; G5 bad row on line 4.
- Baseline at 4c043ed: failed set 0/5 pass (P1 doubled), regression set 5/5 pass.

## Ruled out (suspect -> probe -> result)
- Fault hook artefact -> probe 1 with a real lock -> still doubles. Cleared.
- Retry wrapper or batch generator duplicating -> G1, G2, G3 -> exact counts. Cleared.
- Re-running the same file -> rca/probe_alternative.txt -> duplicates across import_ids, not within one. A separate,
  by-design behaviour; the query there tells the two apart on a real database.

## Refutation (angle -> verdict -> how it was answered)
- evidence -> stands (rca/refute-evidence.md): each fact re-derived; the 3.9-only `with conn:` behaviour is labelled
  observed on this runtime, so the fix uses an explicit rollback rather than relying on it.
- alternative -> stands, one alternative named for the user (rca/refute-alternative.md): re-runs duplicate across
  imports; diagnostic query given.
