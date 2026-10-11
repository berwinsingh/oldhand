# contract lens
Reviewer: lead:opus-5.5 applying the lens in turn (no sub-agent tool) · Read: brief.md criteria, plan.md file table, diff.patch · Ran: nothing
## Findings
None.
## Checked and found fine
- AC1, AC2: delivered by the try/commit/rollback hunk in importer/batches.py; input-independent, so messy CSV/TSV get the same guarantee (replay F3, F4 after the fix).
- R1-R4: importer/cli.py, retry.py and db.py are untouched; the diff cannot change argument parsing (R3), the dry-run branch (R2, returns before connect) or the BadRow path (R4).
- Scope: two files, both in plan.md's table; no refactor, rename or reformat of untouched code.
- Constraints: no schema change, no new flag, no dependency.
- Nothing hard-coded to the sample file or ids.
- Proof: every criterion has a stage that produces its e2e proof (QA); R3 has no check yet, which QA covers.
## Not checked
- AC1's "batch_no counts 2/2/1" is not visible through the CLI (`list` prints totals only) and the fixed QA brief forbids reading the database directly, so QA agents can prove only the totals. The lead's replay harness reads the per-batch counts. Process note, not a code defect.
