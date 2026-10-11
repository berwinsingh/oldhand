# importer

Imports product rows from CSV or TSV files into SQLite, in batches.

    python -m importer import samples/products.csv --db importer.db --retries 3 --batch-size 2
    python -m importer import samples/products.tsv --dry-run
    python -m importer list --db importer.db

Tests: `python3 -m unittest discover -s tests -v`

Chaos testing: `IMPORTER_FAULTS="progress:1"` makes the progress update fail
once with "database is locked" (see importer/faults.py).

The schema lives in importer/db.py. Changing it needs a migration; we have no
migration tooling yet, so schema changes are out of bounds without sign-off.
