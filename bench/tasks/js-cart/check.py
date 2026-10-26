"""Hidden acceptance check for js-cart. Usage: check.py <work dir>. Exit 0 when every case passes.
Expected values are computed here with Decimal, independently of the code under test."""
import json
import os
import subprocess
import sys
import tempfile
from decimal import ROUND_HALF_UP, Decimal

work = os.path.abspath(sys.argv[1])
fails = []
CENT = Decimal("0.01")


def case(label, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else "  " + detail))
    if not ok:
        fails.append(label)


def expected(cart):
    sub = sum(Decimal(str(i["price"])) * i["qty"] for i in cart["items"])
    code = cart.get("code") or ""
    if code.startswith("PERCENT"):
        disc = (sub * Decimal(code[7:]) / 100).quantize(CENT, ROUND_HALF_UP)
    elif code.startswith("FIXED"):
        disc = min(sub, Decimal(code[5:]))
    else:
        disc = Decimal(0)
    tax = ((sub - disc) * Decimal("0.0825")).quantize(CENT, ROUND_HALF_UP)
    vals = [sub, disc, tax, sub - disc + tax]
    return ["%s: %s" % (k, v.quantize(CENT)) for k, v in zip(["subtotal", "discount", "tax", "total"], vals)]


def run(cart):
    path = os.path.join(tempfile.mkdtemp(), "cart.json")
    with open(path, "w") as fh:
        json.dump(cart, fh)
    p = subprocess.run(["node", "bin/cart.js", "total", path], cwd=work, capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout.strip().splitlines(), p.stderr


CARTS = [
    ("reported case: 3 x 0.10", {"items": [{"sku": "A", "price": 0.1, "qty": 3}]}),
    ("tax rounds half up (2.00 -> tax 0.165)", {"items": [{"sku": "A", "price": 2.0, "qty": 1}]}),
    ("PERCENT10 of 10.05 rounds half up", {"items": [{"sku": "A", "price": 10.05, "qty": 1}], "code": "PERCENT10"}),
    ("PERCENT15 on many lines", {"items": [{"sku": "A", "price": 19.99, "qty": 3}, {"sku": "B", "price": 0.07, "qty": 7},
                                           {"sku": "C", "price": 1.15, "qty": 1}], "code": "PERCENT15"}),
    ("tax on 1.30 (0.10725)", {"items": [{"sku": "A", "price": 0.65, "qty": 2}]}),
    ("PERCENT25 of 4.10 (1.025)", {"items": [{"sku": "A", "price": 4.1, "qty": 1}], "code": "PERCENT25"}),
    ("FIXED5 on a cart under five dollars stops at zero", {"items": [{"sku": "A", "price": 3.5, "qty": 1}], "code": "FIXED5"}),
    ("FIXED5 on a normal cart", {"items": [{"sku": "A", "price": 40, "qty": 1}], "code": "FIXED5"}),
    ("big cart", {"items": [{"sku": "A", "price": 1234.56, "qty": 7}, {"sku": "B", "price": 0.01, "qty": 99}]}),
]
for label, cart in CARTS:
    code, lines, err = run(cart)
    want = expected(cart)
    case(label, code == 0 and lines == want, "got %s want %s %s" % (lines, want, err.strip()[-120:]))

code, lines, err = run({"items": [{"sku": "A", "price": 5, "qty": 1}], "code": "BOGUS50"})
case("unknown code: exit 2 and stderr names it", code == 2 and "BOGUS50" in err, "exit %s stderr %r" % (code, err[-200:]))

print("%d failed" % len(fails))
sys.exit(1 if fails else 0)
