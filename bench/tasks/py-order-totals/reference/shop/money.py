"""The shop's one money rule, in Decimal: lines half up to the cent, tax half up on the subtotal."""
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
TAX_RATE = Decimal("0.0725")


def cents(value):
    return value.quantize(CENT, ROUND_HALF_UP)


def totals(order):
    lines = [cents(Decimal(str(l["price"])) * l["qty"]) for l in order["lines"]]
    subtotal = sum(lines, Decimal("0"))
    tax = cents(subtotal * TAX_RATE)
    return lines, subtotal, tax, subtotal + tax
