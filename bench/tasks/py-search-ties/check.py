"""Hidden acceptance check for py-search-ties. Usage: check.py <work dir>. Exit 0 when every case passes.
Each page is a separate process, so hash randomisation shows any order that depends on set iteration."""
import json
import os
import re
import subprocess
import sys
import tempfile

work = os.path.abspath(sys.argv[1])
fails = []
WORD = re.compile(r"[a-z0-9]+")


def case(label, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else "  " + detail))
    if not ok:
        fails.append(label)


arts = []
for i in range(1, 31):
    title = "Garden notes %d" % i if i % 4 == 0 else "Article %d" % i
    body = "garden " * (1 + (i % 3 == 0)) + "tips and tricks"
    arts.append({"id": "doc-%d" % i, "title": title, "body": body})
arts.append({"id": "doc-99", "title": "Lawn", "body": "no match here"})
data = os.path.join(tempfile.mkdtemp(), "articles.json")
with open(data, "w") as fh:
    json.dump(arts, fh)


def expected(query):
    terms = WORD.findall(query.lower())
    out = []
    for a in arts:
        t, b = WORD.findall(a["title"].lower()), WORD.findall(a["body"].lower())
        if any(x in t or x in b for x in terms):
            out.append((a["id"], sum(2 * t.count(x) + b.count(x) for x in terms)))
    out.sort(key=lambda p: (-p[1], int(p[0].split("-")[1])))
    return out


def run(*args, seed="0"):
    env = dict(os.environ, PYTHONHASHSEED=seed)
    p = subprocess.run([sys.executable, "-m", "search", "--data", data] + list(args), cwd=work, env=env,
                       capture_output=True, text=True, timeout=60)
    lines = p.stdout.strip().splitlines()
    rows = [(l.split("  ")[0], int(l.split("  ")[1])) for l in lines[1:]] if p.returncode == 0 else []
    return p.returncode, lines[:1], rows


want = expected("garden")
code, head, rows = run("garden", "--all")
case("--all: score order, ties by natural id order", code == 0 and rows == want, "got %s" % rows[:12])
case("header counts each article once", head == ["%d results" % len(want)], str(head))
for per in (3, 4, 7):
    pages, n = [], 1
    while True:
        code, _, rows = run("garden", "--page", str(n), "--per-page", str(per), seed=str(n * 7919 + per))
        if not rows or n > 20:
            break
        pages.extend(rows)
        n += 1
    case("reported case: --per-page %d pages, each a separate run, cover every result exactly once in order" % per,
         pages == want, "got %d rows, %d distinct" % (len(pages), len({p[0] for p in pages})))
code, _, a = run("garden", "--page", "2", "--per-page", "5", seed="1")
code, _, b = run("garden", "--page", "2", "--per-page", "5", seed="2")
case("the same query gives the same page every time", a == b and a == want[5:10], "%s vs %s" % (a, b))
code, head, rows = run("garden tips", "--all")
case("two-word query keeps scoring and order", rows == expected("garden tips"), str(rows[:6]))
code, head, rows = run("nothingmatches", "--all")
case("regression: no match prints 0 results", code == 0 and head == ["0 results"] and rows == [], str(head))

print("%d failed" % len(fails))
sys.exit(1 if fails else 0)
