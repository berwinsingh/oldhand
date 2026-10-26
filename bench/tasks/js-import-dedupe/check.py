"""Hidden acceptance check for js-import-dedupe. Usage: check.py <work dir>. Exit 0 when every case passes."""
import json
import os
import subprocess
import sys
import tempfile

work = os.path.abspath(sys.argv[1])
fails = []


def case(label, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else "  " + detail))
    if not ok:
        fails.append(label)


tmp = tempfile.mkdtemp()
db = os.path.join(tmp, "crm.json")
csv1 = os.path.join(tmp, "a.csv")


def imp(path):
    p = subprocess.run(["node", "bin/import.js", path, "--db", db], cwd=work, capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout.strip().splitlines(), p.stderr


def stored():
    try:
        with open(db) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


with open(csv1, "w") as fh:
    fh.write('name,email,company\n'
             '"Bob, Jr.",  Bob@Example.com ,"Acme, Inc."\n'
             'Ana,ana@example.com,Engines\n'
             'Robert,bob@example.com,Acme\n'
             'Nobody,not-an-email,Void\n'
             '"Cat ""C"" Lee",Cat@Example.COM,"Lee & Co"\n')

code, out, err = imp(csv1)
case("first import: summary line", code == 0 and out[-1:] == ["added 3, skipped 1, invalid 1"], "%s %s" % (out, err[-200:]))
case("invalid row reported on stderr with its data-row number", "row 4: invalid email" in err, repr(err[-200:]))
s = stored() or []
case("stored emails keep first-seen spelling, trimmed", [c.get("email") for c in s] == ["Bob@Example.com", "ana@example.com", "Cat@Example.COM"],
     str([c.get("email") for c in s]))
case("regression: quoted fields keep working", [c.get("name") for c in s] == ["Bob, Jr.", "Ana", 'Cat "C" Lee']
     and s and s[0].get("company") == "Acme, Inc.", str([(c.get("name"), c.get("company")) for c in s]))
before = json.dumps(stored())
code, out, err = imp(csv1)
case("reported case: importing the same file again adds nothing", code == 0 and out[-1:] == ["added 0, skipped 4, invalid 1"]
     and json.dumps(stored()) == before, "%s" % out)
csv2 = os.path.join(tmp, "b.csv")
with open(csv2, "w") as fh:
    fh.write('name,email,company\nAna Again, ANA@example.com ,X\nDee,dee@example.com,Y\n')
code, out, err = imp(csv2)
case("a later file: case and spaces still match the store", code == 0 and out[-1:] == ["added 1, skipped 1, invalid 0"]
     and [c.get("email") for c in stored()][-1] == "dee@example.com", "%s" % out)

print("%d failed" % len(fails))
sys.exit(1 if fails else 0)
