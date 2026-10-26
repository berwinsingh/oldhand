import unittest

from shop import invoices, orders, reports

ORDER = {"id": 1, "date": "2026-09-01", "customer": "T", "lines": [{"sku": "A", "name": "A", "price": 10.0, "qty": 2}]}


class ShopTest(unittest.TestCase):
    def test_confirmation_total(self):
        self.assertIn("21.45", orders.confirmation(ORDER))

    def test_invoice_total(self):
        self.assertIn("TOTAL,21.45", invoices.render(ORDER))

    def test_report_counts_the_month(self):
        self.assertIn("orders: 1  total: 21.45", reports.monthly([ORDER], "2026-09"))


if __name__ == "__main__":
    unittest.main()
