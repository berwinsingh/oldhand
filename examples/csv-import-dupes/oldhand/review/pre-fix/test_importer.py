import io
import os
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest import mock

from importer import faults
from importer.batches import BadRow, read_batches, write_batch
from importer.cli import main
from importer.db import connect, start_import
from importer.retry import with_retries

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(os.path.dirname(HERE), "samples")


class ReadBatchesTest(unittest.TestCase):
    def test_csv_batches(self):
        batches = list(read_batches(os.path.join(SAMPLES, "products.csv"), batch_size=2))
        self.assertEqual([len(b) for b in batches], [2, 2, 1])
        self.assertEqual(batches[0][0], ("A-100", "Widget", 4))

    def test_tsv_batches(self):
        batches = list(read_batches(os.path.join(SAMPLES, "products.tsv"), batch_size=10))
        self.assertEqual(batches, [[("B-200", "Bolt", 50), ("B-201", "Nut", 75), ("B-202", "Washer", 20)]])

    def test_bad_qty(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
            fh.write("sku,name,qty\nX,Thing,lots\n")
        self.addCleanup(os.remove, fh.name)
        with self.assertRaises(BadRow):
            list(read_batches(fh.name))


class RetryTest(unittest.TestCase):
    def test_retries_transient_then_succeeds(self):
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise sqlite3.OperationalError("database is locked")
            return "ok"

        self.assertEqual(with_retries(flaky, retries=3, delay=0), "ok")
        self.assertEqual(len(calls), 3)

    def test_gives_up(self):
        def always():
            raise sqlite3.OperationalError("database is locked")

        with self.assertRaises(sqlite3.OperationalError):
            with_retries(always, retries=2, delay=0)

    def test_does_not_retry_other_errors(self):
        calls = []

        def broken():
            calls.append(1)
            raise sqlite3.OperationalError("no such table: records")

        with self.assertRaises(sqlite3.OperationalError):
            with_retries(broken, retries=3, delay=0)
        self.assertEqual(len(calls), 1)


class WriteBatchTest(unittest.TestCase):
    def setUp(self):
        faults.reset()
        self.conn = connect(":memory:")
        self.import_id = start_import(self.conn, "t.csv")

    def test_writes_rows_and_progress(self):
        write_batch(self.conn, self.import_id, 1, [("A", "a", 1), ("B", "b", 2)])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM records").fetchone()[0], 2)
        self.assertEqual(self.conn.execute("SELECT batches_done, rows_done FROM imports").fetchone(), (1, 2))

    def test_retry_after_failure_before_insert(self):
        with mock.patch.dict(os.environ, {"IMPORTER_FAULTS": "insert:1"}):
            with_retries(lambda: write_batch(self.conn, self.import_id, 1, [("A", "a", 1)]), delay=0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM records").fetchone()[0], 1)

    def test_retry_after_failure_after_insert_stores_batch_once(self):
        with mock.patch.dict(os.environ, {"IMPORTER_FAULTS": "progress:1"}):
            with_retries(lambda: write_batch(self.conn, self.import_id, 1, [("A", "a", 1), ("B", "b", 2)]), delay=0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM records").fetchone()[0], 2)
        self.assertEqual(self.conn.execute("SELECT batches_done, rows_done FROM imports").fetchone(), (1, 2))


class CliTest(unittest.TestCase):
    def setUp(self):
        faults.reset()
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "t.db")

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_import_csv(self):
        code, out, _ = self.run_cli("import", os.path.join(SAMPLES, "products.csv"), "--db", self.db, "--batch-size", "2")
        self.assertEqual(code, 0)
        self.assertIn("5 rows in 3 batches", out)

    def test_dry_run_writes_nothing(self):
        code, out, _ = self.run_cli("import", os.path.join(SAMPLES, "products.tsv"), "--db", self.db, "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("dry run: 3 rows in 1 batches", out)
        self.assertFalse(os.path.exists(self.db))


if __name__ == "__main__":
    unittest.main()
