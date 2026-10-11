# Learned: csv-import-dupes

Target: none written. The project has no AGENTS.md/CLAUDE.md, and this session's memory directory belongs to another
project; the skill forbids creating a new instruction file without asking. Proposed notes, to apply on the user's OK
(target: a new CLAUDE.md or the README's "Chaos testing" section):

- 2026-10-11: On Python 3.9 `with conn:` does not roll back when its own COMMIT fails ("database is locked"); the
  transaction stays open and the next commit on that connection persists it. Why: write_batch is retried as a unit.
  How to apply: any retried multi-statement write rolls back explicitly in an except before re-raising
  (rca/probe_commit_lock.txt, probe 2).
- 2026-10-11: To tell retry duplicates from re-imports in a user's database: duplicates within one import_id come from
  a retried batch; across import_ids, from importing the same file twice (by design). Query in rca/probe_alternative.txt.

Durable work in a temp folder (will be wiped): rca/replay.py, rca/probe_commit_lock.py, rca/data/*. Proposed home:
tests/ (replay as an integration test) or scripts/. Not moved: needs the user's OK.

Dropped: the fix itself and file locations (in the diff); the fault hook's syntax (in importer/faults.py docstring).
