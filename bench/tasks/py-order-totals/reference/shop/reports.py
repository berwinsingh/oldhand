from decimal import Decimal

from .money import totals


def monthly(all_orders, month):
    rows = [o for o in all_orders if o["date"].startswith(month)]
    out = ["Sales %s" % month]
    grand = Decimal("0")
    for o in sorted(rows, key=lambda o: o["id"]):
        t = totals(o)[3]
        grand += t
        out.append("%d  %-6s %10.2f" % (o["id"], o["customer"], t))
    out.append("orders: %d  total: %.2f" % (len(rows), grand))
    return "\n".join(out)
