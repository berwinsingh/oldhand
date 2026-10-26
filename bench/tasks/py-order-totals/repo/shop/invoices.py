from .tax import TAX_RATE


def render(order):
    out = ["INVOICE %d" % order["id"], "Bill to: %s" % order["customer"]]
    subtotal = 0.0
    for line in order["lines"]:
        amount = line["price"] * line["qty"]
        subtotal += amount
        out.append("%s,%d,%.3f,%.2f" % (line["sku"], line["qty"], line["price"], amount))
    tax = subtotal * TAX_RATE
    out.append("SUBTOTAL,%.2f" % subtotal)
    out.append("TAX,%.2f" % tax)
    out.append("TOTAL,%.2f" % (subtotal + tax))
    return "\n".join(out)
