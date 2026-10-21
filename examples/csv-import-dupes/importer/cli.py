"""Command line: python -m importer import FILE --retries N"""
import argparse
import sqlite3
import sys

from .batches import BadRow, read_batches, write_batch
from .db import connect, finish_import, list_imports, start_import
from .retry import with_retries


def _log(msg):
    print(msg, file=sys.stderr)


def cmd_import(args):
    if args.dry_run:
        n_rows = n_batches = 0
        try:
            for batch in read_batches(args.file, args.batch_size):
                n_batches += 1
                n_rows += len(batch)
        except BadRow as e:
            _log("error: %s" % e)
            return 2
        print("dry run: %d rows in %d batches, nothing written" % (n_rows, n_batches))
        return 0

    conn = connect(args.db)
    import_id = start_import(conn, args.file)
    n_rows = n_batches = 0
    try:
        for batch_no, batch in enumerate(read_batches(args.file, args.batch_size), start=1):
            with_retries(lambda: write_batch(conn, import_id, batch_no, batch), retries=args.retries, log=_log)
            n_batches += 1
            n_rows += len(batch)
    except BadRow as e:
        finish_import(conn, import_id, "failed")
        _log("error: %s" % e)
        return 2
    except sqlite3.Error as e:
        finish_import(conn, import_id, "failed")
        _log("error: storage failed after retries: %s" % e)
        return 1
    finish_import(conn, import_id, "done")
    print("import %d: %d rows in %d batches" % (import_id, n_rows, n_batches))
    return 0


def cmd_list(args):
    conn = connect(args.db)
    for row in list_imports(conn):
        print("%d\t%s\t%s\tbatches=%d\trows=%d\tstored=%d" % row)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="importer")
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("import", help="import a .csv or .tsv file")
    p.add_argument("file")
    p.add_argument("--db", default="importer.db")
    p.add_argument("--retries", type=int, default=3)
    p.add_argument("--batch-size", type=int, default=100)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_import)
    p = sub.add_parser("list", help="list imports and their stored row counts")
    p.add_argument("--db", default="importer.db")
    p.set_defaults(func=cmd_list)
    args = ap.parse_args(argv)
    return args.func(args)
