"""Read delimited files in batches and write each batch to SQLite."""
import csv

from . import faults

COLUMNS = ("sku", "name", "qty")


class BadRow(ValueError):
    pass


def read_batches(path, batch_size=100):
    """Yield lists of (sku, name, qty) tuples. .tsv files are tab separated."""
    delimiter = "\t" if path.endswith(".tsv") else ","
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter=delimiter)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise BadRow("missing column(s): %s" % ", ".join(missing))
        batch = []
        for line_no, row in enumerate(reader, start=2):
            try:
                item = (row["sku"].strip(), row["name"].strip(), int(row["qty"]))
            except (TypeError, ValueError, AttributeError):
                raise BadRow("line %d: bad row %r" % (line_no, row))
            batch.append(item)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch


def write_batch(conn, import_id, batch_no, rows):
    """Insert one batch and bump the import's progress counters, all or nothing.

    with_retries re-runs this whole function, so a failure must leave nothing behind. Roll back
    explicitly: on Python 3.9 `with conn:` keeps the transaction open when its COMMIT fails.
    """
    try:
        faults.maybe_fail("insert")
        conn.executemany(
            "INSERT INTO records(import_id, batch_no, sku, name, qty) VALUES (?, ?, ?, ?, ?)",
            [(import_id, batch_no) + r for r in rows],
        )
        faults.maybe_fail("progress")
        conn.execute(
            "UPDATE imports SET batches_done = batches_done + 1, rows_done = rows_done + ? WHERE id = ?",
            (len(rows), import_id),
        )
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
