import os
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from _load import cli, load

mutate = load("oldhand-build", "mutate")
ledger = load("oldhand", "ledger")

# CRLF line endings and no final newline, so a sloppy restore would show.
CALC = b"def add(a, b):\r\n    return a + b\r\n\r\n\r\ndef unused():\r\n    return 1"
TEST = b"""import unittest
import calc


class T(unittest.TestCase):
    def test_add(self):
        self.assertEqual(calc.add(2, 3), 5)
"""


class Mutate(unittest.TestCase):
    def setUp(self):
        self.d = os.path.realpath(tempfile.mkdtemp())
        self.calc = os.path.join(self.d, "calc.py")
        with open(self.calc, "wb") as fh:
            fh.write(CALC)
        with open(os.path.join(self.d, "test_calc.py"), "wb") as fh:
            fh.write(TEST)
        self.test = "cd %s && %s -m unittest -q test_calc" % (shlex.quote(self.d), shlex.quote(sys.executable))

    def tearDown(self):
        shutil.rmtree(self.d)

    def same(self):
        with open(self.calc, "rb") as fh:
            self.assertEqual(fh.read(), CALC)

    def run_it(self, find, replace, test=None, **kw):
        return mutate.run(self.calc, find, replace, test or self.test, **kw)

    def test_killed(self):
        result, _, output, restored = self.run_it("return a + b", "return a - b")
        self.assertEqual(result, "KILLED", output)
        self.assertTrue(restored)
        self.same()

    def test_survived(self):
        result, reason, _, _ = self.run_it("return 1", "return 2")
        self.assertEqual(result, "SURVIVED")
        self.assertIn("does not guard", reason)
        self.same()

    def test_syntax_error_is_inconclusive(self):
        result, reason, _, _ = self.run_it("return a + b", "return a +")
        self.assertEqual(result, "ERROR")
        self.assertIn("SyntaxError", reason)
        self.same()

    def test_command_that_cannot_start_is_inconclusive(self):
        result, _, _, _ = self.run_it("return a + b", "return a - b", test="no-such-command-oldhand-test")
        self.assertEqual(result, "ERROR")
        self.same()

    def test_find_must_match_exactly_once(self):
        with self.assertRaises(mutate.UsageError) as e:
            self.run_it("return", "yield")
        self.assertIn("matches 2 times", str(e.exception))
        with self.assertRaises(mutate.UsageError) as e:
            self.run_it("return a * b", "return a / b")
        self.assertIn("not found", str(e.exception))
        with self.assertRaises(mutate.UsageError):
            self.run_it("return 1", "return 1")
        self.same()

    def check(self, body):
        """A test command that runs check.py: passes on the original calc.py, does `body` on the mutant."""
        with open(os.path.join(self.d, "check.py"), "w") as fh:
            fh.write("import os, subprocess, sys, time\nimport calc\nif calc.add(2, 3) != 5:\n")
            fh.write("".join("    %s\n" % line for line in body))
        return "cd %s && %s check.py" % (shlex.quote(self.d), shlex.quote(sys.executable))

    def test_timeout_restores_byte_for_byte(self):
        slow = self.check(["time.sleep(30)"])
        result, reason, _, restored = self.run_it("return a + b", "return a - b", test=slow, timeout=2)
        self.assertEqual(result, "ERROR")
        self.assertIn("timed out", reason)
        self.assertTrue(restored)
        self.same()

    def test_ctrl_c_restores(self):
        real = mutate.run_test
        calls = []

        def interrupted(cmd, timeout):
            calls.append(cmd)
            if len(calls) == 1:
                return 0, "control run passed"
            with open(self.calc, "rb") as fh:
                self.assertNotEqual(fh.read(), CALC)  # the mutant is in place while the test runs
            raise KeyboardInterrupt

        mutate.run_test = interrupted
        try:
            with self.assertRaises(KeyboardInterrupt):
                self.run_it("return a + b", "return a - b")
        finally:
            mutate.run_test = real
        self.same()
        self.assertFalse(os.path.exists(mutate.lock_path(self.calc)))

    @unittest.skipUnless(os.name == "posix", "posix signals")
    def test_sigterm_from_the_host_restores_and_ends_the_test(self):
        pid_file = os.path.join(self.d, "child.pid")
        test = self.check(["open(%r, 'w').write(str(os.getpid()))" % pid_file, "time.sleep(30)", "sys.exit(1)"])
        p = subprocess.Popen([sys.executable, mutate.__file__, "--file", self.calc, "--find", "return a + b",
                              "--replace", "return a - b", "--test", test], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, universal_newlines=True)
        deadline = time.time() + 20
        while not os.path.exists(pid_file) and time.time() < deadline:
            time.sleep(0.05)
        self.assertTrue(os.path.exists(pid_file), "the mutant run never started")
        time.sleep(0.2)
        p.send_signal(signal.SIGTERM)
        out, err = p.communicate(timeout=20)
        self.assertEqual(p.returncode, 3, err)
        self.assertIn("cp '", out)  # the backup and the copy-back command were printed before the test ran
        self.assertIn("interrupted", err)
        self.same()
        with open(pid_file) as fh:
            child = int(fh.read())
        for _ in range(40):
            try:
                os.kill(child, 0)
            except ProcessLookupError:
                break
            time.sleep(0.05)
        else:
            self.fail("the test command was left running")

    def test_one_run_per_file_at_a_time(self):
        lock = mutate.lock_path(self.calc)
        with open(lock, "w") as fh:
            fh.write("pid 1\n")
        try:
            with self.assertRaises(mutate.UsageError) as e:
                self.run_it("return a + b", "return a - b")
            self.assertIn("one at a time", str(e.exception))
        finally:
            os.remove(lock)
        self.same()
        self.run_it("return a + b", "return a - b")
        self.assertFalse(os.path.exists(lock))

    def test_an_edit_during_the_test_is_never_overwritten(self):
        test = self.check(["open('calc.py', 'ab').write(b'# edit made while the test ran')", "sys.exit(1)"])
        lock = mutate.lock_path(self.calc)
        try:
            _, _, _, restored = self.run_it("return a + b", "return a - b", test=test)
            self.assertFalse(restored)
            with open(self.calc, "rb") as fh:
                self.assertTrue(fh.read().endswith(b"# edit made while the test ran"))
            self.assertTrue(os.path.exists(lock))  # kept until a person sorts it out
        finally:
            if os.path.exists(lock):
                with open(lock) as fh:
                    backup = fh.read().split("backup ", 1)[1].strip()
                shutil.rmtree(os.path.dirname(backup), ignore_errors=True)
                os.remove(lock)

    def test_a_check_that_fails_or_runs_nothing_on_the_original_is_inconclusive(self):
        for test in ("%s -c 'import sys; sys.exit(1)'" % shlex.quote(sys.executable), "exit 2", "exit 5"):
            with self.subTest(test=test):
                result, reason, _, _ = self.run_it("return a + b", "return a + b + 0", test=test)
                self.assertEqual(result, "ERROR")
                self.assertIn("original code", reason)
                self.same()
        result, reason, _, _ = self.run_it("return a + b", "return a - b", test=self.check(["sys.exit(5)"]))
        self.assertEqual(result, "ERROR")  # pytest's "no tests collected" is not a kill
        self.assertIn("exit 5", reason)

    def test_a_helper_left_running_does_not_hold_the_run(self):
        test = self.check(["subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(6)'], "
                           "start_new_session=True)", "sys.exit(1)"])
        start = time.time()
        result, _, output, restored = self.run_it("return a + b", "return a - b", test=test, timeout=5)
        self.assertEqual(result, "KILLED", output)
        self.assertLess(time.time() - start, 4)
        self.assertTrue(restored)
        self.same()

    def test_ledger_records_a_mutation_check(self):
        task = os.path.join(self.d, ".oldhand", "t")
        ledger.init(task, "calc")
        with open(os.path.join(task, "contract.md"), "w") as fh:
            fh.write("- AC1: add adds (proof: unit)\n")
        ledger.sync(task)
        with self.assertRaises(mutate.UsageError):
            self.run_it("return a + b", "return a - b", ledger_dir=task, cid="AC9")
        with self.assertRaises(mutate.UsageError):
            self.run_it("return a + b", "return a - b", ledger_dir=task)
        self.same()
        result, _, _, _ = self.run_it("return a + b", "return a - b", ledger_dir=task, cid="AC1")
        self.assertEqual(result, "KILLED")
        checks = ledger.load(task)["checks"]
        self.assertEqual([(c["criterion"], c["kind"], c["status"], c["by"]) for c in checks],
                         [("AC1", "mutation", "pass", "mutate.py")])
        self.assertIn("KILLED", checks[0]["evidence"])

    def test_command_line_exit_codes(self):
        base = ["--file", self.calc, "--test", self.test]
        code, out, _ = cli("oldhand-build", "mutate", "--find", "return a + b", "--replace", "return a - b", *base)
        self.assertEqual(code, 0, out)
        self.assertIn("KILLED", out)
        self.assertIn("restored", out)
        code, out, _ = cli("oldhand-build", "mutate", "--find", "return 1", "--replace", "return 2", *base)
        self.assertEqual(code, 1)
        code, out, _ = cli("oldhand-build", "mutate", "--find", "return a + b", "--replace", "return (", *base)
        self.assertEqual(code, 2)
        code, _, err = cli("oldhand-build", "mutate", "--find", "return", "--replace", "x", *base)
        self.assertEqual(code, 3)
        self.assertIn("exactly once", err)
        code, _, _ = cli("oldhand-build", "mutate", "--file", self.calc)
        self.assertEqual(code, 3)
        self.same()

    def test_never_calls_git(self):
        with open(mutate.__file__, encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn('"git"', src)
        self.assertNotIn("'git'", src)


if __name__ == "__main__":
    unittest.main()
