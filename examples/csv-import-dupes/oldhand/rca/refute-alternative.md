# Refute: alternative (run by the lead in turn; no sub-agent tool on this host, independence reduced)
Verdict: stands, with one alternative the user must rule out on their real data. Confidence: high for the mechanism, medium that it explains every duplicate the user saw.
- Hook artefact? No: probe 1 (rca/probe_commit_lock.txt) duplicates a batch with a real reader lock and no IMPORTER_FAULTS.
- Retry wrapper or reader generator duplicating on their own? No: G1, G2 (no fault) and G3 (fault before the insert) store exact counts (rca/baseline-replay.txt).
- Re-running the same file: ALSO produces "duplicates", but across import_ids, by design (rca/probe_alternative.txt: rerun.db within 0 / across 5; retry.db within 2 / across 0). This change cannot and should not touch that (it needs a key and a schema change). The query in probe_alternative.txt tells the two apart on the user's database.
- A second writer process: would cause "database is locked" (the trigger), not the doubling itself; the doubling needs the retry of a non-atomic write. Consistent with the claimed cause.
