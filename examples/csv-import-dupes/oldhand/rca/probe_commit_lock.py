"""Probe: a REAL lock (no fault hook) makes the batch commit fail, then the retry runs.

A second connection holds a read transaction (SHARED lock) while write_batch commits, so the
commit waits the 0.5 s busy timeout and raises "database is locked". The retry wrapper's log
callback releases the reader before the next attempt. Read-only on the repo; temp DB only.

    cd <repo root> && /usr/bin/python3 .oldhand/csv-import-dupes/rca/probe_commit_lock.py
"""
import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.getcwd())
from importer.batches import write_batch  # noqa: E402
from importer.db import connect, start_import  # noqa: E402
from importer.retry import with_retries  # noqa: E402


def fresh():
    db = os.path.join(tempfile.mkdtemp(prefix="probe-"), "t.db")
    conn = connect(db)
    return db, conn, start_import(conn, "probe.csv")


def counts(db):
    c = sqlite3.connect(db)
    r = (c.execute("SELECT COUNT(*) FROM records").fetchone()[0],
         c.execute("SELECT batches_done, rows_done FROM imports").fetchone())
    c.close()
    return r


# 1. The real write_batch under a real commit-time lock.
db, conn, iid = fresh()
reader = sqlite3.connect(db, isolation_level=None)
reader.execute("BEGIN")
reader.execute("SELECT COUNT(*) FROM records").fetchone()  # holds SHARED until COMMIT/ROLLBACK
log = []


def release(msg):
    log.append(msg)
    if reader.in_transaction:
        reader.execute("ROLLBACK")


with_retries(lambda: write_batch(conn, iid, 1, [("P-1", "a", 1), ("P-2", "b", 2)]), retries=3, delay=0, log=release)
print("probe 1, write_batch under a real reader lock: retries=%r  records, (batches_done, rows_done) = %r"
      % (log, counts(db)))

# 2. Python %s: does `with conn:` roll back when its own COMMIT fails?
db, conn, iid = fresh()
reader = sqlite3.connect(db, isolation_level=None)
reader.execute("BEGIN")
reader.execute("SELECT COUNT(*) FROM records").fetchone()
try:
    with conn:
        conn.execute("INSERT INTO records(import_id, batch_no, sku, name, qty) VALUES (?, 1, 'W-1', 'w', 1)", (iid,))
except sqlite3.OperationalError as e:
    print("probe 2, python %s: `with conn:` commit raised %r; conn.in_transaction after it = %r"
          % (sys.version.split()[0], str(e), conn.in_transaction))
reader.execute("ROLLBACK")
conn.commit()
print("probe 2: rows visible after a later commit on the same connection = %d (1 means the failed batch "
      "was NOT rolled back and a later commit, e.g. finish_import, persists it)" % counts(db)[0])
