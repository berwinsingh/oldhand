"""Hidden acceptance check for js-slug. Usage: check.py <work dir>. Exit 0 when every case passes."""
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


def fresh():
    return os.path.join(tempfile.mkdtemp(), "slugs.json")


def add(store, title):
    p = subprocess.run(["node", "bin/slug.js", "add", title, "--store", store], cwd=work, capture_output=True,
                       text=True, timeout=60)
    return p.stdout.strip() if p.returncode == 0 else "exit %d: %s" % (p.returncode, p.stderr.strip()[-120:])


s = fresh()
case("reported case: Café Menü", add(s, "Café Menü") == "cafe-menu", add(fresh(), "Café Menü"))
case("ñ and capital Å lose their accents", add(fresh(), "Ñandú Árbol Åland") == "nandu-arbol-aland", add(fresh(), "Ñandú Árbol Åland"))
case("symbols collapse to single hyphens", add(fresh(), "--Hello,   World!!--") == "hello-world", add(fresh(), "--Hello,   World!!--"))

s = fresh()
got = [add(s, t) for t in ["Hello World", "Hello World", "Hello World 2", "Hello World"]]
case("unique with a numbered-looking title", got == ["hello-world", "hello-world-2", "hello-world-2-2", "hello-world-3"], str(got))

s = fresh()
got = [add(s, t) for t in ["Hello World Tour", "Hello World"]]
case("a longer slug with the same start does not take the plain one", got == ["hello-world-tour", "hello-world"], str(got))

s = fresh()
got = [add(s, t) for t in ["!!!", "???", "Untitled"]]
case("no letters or digits: untitled, kept unique", got == ["untitled", "untitled-2", "untitled-3"], str(got))

s = fresh()
for t in ["A", "B"]:
    add(s, t)
p = subprocess.run(["node", "bin/slug.js", "list", "--store", s], cwd=work, capture_output=True, text=True, timeout=60)
case("regression: list prints the slugs in order", p.stdout == "a\nb\n", repr(p.stdout))
with open(s) as fh:
    case("regression: the store is a JSON list", json.load(fh) == ["a", "b"])

print("%d failed" % len(fails))
sys.exit(1 if fails else 0)
