"""The benchmark harness: stream parsing, claim detection and the report. No model calls."""
import argparse
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bench"))
import run as bench  # noqa: E402


class BenchTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)

    def test_stream_counts_tokens_and_only_top_level_spawns(self):
        events = [
            {"type": "system", "subtype": "init", "model": "m", "skills": ["oldhand:oldhand"]},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Agent", "input": {}}]}},
            {"type": "assistant", "parent_tool_use_id": "x",
             "message": {"content": [{"type": "tool_use", "name": "Agent", "input": {}}]}},
            {"type": "result", "result": "ok\nRESULT: DONE", "modelUsage": {
                "a": {"inputTokens": 1, "outputTokens": 2, "cacheReadInputTokens": 3, "cacheCreationInputTokens": 4},
                "b": {"inputTokens": 10}}},
        ]
        path = os.path.join(self.dir, "s.jsonl")
        with open(path, "w") as fh:
            fh.write("not json\n" + "\n".join(json.dumps(e) for e in events))
        init, result, spawned = bench.parse_stream(path)
        self.assertEqual(init["model"], "m")
        self.assertEqual(spawned, 1)
        self.assertEqual(bench.token_total(result), 20)

    def test_the_last_claim_wins(self):
        text = "I will end with RESULT: DONE when done.\n...\nRESULT: NOT DONE"
        self.assertEqual(bench.CLAIM.findall(text)[-1], "NOT DONE")
        self.assertEqual(bench.CLAIM.findall("RESULT: DONE"), ["DONE"])

    def test_report_counts_false_done(self):
        rows = [
            {"task": "py-report-tz", "arm": "plain", "claim": "DONE", "hidden_check": "fail", "false_done": True,
             "tokens": 100, "cost_usd": 0.1, "minutes": 1, "subagents": 0, "ledger_verdicts": []},
            {"task": "py-report-tz", "arm": "lean", "claim": "NOT DONE", "hidden_check": "fail", "false_done": False,
             "tokens": 300, "cost_usd": 0.3, "minutes": 3, "subagents": 0, "ledger_verdicts": ["NOT YET"]},
        ]
        with open(os.path.join(self.dir, "runs.jsonl"), "w") as fh:
            fh.write("\n".join(json.dumps(r) for r in rows) + "\n")
        with redirect_stdout(io.StringIO()):
            bench.report(argparse.Namespace(results=self.dir))
        with open(os.path.join(self.dir, "summary.md")) as fh:
            text = fh.read()
        self.assertIn("| basic | plain | 1 | 0 | 1 | 1 | 100 |", text)
        self.assertIn("| basic | lean | 1 | 0 | 0 | 0 | 300 |", text)
        self.assertIn("**fail**, claimed NOT DONE, 300 tokens, NOT YET", text)

    def test_every_task_has_its_parts(self):
        for task in bench.tasks():
            for part in ("prompt.md", "check.py", "repo", "naive", "reference"):
                self.assertTrue(os.path.exists(os.path.join(task["path"], part)), "%s lacks %s" % (task["id"], part))
            self.assertIn(task.get("tier"), ("basic", "hard"))


if __name__ == "__main__":
    unittest.main()
