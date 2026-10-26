from .tax import TAX_RATE


def order_total(order):
    subtotal = sum(l["price"] * l["qty"] for l in order["lines"])
    return subtotal * (1 + TAX_RATE)


def monthly(all_orders, month):
    rows = [o for o in all_orders if o["date"].startswith(month)]
    out = ["Sales %s" % month]
    grand = 0.0
    for o in sorted(rows, key=lambda o: o["id"]):
        t = order_total(o)
        grand += t
        out.append("%d  %-6s %10.2f" % (o["id"], o["customer"], t))
    out.append("orders: %d  total: %.2f" % (len(rows), grand))
    return "\n".join(out)
