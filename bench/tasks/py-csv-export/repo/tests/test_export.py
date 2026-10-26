import unittest

from contacts.export import render

FIELDS = ["name", "email", "company", "notes"]
ROWS = [{"name": "Ada", "email": "ada@example.com", "company": "Engines", "notes": "first"}]


class ExportTest(unittest.TestCase):
    def test_csv_has_a_header_and_one_row(self):
        lines = render(ROWS, FIELDS, "csv").splitlines()
        self.assertEqual(lines[0], "name,email,company,notes")
        self.assertEqual(lines[1], "Ada,ada@example.com,Engines,first")

    def test_tsv_uses_tabs(self):
        self.assertEqual(render(ROWS, FIELDS, "tsv").splitlines()[1], "Ada\tada@example.com\tEngines\tfirst")


if __name__ == "__main__":
    unittest.main()
