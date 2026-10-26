"""Hidden acceptance check for js-remember-me: starts the real server and drives it over HTTP.
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
HOUR, DAYS30 = 3600 * 1000, 30 * 24 * 3600 * 1000


def case(label, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else "  " + detail))
    if not ok:
        fails.append(label)


proc = subprocess.Popen(["node", "server.js", "--port", "0"], cwd=work, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
port = None
deadline = time.time() + 20
while time.time() < deadline and port is None:
    line = proc.stdout.readline()
    if not line:
        break
    if "listening on" in line:
        port = int(line.rsplit(" ", 1)[1])
if port is None:
    case("server starts and prints its port", False)
    proc.kill()
    print("1 failed")
    sys.exit(1)


def call(method, path, body=None, sid=None):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), method=method,
                                 data=json.dumps(body).encode() if body is not None else b"")
    if sid:
        req.add_header("cookie", "sid=" + sid)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.headers.get("set-cookie") or "", json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("set-cookie") or "", json.loads(e.read() or b"null")


def parse(cookie):
    parts = [p.strip() for p in cookie.split(";")]
    sid = parts[0].split("=", 1)[1] if parts and parts[0].startswith("sid=") else None
    attrs = {p.split("=", 1)[0].lower(): (p.split("=", 1)[1] if "=" in p else True) for p in parts[1:]}
    return sid, attrs


def flags_ok(attrs):
    return attrs.get("httponly") is True and attrs.get("path") == "/" and str(attrs.get("samesite", "")).lower() == "lax"


def expires_in(sid):
    status, _, body = call("GET", "/me", sid=sid)
    return status, (body or {}).get("expiresAt", 0) - int(time.time() * 1000) if status == 200 else None


try:
    status, cookie, _ = call("POST", "/login", {"email": "ana@example.test", "password": "correct horse", "remember": True})
    sid, attrs = parse(cookie)
    case("remember: login cookie has Max-Age=2592000 and the flags", status == 200 and attrs.get("max-age") == "2592000"
         and flags_ok(attrs), cookie)
    st, left = expires_in(sid)
    case("remember: session expires in about 30 days", st == 200 and left and abs(left - DAYS30) < 120000, "%s %s" % (st, left))

    status, cookie2, _ = call("POST", "/refresh", sid=sid)
    sid2, attrs2 = parse(cookie2)
    case("reported case: refresh of a remembered session keeps Max-Age=2592000 and the flags",
         status == 200 and attrs2.get("max-age") == "2592000" and flags_ok(attrs2) and sid2 and sid2 != sid, cookie2)
    st, left = expires_in(sid2)
    case("reported case: refreshed remembered session still expires in about 30 days",
         st == 200 and left and abs(left - DAYS30) < 120000, "%s %s" % (st, left))
    case("refresh: the old session id stops working", call("GET", "/me", sid=sid)[0] == 401)
    status, cookie3, _ = call("POST", "/refresh", sid=sid2)
    sid3, attrs3 = parse(cookie3)
    case("a second refresh still keeps it remembered", status == 200 and attrs3.get("max-age") == "2592000", cookie3)

    status, cookie, _ = call("POST", "/login", {"email": "ben@example.test", "password": "battery staple"})
    nsid, nattrs = parse(cookie)
    case("normal: login cookie has no Max-Age, keeps the flags", status == 200 and "max-age" not in nattrs and flags_ok(nattrs), cookie)
    st, left = expires_in(nsid)
    case("normal: session expires in about an hour", st == 200 and left and abs(left - HOUR) < 120000, "%s %s" % (st, left))
    status, cookie, _ = call("POST", "/refresh", sid=nsid)
    nsid2, nattrs2 = parse(cookie)
    st, left = expires_in(nsid2)
    case("normal: refresh keeps it a browser-session cookie with a fresh hour",
         status == 200 and "max-age" not in nattrs2 and flags_ok(nattrs2) and st == 200 and abs(left - HOUR) < 120000,
         "%s %s %s" % (cookie, st, left))

    status, cookie, _ = call("POST", "/logout", sid=sid3)
    _, lattrs = parse(cookie)
    case("regression: logout clears the cookie and ends the session",
         status == 200 and lattrs.get("max-age") == "0" and call("GET", "/me", sid=sid3)[0] == 401, cookie)
    case("regression: wrong password is 401", call("POST", "/login", {"email": "ana@example.test", "password": "no"})[0] == 401)
    case("regression: refresh without a session is 401", call("POST", "/refresh")[0] == 401)
finally:
    proc.kill()

print("%d failed" % len(fails))
sys.exit(1 if fails else 0)
