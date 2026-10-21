"""SQLite storage for imports.

Schema v1. Changing it needs a migration (see README).
"""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    status TEXT NOT NULL DEFAULT 'running',
    batches_done INTEGER NOT NULL DEFAULT 0,
    rows_done INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_id INTEGER NOT NULL REFERENCES imports(id),
    batch_no INTEGER NOT NULL,
    sku TEXT NOT NULL,
    name TEXT NOT NULL,
    qty INTEGER NOT NULL
);
"""


def connect(path):
    conn = sqlite3.connect(path, timeout=0.5)
    conn.executescript(SCHEMA)
    return conn


def start_import(conn, source):
    cur = conn.execute("INSERT INTO imports(source) VALUES (?)", (source,))
    conn.commit()
    return cur.lastrowid


def finish_import(conn, import_id, status):
    conn.execute("UPDATE imports SET status = ? WHERE id = ?", (status, import_id))
    conn.commit()


def list_imports(conn):
    return conn.execute(
        "SELECT i.id, i.source, i.status, i.batches_done, i.rows_done, COUNT(r.id) "
        "FROM imports i LEFT JOIN records r ON r.import_id = i.id "
        "GROUP BY i.id ORDER BY i.id"
    ).fetchall()
