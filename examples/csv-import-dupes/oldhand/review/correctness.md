# correctness lens
Reviewer: lead:opus-5.5 applying the lens in turn (no sub-agent tool) · Read: diff.patch, importer/{batches,cli,retry,db,faults}.py, tests/test_importer.py, trace.md · Ran: in a temp copy (rsync of the tree): variant A below, the focused test, rca/probe_commit_lock.py
## Findings
### 1. The regression check does not guard root cause 2 (a failed COMMIT leaving the transaction open)
- Severity: medium · Confidence: high
- Where: tests/test_importer.py:85 (the only new check); the guarded line is importer/batches.py:52-54
- Failure: refactor write_batch to `with conn:` (a natural "simplification") -> the new test still passes (OK), but a real reader lock during COMMIT makes the retry double the batch: 4 records and counters (2, 4) for a 2-row batch on Python 3.9.6.
- Evidence: temp copy, variant A: `unittest ...test_retry_after_failure_after_insert_stores_batch_once` -> OK; `probe_commit_lock.py` -> `records, (batches_done, rows_done) = (4, (2, 4))`.
- Smallest fix: a second focused test that holds a real SHARED lock during the commit (file database, second connection), released between attempts.
## Checked and found fine
- Callers: cli.py:33 (only production caller), tests :76 :82 get the same return (None) and the same exceptions; with_retries still sees the original OperationalError (rollback re-raises it).
- rollback with no open transaction (fault before the insert) is a no-op on 3.9: G3 passes.
- rollback while another connection still holds SHARED succeeds: probe 1 after the fix stores 2 records.
- finish_import after a failed batch commits nothing extra: F5 after the fix stores 0 records, status failed.
- counters bumped once per batch on a retry: F1-F4 after the fix show (done, 3, 5) / (done, 2, 3).
- Concurrency: a second writer now waits for one transaction per batch instead of two short ones; still bounded by the 0.5 s busy timeout and the retries.
## Not checked
- CPython 3.12+ `sqlite3` autocommit modes (repo pins nothing; only /usr/bin/python3 3.9.6 exists here).
