# Refute: evidence (run by the lead in turn; no sub-agent tool on this host, independence reduced)
Verdict: stands. Confidence: high.
- batches.py:42 `conn.commit()` precedes :43 `faults.maybe_fail("progress")` and the UPDATE at :44: re-read (rca/probe_alternative.txt tail). Holds.
- F1 per_batch [4, 2, 1], total 7, imports row ("done", 3, 5): rca/baseline-replay.txt line 1, from a fresh DB per case. Holds; the counters are right and the rows are not, so the import reports success.
- Commit-time failure leaves the transaction open on Python 3.9.6: rca/probe_commit_lock.txt probe 2, `in_transaction = True`, and a later commit persisted the row. Observed on this runtime only; newer CPython may roll back in `__exit__` (assumed, not checked here), so the fix must not rely on `with conn:` alone.
- Objection considered: probe 1 releases the reader from the retry log callback, which is test scaffolding. Answer: it only times the release; the lock, the busy timeout and the failure are real SQLite behaviour.
