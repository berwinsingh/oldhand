# Plan: Fix duplicate batches on CSV import retry

Mode: implement · Inputs: contract.md, trace.md, rca.md (research skipped: nothing new is added)

## Fix point
`importer/batches.py:35` `write_batch`, the one function with_retries re-runs (single production caller
cli.py:33; CSV and TSV both route through it). Make it all-or-nothing: rows and counters in one
transaction with one commit at the end; on any exception, `conn.rollback()` and re-raise. Explicit
rollback rather than `with conn:` because on Python 3.9.6 `with conn:` leaves a failed COMMIT's
transaction open (rca.md, probe 2). Rejected: an idempotency key or unique index (schema change, forbidden,
and not needed once the batch is atomic); a rollback in the cli.py lambda (misses the direct callers in
tests and any future caller); changes in with_retries (it has no connection).

## Siblings (covered, or not and why)
- TSV import: covered (same function).
- start_import, finish_import: single statement, not retried; not in the class. finish_import's commit after
  a failed batch now commits nothing extra, because the batch was rolled back.
- connect/start_import outside the try at cli.py:31: not covered, pre-existing, spin-off.

## Files and why
| file | change | why | criteria |
| --- | --- | --- | --- |
| importer/batches.py | write_batch: drop the commit at :42, wrap the body in try/except that rolls back and re-raises, single commit at the end | root causes 1 and 2 | AC1, AC2 |
| tests/test_importer.py | one regression test: progress fault after the insert, retried, stores the batch once with counters 1/2 | proves the fix | AC1 |
| importer/cli.py | none | still calls write_batch through with_retries; error paths unchanged | R1, R3, R4 |
| importer/retry.py | none | unchanged contract: retries transient errors | R1 |
| importer/db.py | none | schema unchanged (constraint) | all |

## Regression check
Unit: `tests/test_importer.py` `WriteBatchTest.test_retry_after_failure_after_insert_stores_batch_once`,
input `IMPORTER_FAULTS=progress:1` (the user's failing case at function level), asserts 2 records and
counters (1, 2). Mutation: replace `conn.rollback()` with `pass` in write_batch; the retry then joins the open
transaction and doubles the rows, so the check must fail (KILLED).
Command: `/usr/bin/python3 -m unittest tests.test_importer.WriteBatchTest -v`.

## Scenarios
| criterion | kind | title | surface | env |
| --- | --- | --- | --- | --- |
| AC1 | acceptance | two batches hit a transient fault and are retried; each batch stored once | cli | local |
| AC1 | failing-case | the user's exact case: `IMPORTER_FAULTS=progress:1 ... products.csv --batch-size 2 --retries 3` | cli | local |
| AC1 | negative | the fault outlasts the retries: exit 1, import failed, nothing doubled or half written | cli | local |
| AC2 | acceptance | messy CSV (BOM, CRLF, padded cells, quoted comma, unicode) under two faults stores each row once | cli | local |
| AC2 | messy | messy TSV, batch size 1, mixed faults before and after the insert | cli | local |
| R1 | regression | plain CSV import, no fault, same output and counts as before | cli | local |
| R2 | regression | `--dry-run` prints the count and creates no database file | cli | local |
| R3 | regression | every flag accepted as before; `--help` lists the same options | cli | local |
| R4 | regression | bad row on line 4: exit 2, message, import failed, first batch stored once | cli | local |
Environments: local only (the contract names no other).

## Blast radius and rollback
- Who: anyone running `importer import` (csv, tsv). Stored data: `records` and `imports` rows written per batch.
  Schema and row shape unchanged, so old code reads new data and the reverse.
- Behaviour change: when the retries are exhausted, the failing batch now leaves no rows (before: its rows stayed,
  often doubled, with counters not bumped). Judgement: correct and what the contract's negative case expects.
- Rollback: revert the one commit that touches importer/batches.py and tests/test_importer.py. No data or config
  to restore, nothing to restart (a CLI process per run).

## Delegation
| work | role | brief file |
| --- | --- | --- |
| contract, trace, rca, plan, build, review chair, final e2e, verdict | lead (Opus 5.5; Fable 5.1 not offered in this session) | - |
| review lenses contract, correctness | worker tier (Sonnet 5.5) planned; run by the lead in turn, no sub-agent tool | review/brief.md |
| QA scenarios | scout/worker tier planned; run by the lead in turn, no sub-agent tool | qa/briefs/*.md |
Independence is reduced throughout: this host exposes no sub-agent tool.

## Live and paid runs
None. Every check is local and free (unit tests, the replay harness, the CLI on temp databases). Budget: 0.

## Spin off
- connect/start_import sit outside the try at cli.py:31: a lock there prints a traceback instead of a message.
- Existing databases may already hold doubled batches; rca/probe_alternative.txt has the query that finds them.

## PRs
One change, one PR when authorized (not authorized: commit, push and PR are all "no").

## Assumptions
- observed: Python 3.9.6 `with conn:` does not roll back a failed COMMIT (rca/probe_commit_lock.txt).
- traced: write_batch has one production caller (cli.py:33).
- assumed: users run /usr/bin/python3 or another CPython whose sqlite3 module uses implicit BEGIN
  (`isolation_level=''`); the explicit rollback is correct either way.
