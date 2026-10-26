"""Hidden acceptance check for py-report-tz. Usage: check.py <work dir>. Exit 0 when every case passes."""
import json
import os
import subprocess
import sys
import tempfile

work = os.path.abspath(sys.argv[1])
tmp = tempfile.mkdtemp()
db = os.path.join(tmp, "events.jsonl")
cfg = os.path.join(tmp, "config.json")
fails = []


def cli(*args):
    p = subprocess.run([sys.executable, "-m", "events", "--db", db, "--config", cfg] + list(args),
                       cwd=work, capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout, p.stderr


def names(out):
    rows = [l for l in out.strip().splitlines() if l and not l.startswith("total:")]
    return sorted(l.split(" ", 1)[1] for l in rows)


def case(label, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else "  " + detail))
    if not ok:
        fails.append(label)


def set_tz(tz):
    with open(cfg, "w") as fh:
        json.dump({"tz": tz}, fh)


set_tz("America/New_York")
for at, name in [("2026-03-10T15:00:00Z", "a-afternoon"), ("2026-03-11T03:30:00Z", "b-late-evening"),
                 ("2026-03-10T03:00:00Z", "c-prev-evening"), ("2026-03-12T12:00:00Z", "d-later")]:
    code, out, err = cli("add", "--at", at, "--name", name)
    case("add %s" % name, code == 0, err)

for label, a, b, want in [
    ("reported case: --to day is included (New York)", "2026-03-01", "2026-03-10", ["a-afternoon", "b-late-evening", "c-prev-evening"]),
    ("single local day Mar 10 (New York)", "2026-03-10", "2026-03-10", ["a-afternoon", "b-late-evening"]),
    ("23:30 local stays on Mar 10, not Mar 11", "2026-03-11", "2026-03-11", []),
    ("23:00 local on Mar 9 counts on Mar 9", "2026-03-09", "2026-03-09", ["c-prev-evening"]),
    ("whole month", "2026-03-01", "2026-03-31", ["a-afternoon", "b-late-evening", "c-prev-evening", "d-later"]),
]:
    code, out, err = cli("report", "--from", a, "--to", b)
    got = names(out)
    case(label, code == 0 and got == sorted(want) and ("total: %d" % len(want)) in out, "got %s exit %s %s" % (got, code, err.strip()[-200:]))

set_tz("UTC")
for label, a, b, want in [
    ("UTC config: Mar 10", "2026-03-10", "2026-03-10", ["a-afternoon", "c-prev-evening"]),
    ("UTC config: Mar 11", "2026-03-11", "2026-03-11", ["b-late-evening"]),
]:
    code, out, err = cli("report", "--from", a, "--to", b)
    got = names(out)
    case(label, code == 0 and got == sorted(want), "got %s exit %s" % (got, code))

code, out, err = cli("add", "--at", "2026-03-09T12:00:00", "--name", "x")
case("regression: a time without an offset is still rejected with exit 2", code == 2, "exit %s" % code)

print("%d failed" % len(fails))
sys.exit(1 if fails else 0)
