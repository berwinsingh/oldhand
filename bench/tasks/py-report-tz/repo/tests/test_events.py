import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from events.__main__ import main


class EventsTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.db = os.path.join(self.dir, "events.jsonl")
        self.cfg = os.path.join(self.dir, "config.json")
        with open(self.cfg, "w") as fh:
            json.dump({"tz": "UTC"}, fh)

    def run_cli(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["--db", self.db, "--config", self.cfg] + list(args))
        return code, buf.getvalue()

    def test_report_lists_events_in_range(self):
        self.run_cli("add", "--at", "2026-03-09T12:00:00Z", "--name", "kickoff")
        self.run_cli("add", "--at", "2026-03-10T12:00:00Z", "--name", "review")
        code, out = self.run_cli("report", "--from", "2026-03-09", "--to", "2026-03-11")
        self.assertEqual(code, 0)
        self.assertIn("kickoff", out)
        self.assertIn("review", out)
        self.assertIn("total: 2", out)

    def test_add_rejects_a_time_without_offset(self):
        code, _ = self.run_cli("add", "--at", "2026-03-09T12:00:00", "--name", "x")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
