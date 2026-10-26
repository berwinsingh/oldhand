"""Hidden acceptance check for py-order-totals. Usage: check.py <work dir>. Exit 0 when every case passes.
Expected amounts are computed here with Decimal, independently of the code under test."""
import json
import os
import re
import subprocess
import sys
import tempfile
from decimal import ROUND_HALF_UP, Decimal

work = os.path.abspath(sys.argv[1])
fails = []
CENT = Decimal("0.01")
ORDERS = [
    {"id": 1, "date": "2026-09-03", "customer": "Ana", "lines": [
        {"sku": "APPLE-KG", "name": "Apples", "price": 2.345, "qty": 3},
        {"sku": "MILK", "name": "Milk 1L", "price": 1.19, "qty": 2}]},
    {"id": 2, "date": "2026-09-14", "customer": "Ben", "lines": [
        {"sku": "CHEESE-KG", "name": "Cheddar", "price": 14.995, "qty": 3},
        {"sku": "BREAD", "name": "Sourdough", "price": 4.5, "qty": 1},
        {"sku": "OLIVE-KG", "name": "Olives", "price": 11.335, "qty": 4},
        {"sku": "EGGS", "name": "Eggs x12", "price": 3.99, "qty": 2}]},
    {"id": 3, "date": "2026-09-20", "customer": "Cai", "lines": [
        {"sku": "HAM-KG", "name": "Ham", "price": 1.005, "qty": 1},
        {"sku": "FIG-KG", "name": "Figs", "price": 0.665, "qty": 7}]},
    {"id": 4, "date": "2026-09-30", "customer": "Dee", "lines": [
        {"sku": "NUT-KG", "name": "Walnuts", "price": 8.085, "qty": 9},
        {"sku": "OIL", "name": "Olive oil", "price": 12.4, "qty": 1}]},
    {"id": 5, "date": "2026-10-01", "customer": "Eli", "lines": [{"sku": "RICE-KG", "name": "Rice", "price": 3.125, "qty": 5}]},
]


def q(v):
    return v.quantize(CENT, ROUND_HALF_UP)


def expected(order):
    lines = [q(Decimal(str(l["price"])) * l["qty"]) for l in order["lines"]]
    sub = sum(lines, Decimal(0))
    tax = q(sub * Decimal("0.0725"))
    return lines, sub, tax, sub + tax


def case(label, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else "  " + detail))
    if not ok:
        fails.append(label)


path = os.path.join(tempfile.mkdtemp(), "orders.json")
with open(path, "w") as fh:
    json.dump(ORDERS, fh)


def cli(*args):
    p = subprocess.run([sys.executable, "-m", "shop", "--data", path] + list(args), cwd=work, capture_output=True,
                       text=True, timeout=60)
    return p.returncode, p.stdout, p.stderr


def amounts(text):
    return re.findall(r"-?\d+\.\d\d(?![\d%])", text)


for o in ORDERS[:4]:
    lines, sub, tax, total = expected(o)
    code, conf, err = cli("order", str(o["id"]))
    nums = amounts(conf)
    case("order %d: confirmation lines, subtotal, tax, total" % o["id"],
         code == 0 and nums == [str(x) for x in lines + [sub, tax, total]], "got %s want %s %s" % (
             nums, [str(x) for x in lines + [sub, tax, total]], err[-120:]))
    code, inv, err = cli("invoice", str(o["id"]))
    rows = [r.split(",") for r in inv.splitlines()[2:]]
    want_rows = [[l["sku"], str(l["qty"]), "%.3f" % l["price"], str(a)] for l, a in zip(o["lines"], lines)]
    want_rows += [["SUBTOTAL", str(sub)], ["TAX", str(tax)], ["TOTAL", str(total)]]
    case("order %d: invoice matches the same rule and layout" % o["id"], code == 0 and rows == want_rows,
         "got %s want %s" % (rows, want_rows))

code, rep, err = cli("report", "2026-09")
want = ["Sales 2026-09"]
grand = Decimal(0)
for o in ORDERS[:4]:
    t = expected(o)[3]
    grand += t
    want.append("%d  %-6s %10s" % (o["id"], o["customer"], t))
want.append("orders: 4  total: %s" % grand)
case("report: each order's total and the grand total", code == 0 and rep.strip().splitlines() == want,
     "got %r want %r" % (rep.strip().splitlines(), want))
code, rep, err = cli("report", "2026-10")
case("report: another month", code == 0 and rep.strip().splitlines()[-1] == "orders: 1  total: %s" % expected(ORDERS[4])[3],
     repr(rep[-80:]))
code, out, err = cli("order", "999")
case("regression: unknown order exits 2", code == 2, str(code))

print("%d failed" % len(fails))
sys.exit(1 if fails else 0)
