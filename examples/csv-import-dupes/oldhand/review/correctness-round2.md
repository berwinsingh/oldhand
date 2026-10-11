# correctness lens, round 2
Reviewer: lead:opus-5.5 in turn (no sub-agent tool) · Read: review/diff-round2.patch, importer/db.py:27-30 · Ran: the new test 1x in the tree (0.58 s), the 'with conn:' variant in a temp copy (fails 4 != 2), mutate.py on conn.rollback() (KILLED, C10)
## Findings
None.
## Checked and found fine
- Deterministic: the reader holds SHARED until the retry callback releases it; COMMIT waits the 0.5 s busy timeout from connect() (db.py:28) and fails; no timing race.
- Not vacuous: asserts exactly one retry happened, so a change in locking (WAL, timeout) fails the test instead of passing it silently.
- Asserts both the stored rows (2) and the counters (1, 2), matching the contract's reading of "one persisted batch".
- Temp directory without cleanup: same idiom as CliTest.setUp (tests/test_importer.py, mkdtemp); not a defect.
## Not checked
- Behaviour under CPython 3.12+ (not installed here).
