"""Replay harness for csv-import-dupes. Runs the real CLI (python -m importer) in a subprocess
against a fresh SQLite file per case, then reads the database back. Read-only on the repo.

    cd <repo root> && /usr/bin/python3 .oldhand/csv-import-dupes/rca/replay.py [--only F1,G2]

Prints one line per case and a summary: failed set a/b pass, regression set c/d pass.
Exit 0 when every case passes.
"""
import os
import sqlite3
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DATA = os.path.join(HERE, "data")
PY = sys.executable


def run_cli(args, faults="", db=None):
    env = dict(os.environ)
    env.pop("IMPORTER_FAULTS", None)
    if faults:
        env["IMPORTER_FAULTS"] = faults
    cmd = [PY, "-m", "importer"] + args + (["--db", db] if db else [])
    p = subprocess.run(cmd, cwd=REPO, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.returncode, p.stdout, p.stderr


def db_state(db):
    if not os.path.exists(db):
        return None
    c = sqlite3.connect(db)
    per_batch = [n for _, n in c.execute("SELECT batch_no, COUNT(*) FROM records GROUP BY batch_no ORDER BY batch_no")]
    total = c.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    dup_skus = c.execute("SELECT COUNT(*) FROM (SELECT sku FROM records GROUP BY import_id, sku HAVING COUNT(*) > 1)").fetchone()[0]
    imp = c.execute("SELECT status, batches_done, rows_done FROM imports ORDER BY id DESC LIMIT 1").fetchone()
    c.close()
    return {"per_batch": per_batch, "total": total, "dup_skus": dup_skus, "import": imp}


def case(cid, args, faults, expect_code, expect):
    tmp = tempfile.mkdtemp(prefix="replay-%s-" % cid)
    db = os.path.join(tmp, "t.db")
    code, out, err = run_cli(args, faults, None if "--dry-run" in args else db)
    if "--dry-run" in args:
        code, out, err = run_cli(args + ["--db", db], faults)
    st = db_state(db)
    problems = []
    if code != expect_code:
        problems.append("exit %d, expected %d" % (code, expect_code))
    for key, want in expect.items():
        if key == "stdout":
            if want not in out:
                problems.append("stdout %r lacks %r" % (out.strip(), want))
        elif key == "stderr":
            if want not in err:
                problems.append("stderr %r lacks %r" % (err.strip()[-200:], want))
        elif key == "no_db":
            if st is not None:
                problems.append("a database file was created")
        else:
            got = None if st is None else st[key]
            if got != want:
                problems.append("%s=%r, expected %r" % (key, got, want))
    return problems, code, out.strip(), err.strip().splitlines()[-1:] if err.strip() else [], st


CSV = os.path.join(REPO, "samples", "products.csv")
TSV = os.path.join(REPO, "samples", "products.tsv")

FAILED = [
    ("F1", "csv, transient fault after the rows are written, retried",
     ["import", CSV, "--batch-size", "2", "--retries", "3"], "progress:1", 0,
     {"total": 5, "per_batch": [2, 2, 1], "dup_skus": 0, "import": ("done", 3, 5)}),
    ("F2", "tsv, same fault",
     ["import", TSV, "--batch-size", "2", "--retries", "3"], "progress:1", 0,
     {"total": 3, "per_batch": [2, 1], "dup_skus": 0, "import": ("done", 2, 3)}),
    ("F3", "messy csv (BOM, CRLF, padding, quoted comma, unicode), two faults",
     ["import", os.path.join(DATA, "messy.csv"), "--batch-size", "2", "--retries", "3"], "progress:2", 0,
     {"total": 5, "per_batch": [2, 2, 1], "dup_skus": 0, "import": ("done", 3, 5)}),
    ("F4", "messy tsv, one fault",
     ["import", os.path.join(DATA, "messy.tsv"), "--batch-size", "2", "--retries", "3"], "progress:1", 0,
     {"total": 3, "per_batch": [2, 1], "dup_skus": 0, "import": ("done", 2, 3)}),
    ("F5", "fault outlasts the retries: visible failure, no doubled or half batch (judgement)",
     ["import", CSV, "--batch-size", "2", "--retries", "1"], "progress:5", 1,
     {"total": 0, "dup_skus": 0, "stderr": "storage failed after retries"}),
]
REGRESSION = [
    ("G1", "csv, no fault", ["import", CSV, "--batch-size", "2"], "", 0,
     {"stdout": "5 rows in 3 batches", "total": 5, "per_batch": [2, 2, 1], "import": ("done", 3, 5)}),
    ("G2", "tsv, no fault, default batch size", ["import", TSV], "", 0,
     {"stdout": "3 rows in 1 batches", "total": 3, "per_batch": [3], "import": ("done", 1, 3)}),
    ("G3", "fault before the insert, retried", ["import", CSV, "--batch-size", "2"], "insert:1", 0,
     {"total": 5, "per_batch": [2, 2, 1], "dup_skus": 0, "import": ("done", 3, 5)}),
    ("G4", "dry run writes nothing", ["import", TSV, "--dry-run"], "", 0,
     {"stdout": "dry run: 3 rows in 1 batches, nothing written", "no_db": True}),
    ("G5", "bad row on line 4 stops the import", ["import", os.path.join(DATA, "badrow.csv"), "--batch-size", "2"], "", 2,
     {"stderr": "line 4: bad row", "total": 2, "per_batch": [2], "import": ("failed", 1, 2)}),
]


def main():
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    tally = {}
    for name, cases in (("failed set", FAILED), ("regression set", REGRESSION)):
        ok = n = 0
        for cid, title, args, faults, code, expect in cases:
            if only and cid not in only:
                continue
            n += 1
            problems, got_code, out, err, st = case(cid, args, faults, code, expect)
            ok += not problems
            print("%s %-4s %s | faults=%r exit=%d db=%s | %s" % (
                "PASS" if not problems else "FAIL", cid, title, faults, got_code, st,
                "; ".join(problems) if problems else (out or (err[0] if err else ""))))
        tally[name] = (ok, n)
    print("SUMMARY: failed set %d/%d pass, regression set %d/%d pass" % (tally["failed set"] + tally["regression set"]))
    return 0 if all(a == b for a, b in tally.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
