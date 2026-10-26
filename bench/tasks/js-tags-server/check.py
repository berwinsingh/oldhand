"""Hidden acceptance check for js-tags-server: starts the real server and calls it over HTTP.
Usage: check.py <work dir>. Exit 0 when every case passes."""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

work = os.path.abspath(sys.argv[1])
fails = []


def case(label, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else "  " + detail))
    if not ok:
        fails.append(label)


proc = subprocess.Popen(["node", "server.js", "--port", "0"], cwd=work, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        text=True)
port = None
deadline = time.time() + 20
while time.time() < deadline and port is None:
    line = proc.stdout.readline()
    if not line:
        break
    if "listening on" in line:
        port = int(line.rsplit(" ", 1)[1])
if port is None:
    case("server starts and prints its port", False, proc.stderr.read()[-300:] if proc.poll() is not None else "")
    proc.kill()
    print("1 failed")
    sys.exit(1)


def get(path):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, path), timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


try:
    for label, path, want in [
        ("reported case: red AND large", "/items?tag=red&tag=large", [2, 4]),
        ("case-insensitive single tag", "/items?tag=red", [1, 2, 4, 6]),
        ("query tag in capitals", "/items?tag=SMALL", [1, 6]),
        ("three tags", "/items?tag=red&tag=small&tag=wool", [6]),
        ("unknown tag is an empty list", "/items?tag=purple", []),
        ("known tags with no common item", "/items?tag=green&tag=large", []),
        ("regression: no tag lists everything", "/items", [1, 2, 3, 4, 5, 6]),
    ]:
        status, body = get(path)
        ids = [i["id"] for i in body] if isinstance(body, list) else body
        case(label, status == 200 and ids == want, "status %s got %s want %s" % (status, ids, want))
    status, body = get("/items/3")
    case("regression: /items/3", status == 200 and body.get("name") == "Tee, blue, L", "%s %s" % (status, body))
    status, body = get("/items/99")
    case("regression: missing id is 404", status == 404, str(status))
finally:
    proc.kill()

print("%d failed" % len(fails))
sys.exit(1 if fails else 0)
