from .money import totals


def confirmation(order):
    lines, subtotal, tax, total = totals(order)
    out = ["Order %d for %s" % (order["id"], order["customer"])]
    for line, amount in zip(order["lines"], lines):
        out.append("  %-12s x%-3d %10.2f" % (line["name"], line["qty"], amount))
    out.append("  %-17s %10.2f" % ("Subtotal", subtotal))
    out.append("  %-17s %10.2f" % ("Tax 7.25%", tax))
    out.append("  %-17s %10.2f" % ("Total", total))
    return "\n".join(out)
