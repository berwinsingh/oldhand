# Examples

Real runs of the Oldhand pack, kept as they were produced. Nothing in here is
written by hand after the fact; the `oldhand/` folder in each example is the
task folder the pack wrote (normally `.oldhand/<task>/`, renamed so git keeps it).

## csv-import-dupes

A small stdlib Python project (`importer/`) with a seeded bug: a transient
write failure plus a retry stored a CSV batch twice. The request was a plain
prompt with no ticket:

> No ticket. Fix intermittent duplicate batches on CSV import. Current: a
> transient write failure plus retry inserts the batch twice. Constraints: no
> schema migration; keep the CLI flags. Acceptance: one import produces one
> persisted batch even after a retry. Prove it end to end.

What to read, in order:

- `oldhand/contract.md`: the criteria the run was held to (AC1, AC2, R1 to R4).
- `oldhand/rca.md`: two root causes, not the "missing idempotency key" the
  request assumed; the second (a failed COMMIT leaves the transaction open)
  was found by a probe, and the obvious fix passes the obvious test but still
  doubles rows under a real lock.
- `oldhand/review.md`: the correctness lens found the regression test did not
  guard the second cause; the fix added a second test, killed by mutation.
- `oldhand/qa/results.md`: nine scenarios through the real CLI, with a
  transcript per scenario under `qa/evidence/`.
- `oldhand/report.md`: the verdict computed by `ledger.py`, with its "Not
  verified" section.

Honest limits, from the report itself: the run happened inside a host with no
sub-agent tool, so every reviewer, refuter and QA scenario was run by the lead
in turn. The ledger labels (`qa:worker`, `qa:scout`) are the planned tiers, not
who ran them. The binary SQLite evidence files were left out of the repo.

## site-rebuild

The task folder of the run that rebuilt the project website with the pack
itself: the contract (`oldhand/contract.md`), trace and plan, the four review
memos and the chair's `review.md`, eleven QA scenarios with their briefs,
results and text evidence (`oldhand/qa/`), the ledger, and the computed
verdict in `oldhand/report.md`. Read `oldhand/qa/results.md` for what each
scenario observed, and `oldhand/learned.md` for what the run taught.

The QA screenshots (109 files, about 20 MB) are left out to keep the
repository small; the evidence paths in the results still name them. The text
evidence, the per-scenario transcripts and the ledger are complete.

Pack version at the time: 2.0.0, before the review fixes of 2026-10-11.
