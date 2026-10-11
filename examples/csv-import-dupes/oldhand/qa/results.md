# QA results: Fix duplicate batches on CSV import retry

**9 pass, 0 fail, 0 blocked, 0 missing, 0 invalid** out of 9 scenarios.

| id | criterion | kind | surface | env | status | observed | evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S1 | AC1 | acceptance | cli | local | pass | Import printed 'import 1: 5 rows in 3 batches', exit=0, stderr had retry 1/3 and retry 2/3. list: '1 samples/products.cs... | [run.txt](evidence/S1/run.txt) |
| S2 | AC1 | failing-case | cli | local | pass | Import printed 'import 1: 5 rows in 3 batches', exit=0, one 'retry 1/3' line. list: done batches=3 rows=5 stored=5 (the ... | [run.txt](evidence/S2/run.txt) |
| S3 | AC1 | negative | cli | local | pass | exit=1; stderr 'retry 1/1' then 'error: storage failed after retries: database is locked'. list: '1 samples/products.csv... | [run.txt](evidence/S3/run.txt) |
| S4 | AC2 | acceptance | cli | local | pass | Import printed 'import 1: 5 rows in 3 batches', exit=0, retry 1/3 and 2/3. list: done batches=3 rows=5 stored=5. | [run.txt](evidence/S4/run.txt) |
| S5 | AC2 | messy | cli | local | pass | Import printed 'import 1: 3 rows in 3 batches', exit=0, retries 1/3, 2/3, 3/3. list: done batches=3 rows=3 stored=3. | [run.txt](evidence/S5/run.txt) |
| S6 | R1 | regression | cli | local | pass | Import printed exactly 'import 1: 5 rows in 3 batches', exit=0, no stderr. list: done batches=3 rows=5 stored=5. | [run.txt](evidence/S6/run.txt) |
| S7 | R2 | regression | cli | local | pass | Printed 'dry run: 3 rows in 1 batches, nothing written', exit=0. ls of the evidence folder showed it empty: no s7.db. | [run.txt](evidence/S7/run.txt) |
| S8 | R3 | regression | cli | local | pass | import --help lists file, --db DB, --retries RETRIES, --batch-size BATCH_SIZE, --dry-run; list --help lists --db DB. imp... | [run.txt](evidence/S8/run.txt) |
| S9 | R4 | regression | cli | local | pass | exit=2; stderr "error: line 4: bad row {'sku': 'E-502', 'name': 'Broken', 'qty': 'lots'}". list: '1 ... failed batches=1... | [run.txt](evidence/S9/run.txt) |

Recorded in the ledger: S1 as C19, S2 as C20, S3 as C21, S4 as C22, S5 as C23, S6 as C24, S7 as C25, S8 as C26, S9 as C27.

Counted by qa.py from the result files the QA agents wrote. The lead still opens the evidence, re-runs every fail and every surprising pass, and re-runs the most important acceptance scenario itself (recorded with ledger.py record --lead).
