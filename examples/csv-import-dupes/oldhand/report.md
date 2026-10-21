# Fix duplicate batches on CSV import retry: report

### Verdict: VERIFIED

| criterion | outcome | proof | counted checks | status | by | evidence | flags |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC1 | With a transient "database is locked" failure injected right after a batch's rows are written (`IMPORTER_FAULTS=progress:1`) and `--retries 3`, `python -m importer import samples/products.csv --batch-size 2` exits 0 and the database holds each batch exactly once: 5 records, batch_no counts 2/2/1, and `importer list` shows batches=3 rows=5 stored=5 | e2e | C19, C21, C28 | pass | lead:opus-5.5 | qa/evidence/S2/lead-1.txt |  |
| AC2 | A sloppy real-world file (UTF-8 BOM, CRLF line endings, padded cells; and the `.tsv` variant) imported under the same transient failure also stores each row exactly once | e2e | C22, C23 | pass | qa:worker | qa/results/S5.json |  |
| R1 | An import with no failures behaves as before: exit 0, prints `import <id>: 5 rows in 3 batches`, 5 records stored, `list` counters match | e2e | C24 | pass | qa:worker | qa/results/S6.json |  |
| R2 | `import FILE --dry-run` still prints `dry run: <n> rows in <m> batches, nothing written` and creates no database file | e2e | C25 | pass | qa:scout | qa/results/S7.json |  |
| R3 | The CLI keeps its flags: `import FILE [--db] [--retries N] [--batch-size N] [--dry-run]` and `list [--db]` are accepted exactly as before | e2e | C26 | pass | qa:scout | qa/results/S8.json |  |
| R4 | A file with a bad row still stops with exit 2 and `error: line <n>: bad row ...`, marks the import `failed`, and keeps the batches before the bad row stored once (added by trace: same error path in cmd_import) | e2e | C27 | pass | qa:worker | qa/results/S9.json |  |

**Why:**
- every live criterion has a passing check of its proof kind on the current tree and the lead recorded an e2e pass; no open high or medium findings

**Review findings**

| id | sev | lens | where | status | finding | note |
| --- | --- | --- | --- | --- | --- | --- |
| F1 | medium | correctness | tests/test_importer.py:85 | fixed | regression check does not guard root cause 2 (failed COMMIT leaves the transaction open); write_batch refactored to 'with conn:' -> test still OK, real reader lock during commit -> 4 records, counters (2, 4) for a 2-row batch on Python 3.9.6 | added WriteBatchTest.test_retry_after_commit_lock_stores_batch_once (real SHARED lock during COMMIT); mutate conn.rollback()->pass KILLED (C10); catches the 'with conn:' refactor (review/variantA-after-fix.txt: 4 != 2); unit rerun C11-C13, replay rerun C14-C18 |

**Notes**
- C1 mutation check on AC1: KILLED
- C10 mutation check on AC1: KILLED

Computed by ledger.py from ledger.json at 2026-10-10T19:17:57+00:00 on tree 4c043ed41b:4a2697fb:e3b0c442. Not written by hand.

## Asked
No ticket. Stop a transient write failure plus retry from storing a CSV batch twice; no schema migration; keep the
CLI flags; prove it end to end. Criteria: AC1 retried batch stored once; AC2 the same for messy CSV/TSV; R1 normal
import; R2 dry run writes nothing; R3 flags unchanged; R4 bad-row path unchanged (R4 added by trace).

## Root cause
(traced + observed, rca.md) `write_batch` (importer/batches.py) was retried as a unit by `with_retries` but was not
atomic: it committed the rows before the progress update, and any failure inside its transaction, the COMMIT
included, left the transaction open on the shared connection, so the retry's INSERTs joined it. The user's "no
idempotency key" is true but not the cause; an atomic, rolled-back batch makes the retry safe without a schema change.
Observed on Python 3.9.6: `with conn:` does not roll back a failed COMMIT, so the fix rolls back explicitly.

## Changed
- importer/batches.py: write_batch is one transaction, a single commit at the end, `conn.rollback()` + re-raise on any
  exception. (traced: one production caller, importer/cli.py:33; CSV and TSV share it)
- tests/test_importer.py: two focused checks: the fault after the insert (build) and a real SHARED lock during COMMIT
  (review fix for F1).
No schema, CLI, retry or db.py change. Diff: 47 insertions, 13 deletions in 2 files (`git diff --stat`).

## Proof
- observed: unit suite 12/12 OK, baseline 10/10 (build/after-unit.txt, build/baseline-unit.txt); no new failures.
- observed: mutation `conn.rollback()` -> `pass`: KILLED by both focused checks (C1, C10; build/mutation.txt,
  review/mutation-round1.txt).
- observed: replay harness through the real CLI: failed set 0/5 -> 5/5, regression set 5/5 -> 5/5
  (build/baseline-replay.txt, build/after-replay.txt); real-lock probe 4 records -> 2 (rca/probe_commit_lock.txt,
  build/after-probe.txt).
- observed: QA 9/9 pass (qa/results.md), all cli surface, each with a transcript in qa/evidence/<id>/run.txt.
- observed, lead's own run: S2 (the reported case) on a fresh database: exit 0, `list` stored=5, sqlite3 shows
  batch_no 1/2/3 = 2/2/1 rows and no duplicate sku (qa/evidence/S2/lead-1.txt, C28). Spot check of S4's stored values:
  padding stripped, BOM handled, accented name intact (qa/evidence/S4/lead-spotcheck.txt).

## Prior art
Research skipped: nothing new was added. Reused the stdlib `sqlite3` transaction and `rollback()`.

## Review
Lenses contract and correctness (trial cap of 2; the data lens also applied by the skill's rule and was not run as
its own memo). F1 medium (regression check did not guard the failed-COMMIT path) fixed with a second focused check,
KILLED. Round 2 (correctness, the fix only): no findings. Refuted: none. Lows: none.

## Live runs
0 live or paid runs; no model calls. Sub-agents: 0 (this host exposes no sub-agent tool). 2 refuter briefs, the
review brief (2 lenses + round 2) and 9 QA briefs were run by the lead in turn.

## Not verified
- Independence: every review lens, refuter and QA scenario was run by the lead, not by independent agents. The
  ledger's `qa:worker` / `qa:scout` labels come from the scenario tier field, not from who ran them; the lead ran all of them.
- CPython 3.12+ behaviour (only /usr/bin/python3 3.9.6 here). The explicit rollback is correct either way (assumed).
- A real lock end to end through the CLI: shown in-process only (probe 1 and the second unit check); the CLI
  scenarios use the project's fault hook.
- Per-batch counts are checked by the lead and the replay harness only; the QA brief forbids reading the database.

## Follow-ups
- connect/start_import sit outside the try at importer/cli.py:31: a lock there prints a traceback.
- Existing databases may hold doubled batches from before the fix; rca/probe_alternative.txt has the query that finds
  them (within one import_id = retry duplicates; across import_ids = the same file imported twice, by design).
- The replay harness and probes live in .oldhand/ (git-excluded, in a temp folder): move them into the repo if wanted.

## Published
Nothing published: commit, push, PR, tracker and deploy are all "no" in contract.md.
