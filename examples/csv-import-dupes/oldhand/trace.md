# Trace: csv-import-dupes

Repo at 4c043ed (main, clean). Python /usr/bin/python3 3.9.6, SQLite library 3.54.0,
`sqlite3.connect()` default `isolation_level=''` (implicit BEGIN before INSERT/UPDATE/DELETE).
All hops opened by the lead; no scouts (one process, one subsystem).

## Path
| hop | file:line | what happens | timeout x retries | failure mode |
| --- | --- | --- | --- | --- |
| entry | importer/__main__.py:5 | `sys.exit(main())` | - | exit code from cmd_* |
| CLI parse | importer/cli.py:56-70 | argparse: `import FILE --db --retries --batch-size --dry-run`, `list --db` | - | argparse exit 2 on bad flags |
| dry-run branch | importer/cli.py:16-26 | reads all batches, counts, prints, returns before `connect` | - | BadRow -> exit 2; no DB touched |
| connect | importer/db.py:27-30 | `sqlite3.connect(path, timeout=0.5)` + `executescript(SCHEMA)` | busy timeout 0.5 s per statement | OperationalError propagates (not inside the try at cli.py:31) |
| start import | importer/db.py:33-36 | INSERT imports row, commit, return id | 0.5 s busy | uncaught -> traceback |
| read batches | importer/batches.py:13-32 | generator; `csv.DictReader`, `utf-8-sig`, tab for `.tsv`, `int(qty)`; yields lists of `batch_size` | - | BadRow raised lazily inside the loop at cli.py:32 |
| retry wrapper | importer/retry.py:12-24 | calls fn; on OperationalError containing "database is locked"/"busy" retries up to `retries` more times, sleeping 0.05*attempt | `--retries` (default 3) -> 4 attempts | re-raises after the last attempt or for non-transient errors |
| batch write | importer/batches.py:35-48 | `maybe_fail("insert")`; executemany INSERT records; **commit (42)**; `maybe_fail("progress")`; UPDATE imports counters; commit (48) | 0.5 s busy per statement | a failure after line 42 leaves the batch's rows committed and the counters not bumped; the retry re-runs the whole function and inserts the rows again |
| finish | importer/db.py:39-41 | UPDATE imports.status, **commit** | 0.5 s busy | commits whatever transaction is open on the shared `conn` |
| failure handling | importer/cli.py:36-43 | BadRow -> status failed, exit 2; sqlite3.Error -> status failed, exit 1 | - | both call finish_import on the same connection |
| render | importer/cli.py:45-46, 49-53 | prints `import <id>: <rows> rows in <batches> batches`; `list` prints counters and COUNT(records) | - | - |

No queue, no external service, no HTTP: hops "API", "auth", "queue", "external" do not exist.

## Callers, readers and siblings (grep commands, then hits marked changes / must keep working)
Commands (run from the repo root; quote the glob under zsh):
- `grep -rnE 'write_batch' --include='*.py' importer tests`
- `grep -rnE 'with_retries' --include='*.py' importer tests`
- `grep -rnE '\.commit\(' --include='*.py' importer tests`
- `grep -rnE 'records' --include='*.py' importer tests`
- `grep -rnE 'batches_done|rows_done' --include='*.py' importer tests`
- `grep -rnE 'maybe_fail|IMPORTER_FAULTS' --include='*.py' importer tests`
- `grep -rnE 'isolation_level|BEGIN|rollback|with conn' --include='*.py' importer tests` -> no hits

Hits:
- importer/batches.py:35 `write_batch` definition: **changes**.
- importer/cli.py:33 the only production caller (CSV and TSV both route here): must keep working.
- tests/test_importer.py:76, :82 direct callers: must keep working.
- importer/retry.py:12 `with_retries`, callers cli.py:33 and tests :47 :55 :65 :82: must keep working (no change planned).
- commits: db.py:35 (start_import), db.py:41 (finish_import), batches.py:42 and :48: batches.py ones **change**; db.py:41 matters because finish_import commits on the same connection after a failed batch (see failure handling).
- readers of `records` and the counters: db.py:46-47 (`list`), tests :77 :78 :83: must keep working; `list` is the observation point for AC1.
- fault hook: batches.py:37 and :43 call sites, faults.py:15 reads the env var: must keep working (QA uses it).
- Siblings sharing the mechanism: none outside write_batch. TSV is not a separate path; it shares read_batches/write_batch (AC2 covers it).
- Error path group (BadRow mid-file at cli.py:36) had no R: added R4 to contract.md (sync: 6 live criteria).

## Processes and phases
One process: the CLI. Every phase runs in it, in order; no async step, no 202. A silent drop would
only show in `importer list` (counters vs stored count) or a direct SQL count.

## What the runtime reads (config keys, precedence, caches, prompt and document copies)
- CLI flags only (cli.py:59-63); no config file, no env vars except `IMPORTER_FAULTS`
  (faults.py:15, re-read on every call; per-process counter `_seen` at faults.py:11).
- No caches. No prompt or template copies.

## Timeout budgets
Per batch, worst case: attempts = retries + 1 = 4 (default). Each attempt runs up to 2 write
statements plus 2 commits, each may wait the 0.5 s busy timeout -> about 2 s per attempt, 8 s per
batch, plus sleeps 0.05+0.10+0.15 = 0.3 s. No caller budget above it (interactive CLI); no client
without an explicit timeout.

## Trust boundaries
- File content (user input) enters at batches.py:17-26; values go into parameterised SQL
  (batches.py:39, 45), so no SQL injection. Bad rows raise BadRow.
- `--db` path is user chosen (cli.py:60); same trust as the user running the CLI.
- No auth, no secrets.

## Reuse, tests, commands, test data
- Reuse: the stdlib connection context manager (`with conn:` commits on success, rolls back on
  an exception), or `conn.rollback()`. Nothing in the repo already wraps a transaction.
- Tests: `/usr/bin/python3 -m unittest discover -s tests -v` (10 tests, all pass at 4c043ed).
- Run locally: `/usr/bin/python3 -m importer import samples/products.csv --db /tmp/x.db --batch-size 2`.
- Test data: samples/products.csv (5 rows), samples/products.tsv (3 rows); fault hook
  `IMPORTER_FAULTS=progress:1` (transient after the rows are written) and `insert:1` (before).

## Unknowns (what, why it matters, how to find out)
- Whether real-world transient failures also hit the COMMIT itself (SQLITE_BUSY at commit). Matters:
  on Python 3.9 a failed commit may leave the transaction open, so a retry would add to it. Find out:
  rca probe that makes commit fail once.
