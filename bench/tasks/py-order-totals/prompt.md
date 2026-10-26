Bug: order 1042 shows one total on the confirmation (`python3 -m shop order 1042`) and a different one on its invoice (`python3 -m shop invoice 1042`). Accounting says the September report doesn't add up either.

Expected behaviour, one money rule everywhere:
- Each line is unit price x quantity, rounded half up to the cent.
- The subtotal is the sum of the rounded lines.
- Tax is 7.25% of the subtotal, rounded half up to the cent. Total = subtotal + tax.
- `order`, `invoice` and `report` all follow this rule, so the same order shows the same line amounts and the same total everywhere; the report's grand total is the sum of its orders' totals.
- Every amount prints with two decimals. Keep each command's layout as it is now.
