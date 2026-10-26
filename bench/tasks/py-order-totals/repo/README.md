# shop

Order confirmations, invoices and a monthly sales report for a small grocery shop.
Unit prices can have three decimals (goods sold by weight).

    python3 -m shop order 1042        # the confirmation the customer sees
    python3 -m shop invoice 1042      # the invoice accounting sends
    python3 -m shop report 2026-09    # monthly sales

Data lives in `orders.json`. Run the tests with `python3 -m unittest discover -s tests`.
