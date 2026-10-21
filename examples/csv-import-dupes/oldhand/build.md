# Build: csv-import-dupes

Mode implement. Pre-existing changes (`git status --short` before the first edit): none (build/git-status-before.txt
is empty). HEAD 4c043ed. Independence: built by the lead; no worker slices.

## Fix point and siblings
importer/batches.py `write_batch`: one transaction for the rows and the progress counters, a single commit at the
end, and `conn.rollback()` + re-raise on any exception. Covers CSV and TSV (same function) and the commit-time
lock (rca probe 1). start_import/finish_import are not in the class (rca.md).

## Changed files and why
| file | change | criteria |
| --- | --- | --- |
| importer/batches.py | removed the mid-function commit; try/except BaseException -> rollback -> raise | AC1, AC2 |
| tests/test_importer.py | `WriteBatchTest.test_retry_after_failure_after_insert_stores_batch_once` | AC1 |
Nothing outside plan.md's file table. Diff: build/diff.patch (26 insertions, 13 deletions).

## Regression check and mutation
- Check: `/usr/bin/python3 -m unittest tests.test_importer.WriteBatchTest.test_retry_after_failure_after_insert_stores_batch_once -v`
- mutate.py: `conn.rollback()` -> `pass`: KILLED (`AssertionError: 4 != 2`), file restored, sha256 verified
  (build/mutation.txt; ledger C1).

## Baseline against after
| check | baseline (4c043ed) | after |
| --- | --- | --- |
| unit `/usr/bin/python3 -m unittest discover -s tests -v` | 10 run, OK, 0 FAILED/ERROR (build/baseline-unit.txt) | 11 run, OK, 0 FAILED/ERROR (build/after-unit.txt) |
| replay `rca/replay.py` | failed set 0/5, regression 5/5 (build/baseline-replay.txt) | failed set 5/5, regression 5/5 (build/after-replay.txt) |
| real-lock probe `rca/probe_commit_lock.py` | probe 1: 4 records for a 2-row batch | probe 1: 2 records, counters (1, 2) (build/after-probe.txt) |
| lint / types | none configured in the repo | none |
New failures against the baseline: none. Pre-existing failures: none.

Ledger: C2-C4 unit (AC1, R1, R2), C5-C9 integration via the replay harness, which drives the real CLI on temp
databases (AC1, AC2, R1, R2, R4). R3 has no unit or integration check; QA covers it.

## Deviations from plan.md
None.

## Restarts QA needs
None: a CLI process per run reads nothing cached.

## Spin-offs
As in plan.md: connect/start_import outside the try (traceback on a lock); old databases with doubled batches.

## Not done
No commit (not authorized). No `with conn:` refactor of start_import/finish_import (not in the class).
