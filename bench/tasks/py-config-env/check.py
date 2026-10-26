"""Hidden acceptance check for py-config-env. Usage: check.py <work dir>. Exit 0 when every case passes."""
import json
import os
import subprocess
import sys

work = os.path.abspath(sys.argv[1])
fails = []
BASE_ENV = {k: v for k, v in os.environ.items() if not k.upper().startswith("APP_")}


def show(env, *args):
    e = dict(BASE_ENV, **env)
    p = subprocess.run([sys.executable, "-m", "appcfg", "show"] + list(args), cwd=work, env=e,
                       capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout, p.stderr


def case(label, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else "  " + detail))
    if not ok:
        fails.append(label)


def cfg(env):
    code, out, err = show(env, "--json")
    try:
        return code, json.loads(out), err
    except ValueError:
        return code, None, err


code, c, err = cfg({"APP__DB__PORT": "6543"})
case("reported case: APP__DB__PORT overrides db.port as an int", code == 0 and c and c["db"]["port"] == 6543
     and type(c["db"]["port"]) is int, "exit %s %s" % (code, c and c["db"]))
code, c, err = cfg({"APP__DB__POOL__SIZE": "12", "APP__DB__POOL__TIMEOUT": "7"})
case("three levels deep, int and float kept", code == 0 and c and c["db"]["pool"]["size"] == 12
     and type(c["db"]["pool"]["timeout"]) is float and c["db"]["pool"]["timeout"] == 7.0, str(c and c["db"]))
code, c, err = cfg({"APP__FEATURES__SEARCH": "false", "APP__DEBUG": "TRUE"})
case("bools: 'false' is False and 'TRUE' is True", code == 0 and c and c["features"]["search"] is False
     and c["debug"] is True, str(c and (c["features"], c["debug"])))
code, c, err = cfg({"APP__FEATURES__SEARCH": "0"})
case("bool '0' is False", code == 0 and c and c["features"]["search"] is False, str(c and c["features"]))
code, c, err = cfg({"APP__Db__Host": "db.internal"})
case("names after the prefix are case-insensitive", code == 0 and c and c["db"]["host"] == "db.internal", str(c and c["db"]))
code, c, err = cfg({"APP__CACHE__REDIS__URL": "redis://x:6379"})
case("a new path is added as a string with its levels", code == 0 and c and c.get("cache", {}).get("redis", {}).get("url")
     == "redis://x:6379", str(c and c.get("cache")))
code, out, err = show({"APP__DB__PORT": "abc"}, "--json")
case("bad value: exit 2, names the variable, no traceback", code == 2 and "APP__DB__PORT" in err and "Traceback" not in err,
     "exit %s stderr %r" % (code, err[-200:]))
code, out, err = show({"APP_PORT": "9000"}, "--key", "port")
case("regression: APP_PORT still works", code == 0 and out.strip() == "9000", "exit %s %r" % (code, out))
code, c, err = cfg({})
case("regression: no env shows the file unchanged", code == 0 and c and c["db"]["port"] == 5432 and c["debug"] is False, str(c))

print("%d failed" % len(fails))
sys.exit(1 if fails else 0)
