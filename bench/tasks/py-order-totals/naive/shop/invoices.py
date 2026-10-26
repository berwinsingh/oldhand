from .orders import totals


def render(order):
    lines, subtotal, tax, total = totals(order)
    out = ["INVOICE %d" % order["id"], "Bill to: %s" % order["customer"]]
    for line, amount in zip(order["lines"], lines):
        out.append("%s,%d,%.3f,%.2f" % (line["sku"], line["qty"], line["price"], amount))
    out.append("SUBTOTAL,%.2f" % subtotal)
    out.append("TAX,%.2f" % tax)
    out.append("TOTAL,%.2f" % total)
    return "\n".join(out)
