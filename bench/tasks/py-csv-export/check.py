"""Hidden acceptance check for py-csv-export. Usage: check.py <work dir>. Exit 0 when every case passes."""
import csv
import io
import json
import os
import subprocess
import sys
import tempfile

work = os.path.abspath(sys.argv[1])
fails = []
ROWS = [
    {"name": "Wile E. Coyote", "email": "wile@acme.test", "company": "Acme, Inc.", "notes": "orders often"},
    {"name": "Dwayne \"The Rock\" Johnson", "email": "rock@example.test", "company": "Seven Bucks", "notes": "said \"hi\""},
    {"name": "Multi Line", "email": "ml@example.test", "company": "Lines Ltd", "notes": "first line\nsecond line"},
    {"name": "=HYPERLINK(\"http://evil\")", "email": "x@example.test", "company": "+1 Corp", "notes": "-5 discount"},
    {"name": "@handle", "email": "h@example.test", "company": "Plain", "notes": "ok"},
    {"name": "Zoë Ångström", "email": "zoe@example.test", "company": "Müller & Söhne", "notes": "naïve café"},
]
FIELDS = ["name", "email", "company", "notes"]


def expect(value):
    return "'" + value if value[:1] in ("=", "+", "-", "@") else value


def case(label, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else "  " + detail))
    if not ok:
        fails.append(label)


tmp = tempfile.mkdtemp()
data = os.path.join(tmp, "contacts.json")
with open(data, "w", encoding="utf-8") as fh:
    json.dump(ROWS, fh, ensure_ascii=False)
p = subprocess.run([sys.executable, "-m", "contacts", "--data", data, "export", "--format", "csv"], cwd=work,
                   capture_output=True, timeout=60)
case("export exits 0", p.returncode == 0, p.stderr.decode("utf-8", "replace")[-300:])
text = p.stdout.decode("utf-8", "replace")
try:
    table = list(csv.reader(io.StringIO(text)))
except csv.Error as e:
    table = []
    case("csv module can parse the export", False, str(e))
case("header row unchanged", bool(table) and table[0] == FIELDS, str(table[:1]))
body = table[1:]
case("one row per contact", len(body) == len(ROWS), "got %d rows" % len(body))
if len(body) == len(ROWS):
    for i, row in enumerate(ROWS):
        want = [expect(row[f]) for f in FIELDS]
        case("row %d round-trips (%s)" % (i + 1, row["name"][:20]), body[i] == want, "got %r want %r" % (body[i], want))

p = subprocess.run([sys.executable, "-m", "contacts", "--data", data, "export", "--format", "csv", "--out",
                    os.path.join(tmp, "out.csv")], cwd=work, capture_output=True, timeout=60)
with open(os.path.join(tmp, "out.csv"), encoding="utf-8", newline="") as fh:
    case("--out writes the same table", list(csv.reader(fh)) == table, "")

plain = os.path.join(tmp, "plain.json")
with open(plain, "w", encoding="utf-8") as fh:
    json.dump([{"name": "Ada", "email": "ada@example.com", "company": "Engines", "notes": "first"}], fh)
p = subprocess.run([sys.executable, "-m", "contacts", "--data", plain, "export", "--format", "tsv"], cwd=work,
                   capture_output=True, text=True, timeout=60)
case("regression: TSV for ordinary values unchanged",
     p.stdout == "name\temail\tcompany\tnotes\nAda\tada@example.com\tEngines\tfirst\n", repr(p.stdout))

print("%d failed" % len(fails))
sys.exit(1 if fails else 0)
