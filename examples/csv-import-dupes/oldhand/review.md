# Review: Fix duplicate batches on CSV import retry
At 4c043ed + uncommitted diff · Chair: lead:opus-5.5 · Independence: lenses run in turn by the lead (no sub-agent tool on this host)

Panel: contract and correctness only (trial cap of 2 lenses). By the skill's own rule the data lens also applied,
because the change alters a transaction boundary on stored records; its questions (partial writes, transaction
boundaries, duplicated data) were covered under correctness, but not as an independent memo.

| lens | reviewer | high | medium | low | survived | refuted | result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| contract | lead:opus-5.5 (in turn) | 0 | 0 | 0 | 0 | 0 | clear |
| correctness | lead:opus-5.5 (in turn) | 0 | 1 | 0 | 1 | 0 | fixed |

## Survived
- F1 (medium, correctness, tests/test_importer.py:85): the regression check did not guard root cause 2 (a failed
  COMMIT leaves the transaction open). Proven in a temp copy: a `with conn:` refactor passed the test while a real
  reader lock doubled the batch (4 records, counters 2/4). Resolution: fixed. Added
  `WriteBatchTest.test_retry_after_commit_lock_stores_batch_once`; mutate.py `conn.rollback()` -> `pass` KILLED (C10);
  the same refactor now fails it (review/variantA-after-fix.txt). Unit and replay rerun on the new tree (C11-C18).

## Refuted
None raised.

## Follow-ups
- Contract note: AC1's per-batch counts (2/2/1) are not visible through the CLI and the fixed QA brief forbids reading
  the database directly; QA agents prove totals via `importer list`, the lead's replay harness proves per-batch counts.
- Pre-existing, out of scope: connect/start_import outside the try at importer/cli.py:31 (traceback on a lock).

## Round 2
Correctness only, on review/diff-round2.patch: no findings (review/correctness-round2.md). No third round.
