# Fix duplicate batches on CSV import retry

Source: prompt  ·  Mode: implement

## Problem / expected behaviour
Current (as reported, premise unverified; rca checks it): a transient write failure during a CSV
import, followed by the retry wrapper retrying the batch, stores that batch's rows twice.
Expected: one import stores each batch's rows exactly once, also when a batch write was retried.
Concrete failing case (from the report, to be reproduced in rca): import a CSV with a transient
"database is locked" error on the write step after rows were inserted, with `--retries N` >= 1.

Worked example of "one persisted batch" (ASSUMED reading, see Open questions): `samples/products.csv`
has 5 rows; with `--batch-size 2` it is 3 batches (2, 2, 1 rows). After one import the `records`
table holds 5 rows for that import, `batch_no` 1, 2, 3 hold 2, 2, 1 rows, and the import's
`imports` row reads `batches_done=3, rows_done=5`, as `python -m importer list` prints them.

## Acceptance criteria
- AC1: With a transient "database is locked" failure injected right after a batch's rows are written (`IMPORTER_FAULTS=progress:1`) and `--retries 3`, `python -m importer import samples/products.csv --batch-size 2` exits 0 and the database holds each batch exactly once: 5 records, batch_no counts 2/2/1, and `importer list` shows batches=3 rows=5 stored=5 (proof: e2e)
- AC2: A sloppy real-world file (UTF-8 BOM, CRLF line endings, padded cells; and the `.tsv` variant) imported under the same transient failure also stores each row exactly once (proof: e2e)
- R1: An import with no failures behaves as before: exit 0, prints `import <id>: 5 rows in 3 batches`, 5 records stored, `list` counters match (proof: e2e)
- R2: `import FILE --dry-run` still prints `dry run: <n> rows in <m> batches, nothing written` and creates no database file (proof: e2e)
- R4: A file with a bad row still stops with exit 2 and `error: line <n>: bad row ...`, marks the import `failed`, and keeps the batches before the bad row stored once (added by trace: same error path in cmd_import) (proof: e2e)
- R3: The CLI keeps its flags: `import FILE [--db] [--retries N] [--batch-size N] [--dry-run]` and `list [--db]` are accepted exactly as before (proof: e2e)

## In scope / out of scope
In: the batch write path used by `importer import` for .csv and .tsv, and its retry behaviour.
Out: a schema change of any kind (new column, unique index, idempotency-key table); new CLI
flags; the fault-injection hook's design; performance.

## Context the user gave (assumptions, changed requirements, constraints, partial work, files, links)
- "No ticket." The prompt is the whole source.
- The user's diagnosis: "no idempotency key". Treated as a hypothesis for rca, not as the fix.
- Constraints: no schema migration; keep the CLI flags.
- Requested proof: "Prove it end to end."
- Partial work: none. Branch `main`, clean tree at 4c043ed (git status --short empty).
- Project instruction files: none (no AGENTS.md, CLAUDE.md, GEMINI.md, .cursor/rules). README says
  schema changes need a migration and sign-off; `IMPORTER_FAULTS` is the project's own chaos hook.

## Affected users, roles, tenants, data, integrations, environments
- Anyone running `python -m importer import`; stored data in the `records` and `imports` tables of
  the SQLite file passed with `--db`. Environment: local only (no deployed environment named).
- Existing databases may already hold duplicated batches from past retries: not cleaned up here.

## Open questions and assumptions (each: what, why it matters, default taken)
- "One persisted batch" read as: each batch's rows stored once per import, and the import's
  progress counters agree with the stored rows. ASSUMED; matters because a fix could stop the
  duplicate rows yet leave the counters wrong. Default: both must hold.
- When the transient failure outlasts the retries: the import should fail visibly (non-zero exit,
  status `failed`) without a half-written or doubled batch. Judgement call, not stated by the user.
  Default: covered by a negative QA scenario, not a separate criterion.
- Existing duplicated rows in old databases: out of scope (would need a data fix). Default: listed
  as a follow-up only.

## Authorized actions (commit? push? PR? tracker? deploy? migration? live paid runs and how many?)
- commit: no | push: no | PR: no | tracker: no | deploy: no | migration: no | live runs: 0
