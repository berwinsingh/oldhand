import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

from _load import GIT_ENV, cli, git, git_repo, load, script

ledger = load("oldhand", "ledger")
_saved_env = {}

CONTRACT = """# Guest signup

Source: prompt  ·  Mode: {mode}

## Acceptance criteria
- AC1: A guest can sign up from /signup (proof: e2e)
- AC2: POST /api/guests returns 201 (proof: integration)
- R1: Members still sign in from /login
"""


def setUpModule():
    # The rerun key lives outside every project: here in a folder of its own, never the user's real one.
    _saved_env["state"] = tempfile.mkdtemp()
    _saved_env["folders"] = ledger._key_folders
    ledger._key_folders = lambda: [os.path.join(_saved_env["state"], "oldhand")]
    for k, v in dict(GIT_ENV, XDG_STATE_HOME=_saved_env["state"]).items():
        _saved_env[k] = os.environ.get(k)
        os.environ[k] = v


def tearDownModule():
    ledger._key_folders = _saved_env.pop("folders")
    shutil.rmtree(_saved_env.pop("state"))
    for k, v in _saved_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


class Base(unittest.TestCase):
    mode = "implement"
    use_git = False

    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp())
        if self.use_git:
            git_repo(self.root)
        self.d = os.path.join(self.root, ".oldhand", "t")
        ledger.init(self.d, "Guest signup", self.mode)
        self.contract(CONTRACT.format(mode=self.mode))
        ledger.sync(self.d)

    def tearDown(self):
        shutil.rmtree(self.root)

    def contract(self, text):
        with open(os.path.join(self.d, "contract.md"), "w", encoding="utf-8") as fh:
            fh.write(text)

    def evidence(self, name="ev.txt"):
        with open(os.path.join(self.d, name), "w") as fh:
            fh.write("saw it\n")
        return name

    def rec(self, cid, kind="e2e", status="pass", lead=False, ev=None, cmd=None):
        return ledger.record(self.d, cid, kind, status, ev or self.evidence(), "qa:worker",
                             cmd=cmd or "%s %s" % (cid, kind), lead=lead)[0]

    def all_pass(self):
        self.rec("AC1", lead=True)
        self.rec("AC2", "integration")
        self.rec("R1")

    def verdict(self):
        return ledger.evaluate(self.d)

    def row(self, res, cid):
        return next(r for r in res["criteria"] if r["id"] == cid)


class Contract(unittest.TestCase):
    def test_ac_and_r_lines_parse_with_and_without_proof(self):
        mode, found, problems = ledger.parse_contract(
            "Mode: verify\n- AC1: works (proof: unit)\n- R12: old thing still works  \n- AC2: x (proof: manual)\n")
        self.assertEqual(problems, [])
        self.assertEqual(mode, "verify")
        self.assertEqual([(f["id"], f["proof"]) for f in found], [("AC1", "unit"), ("R12", None), ("AC2", "manual")])
        self.assertEqual(found[1]["text"], "old thing still works")

    def test_malformed_lines_are_errors_not_guesses(self):
        for text in ("- AC1: x (proof: smoke)\n", "- AC1 no colon\n", "* AC2: star bullet\n",
                     "- AC1: a\n- AC1: b\n", "Mode: someday\n"):
            with self.subTest(text=text):
                self.assertTrue(ledger.parse_contract(text)[2])

    def test_a_title_with_mode_in_it_is_not_the_mode(self):
        for title in ("# Dark Mode: persist the toggle", "# Edit Mode: Verify button saves draft"):
            with self.subTest(title=title):
                mode, _, problems = ledger.parse_contract(title + "\n\nSource: prompt  ·  Mode: implement\n- AC1: x\n")
                self.assertEqual((mode, problems), ("implement", []))

    def test_default_proof_follows_the_mode(self):
        self.assertEqual(ledger.default_proof("implement"), "e2e")
        self.assertEqual(ledger.default_proof("verify"), "e2e")
        self.assertEqual(ledger.default_proof("plan-only"), "review")
        self.assertEqual(ledger.default_proof("investigate"), "review")


class Sync(Base):
    def test_sync_adds_drops_and_restores(self):
        led = ledger.load(self.d)
        self.assertEqual([(c["id"], c["proof"], c["status"]) for c in led["criteria"]],
                         [("AC1", "e2e", "live"), ("AC2", "integration", "live"), ("R1", "e2e", "live")])
        self.contract("Mode: implement\n- AC1: A guest can sign up (proof: e2e)\n- R1: Members\n- AC3: new\n")
        changes = ledger.sync(self.d)
        self.assertIn("dropped AC2", changes)
        self.assertIn("added AC3", changes)
        with self.assertRaises(ledger.LedgerError):
            self.rec("AC2", "integration")
        with self.assertRaises(ledger.LedgerError):
            self.rec("AC9")
        self.contract(CONTRACT.format(mode="implement"))
        self.assertIn("restored AC2", ledger.sync(self.d))

    def test_a_changed_or_restored_criterion_needs_new_checks(self):
        self.all_pass()
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")
        self.contract(CONTRACT.format(mode="implement").replace("from /signup", "from /signup and /join"))
        self.assertIn("updated AC1", ledger.sync(self.d))
        res = self.verdict()
        self.assertEqual(res["verdict"], "INCOMPLETE", res["reasons"])
        self.assertTrue(any("older wording" in n for n in res["notes"]), res["notes"])
        self.rec("AC1", lead=True)
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")
        self.contract(CONTRACT.format(mode="implement").replace("- AC2: POST /api/guests returns 201 (proof: integration)\n", ""))
        ledger.sync(self.d)
        self.contract(CONTRACT.format(mode="implement"))
        self.assertIn("restored AC2", ledger.sync(self.d))
        self.assertEqual(self.verdict()["verdict"], "INCOMPLETE")

    def test_bad_contract_changes_nothing(self):
        before = ledger.load(self.d)
        self.contract("- AC1: x (proof: smoke)\n")
        with self.assertRaises(ledger.LedgerError):
            ledger.sync(self.d)
        self.assertEqual(ledger.load(self.d)["criteria"], before["criteria"])

    def test_mode_change_in_contract_is_picked_up(self):
        self.contract(CONTRACT.format(mode="plan-only"))
        ledger.sync(self.d)
        led = ledger.load(self.d)
        self.assertEqual(led["mode"], "plan-only")
        self.assertEqual(next(c for c in led["criteria"] if c["id"] == "R1")["proof"], "review")

    def test_init_refuses_an_existing_ledger(self):
        with self.assertRaises(ledger.LedgerError):
            ledger.init(self.d, "again")


class Verdicts(Base):
    def test_verified(self):
        self.all_pass()
        res = self.verdict()
        self.assertEqual(res["verdict"], "VERIFIED", res["reasons"])
        self.assertEqual(res["exit"], 0)
        self.assertIn("staleness is not tracked", " ".join(res["notes"]))

    def test_incomplete_without_contract_or_criteria(self):
        os.remove(os.path.join(self.d, "contract.md"))
        self.assertEqual(self.verdict()["verdict"], "INCOMPLETE")
        self.contract("# nothing yet\n")
        ledger.sync(self.d)
        res = self.verdict()
        self.assertEqual(res["verdict"], "INCOMPLETE")
        self.assertIn("no live criteria", res["reasons"][0])

    def test_incomplete_when_a_criterion_has_no_check(self):
        self.rec("AC1", lead=True)
        self.rec("AC2", "integration")
        res = self.verdict()
        self.assertEqual(res["verdict"], "INCOMPLETE")
        self.assertTrue(any(r.startswith("R1 has no e2e check") for r in res["reasons"]), res["reasons"])
        self.assertEqual(self.row(res, "R1")["status"], "none")

    def test_proof_hierarchy(self):
        self.rec("AC1", lead=True)
        self.rec("R1")
        self.rec("AC2", "unit")  # weaker than integration: does not count
        self.assertEqual(self.verdict()["verdict"], "INCOMPLETE")
        self.rec("AC2", "e2e")  # stronger: counts
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")
        self.assertEqual(ledger.satisfying("unit"), {"unit", "integration", "e2e"})
        self.assertEqual(ledger.satisfying("review"), {"review"})
        self.assertEqual(ledger.satisfying("manual"), {"manual"})

    def test_review_is_only_satisfied_by_review(self):
        self.contract("Mode: implement\n- AC1: docs explain it (proof: review)\n- AC2: works (proof: e2e)\n")
        ledger.sync(self.d)
        self.rec("AC2", lead=True)
        self.rec("AC1", "e2e")
        self.assertEqual(self.verdict()["verdict"], "INCOMPLETE")
        self.rec("AC1", "review")
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")

    def test_baseline_fail_never_counts_but_is_reported(self):
        self.all_pass()
        self.rec("R1", "unit", "baseline-fail")
        res = self.verdict()
        self.assertEqual(res["verdict"], "VERIFIED")
        self.assertTrue(any("pre-existing" in n for n in res["notes"]))
        self.contract(CONTRACT.format(mode="implement") + "- AC3: new rule (proof: unit)\n")
        ledger.sync(self.d)
        ledger.record(self.d, "AC3", "unit", "baseline-fail", "pytest -q: 1 failed", "lead:fable", cmd="pytest -q")
        res = self.verdict()
        self.assertEqual(res["verdict"], "INCOMPLETE")
        self.assertEqual(self.row(res, "AC3")["status"], "none")

    def test_latest_check_wins_and_a_fail_is_not_yet(self):
        self.all_pass()
        self.rec("AC2", "integration", "fail")
        res = self.verdict()
        self.assertEqual(res["verdict"], "NOT YET")
        self.assertEqual(self.row(res, "AC2")["status"], "fail")
        self.assertTrue(any(r.startswith("AC2 fails") for r in res["reasons"]))
        self.rec("AC2", "integration", "pass")
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")

    def test_a_later_pass_of_one_check_never_hides_another_checks_fail(self):
        self.all_pass()
        self.rec("AC2", "e2e", "fail", cmd="qa.py scenario S2")
        self.rec("AC2", "e2e", "pass", cmd="qa.py scenario S4")
        res = self.verdict()
        self.assertEqual(res["verdict"], "NOT YET")
        row = self.row(res, "AC2")
        self.assertEqual((row["status"], row["check"]), ("fail", "C4"))
        self.assertEqual(row["counted"], ["C2", "C4", "C5"])
        self.rec("AC2", "e2e", "pass", cmd="qa.py scenario S2")  # the same check re-run replaces its old run
        res = self.verdict()
        self.assertEqual(res["verdict"], "VERIFIED", res["reasons"])
        self.assertEqual(self.row(res, "AC2")["counted"], ["C2", "C5", "C6"])

    def test_every_record_names_its_check(self):
        for cmd in (None, "", "  "):
            with self.assertRaises(ledger.LedgerError) as e:
                ledger.record(self.d, "AC1", "e2e", "fail", "scenario S2 failed: saw 7 rows", "lead:x", cmd=cmd)
            self.assertIn("--cmd", str(e.exception))

    def test_a_voided_check_is_listed_not_counted(self):
        self.all_pass()
        bad = self.rec("AC2", "e2e", "fail", cmd="qa.py scenario S4")
        self.assertEqual(self.verdict()["verdict"], "NOT YET")
        with self.assertRaises(ledger.LedgerError):
            ledger.void(self.d, bad["id"], " ")
        ledger.void(self.d, bad["id"], "S4 expected the wrong status code and is removed")
        res = self.verdict()
        self.assertEqual(res["verdict"], "VERIFIED", res["reasons"])
        self.assertTrue(any("voided" in n and "wrong status code" in n for n in res["notes"]), res["notes"])

    def test_a_baseline_fail_run_replaces_the_fail_of_the_same_check(self):
        self.all_pass()
        self.rec("AC2", "e2e", "fail", cmd="pytest tests/test_import.py")
        self.assertEqual(self.verdict()["verdict"], "NOT YET")
        self.rec("AC2", "e2e", "baseline-fail", cmd="pytest tests/test_import.py")
        res = self.verdict()
        self.assertEqual(res["verdict"], "VERIFIED", res["reasons"])
        self.assertTrue(any("pre-existing" in n for n in res["notes"]))

    def test_blocked(self):
        self.all_pass()
        self.rec("R1", status="blocked", ev="no test account for the member role")
        res = self.verdict()
        self.assertEqual(res["verdict"], "BLOCKED")
        self.assertEqual(res["exit"], 2)
        self.assertIn("no test account", res["reasons"][0])

    def test_evidence_missing_does_not_count(self):
        self.all_pass()
        self.rec("R1", ev="qa/results/S9.json")
        res = self.verdict()
        self.assertEqual(res["verdict"], "INCOMPLETE")
        self.assertIn("evidence missing", self.row(res, "R1")["flags"])
        os.makedirs(os.path.join(self.d, "qa", "results"))
        with open(os.path.join(self.d, "qa", "results", "S9.json"), "w") as fh:
            fh.write("{}")
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")

    def test_text_evidence_and_urls_are_not_paths(self):
        for ev in ("pytest -q: 12 passed", "https://example.test/pr/3", "1.5s", "ok"):
            self.assertFalse(ledger.evidence_missing(self.d, self.root, ev), ev)
        self.assertTrue(ledger.evidence_missing(self.d, self.root, "src/nope.py:12"))
        self.assertTrue(ledger.evidence_missing(self.d, self.root, "shot.png"))

    def test_open_high_finding_blocks_and_low_is_a_follow_up(self):
        self.all_pass()
        f = ledger.finding_add(self.d, "high", "security", "src/x.py:4", "tenant id taken from the body")
        ledger.finding_add(self.d, "low", "simplicity", "src/y.py:9", "helper could be inlined")
        res = self.verdict()
        self.assertEqual(res["verdict"], "NOT YET")
        self.assertEqual([x["id"] for x in res["open_findings"]], ["F1", "F2"])
        ledger.finding_resolve(self.d, f["id"], "fixed", "reads tenant from the session now")
        res = self.verdict()
        self.assertEqual(res["verdict"], "VERIFIED")
        self.assertTrue(any("follow-up" in n for n in res["notes"]))

    def test_deferred_high_needs_the_users_acceptance(self):
        self.all_pass()
        ledger.finding_add(self.d, "medium", "data", "db.py:3", "no rollback path")
        ledger.finding_resolve(self.d, "F1", "deferred", "next sprint")
        self.assertEqual(self.verdict()["verdict"], "NOT YET")
        with self.assertRaises(ledger.LedgerError):
            ledger.finding_resolve(self.d, "F1", "fixed", "x", accepted_by="user")
        with self.assertRaises(ledger.LedgerError):
            ledger.finding_resolve(self.d, "F1", "deferred", "x", accepted_by="lead")
        ledger.finding_resolve(self.d, "F1", "deferred", "user said ship it", accepted_by="user")
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")

    def test_refuted_finding_clears(self):
        self.all_pass()
        ledger.finding_add(self.d, "high", "correctness", "a.py:1", "maybe null")
        ledger.finding_resolve(self.d, "F1", "refuted", "the caller checks it at a.py:0")
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")

    def test_implement_mode_needs_a_lead_e2e_pass(self):
        self.rec("AC1")
        self.rec("AC2", "integration")
        self.rec("R1")
        res = self.verdict()
        self.assertEqual(res["verdict"], "NOT YET")
        self.assertIn("--lead", res["reasons"][0])
        self.rec("AC1", lead=True)
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")

    def test_mutation_checks_are_reported_not_counted(self):
        self.all_pass()
        ledger.record(self.d, "AC2", "mutation", "pass", "KILLED: src/x.py", "mutate.py", cmd="pytest -q")
        res = self.verdict()
        self.assertEqual(res["verdict"], "VERIFIED")
        self.assertTrue(any("KILLED" in n for n in res["notes"]))


class PlanOnly(Base):
    mode = "plan-only"

    def test_no_lead_e2e_needed_and_review_is_the_default(self):
        self.contract("Mode: plan-only\n- AC1: the plan names the fix point\n")
        ledger.sync(self.d)
        self.rec("AC1", "review", ev="plan.md")
        with open(os.path.join(self.d, "plan.md"), "w") as fh:
            fh.write("plan\n")
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")


class Stale(Base):
    use_git = True

    def test_editing_a_tracked_file_makes_checks_stale_and_restamp_clears(self):
        self.all_pass()
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")
        with open(os.path.join(self.root, "a.txt"), "a") as fh:
            fh.write("two\n")
        res = self.verdict()
        self.assertEqual(res["verdict"], "NOT YET")
        self.assertIn("stale", self.row(res, "R1")["flags"])
        led = ledger.load(self.d)
        for ch in led["checks"]:
            self.assertIsNotNone(ledger.restamp(self.d, ch["id"], "a.txt is a fixture no check reads"))
        self.assertIsNone(ledger.restamp(self.d, "C1", "again"))
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")
        with self.assertRaises(ledger.LedgerError):
            ledger.restamp(self.d, "C99", "x")

    def test_a_new_untracked_file_makes_checks_stale(self):
        self.all_pass()
        with open(os.path.join(self.root, "new.py"), "w") as fh:
            fh.write("x = 1\n")
        self.assertEqual(self.verdict()["verdict"], "NOT YET")

    def test_writes_inside_oldhand_never_change_the_fingerprint(self):
        fp = ledger.fingerprint(self.d)
        self.all_pass()
        ledger.finding_add(self.d, "low", "x", "y", "z")
        self.assertEqual(ledger.fingerprint(self.d), fp)
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")

    def test_stale_lead_check_does_not_satisfy_the_lead_rule(self):
        self.rec("AC1", lead=True)
        with open(os.path.join(self.root, "a.txt"), "a") as fh:
            fh.write("two\n")
        self.rec("AC1")
        self.rec("AC2", "integration")
        self.rec("R1")
        res = self.verdict()
        self.assertEqual(res["verdict"], "NOT YET")
        self.assertTrue(any("--lead" in r for r in res["reasons"]))

    def test_init_writes_info_exclude_once(self):
        ledger.init(os.path.join(self.root, ".oldhand", "second"), "Second task")
        with open(os.path.join(self.root, ".git", "info", "exclude")) as fh:
            lines = [ln.strip() for ln in fh.read().splitlines()]
        self.assertEqual(lines.count(".oldhand/"), 1)

    def test_init_survives_a_write_protected_git_folder(self):
        exclude = os.path.join(self.root, ".git", "info", "exclude")
        with open(exclude, "w") as fh:
            fh.write("# nothing\n")
        os.remove(os.path.join(self.root, ".oldhand", ".gitignore"))
        os.chmod(exclude, 0o444)  # what a sandbox that protects .git looks like to init
        try:
            excluded, warning = ledger.init(os.path.join(self.root, ".oldhand", "boxed"), "Boxed")
        finally:
            os.chmod(exclude, 0o644)
        self.assertIsNone(excluded)
        self.assertIn("could not add", warning)
        out = subprocess.run(["git", "status", "--porcelain"], cwd=self.root, stdout=subprocess.PIPE,
                             universal_newlines=True).stdout
        self.assertNotIn(".oldhand", out)

    def test_git_that_fails_is_an_error_not_no_git(self):
        self.all_pass()
        path = os.environ.get("PATH", "")
        os.environ["PATH"] = os.path.join(self.root, "nowhere")  # git missing from PATH
        try:
            with self.assertRaises(ledger.LedgerError) as e:
                self.verdict()
        finally:
            os.environ["PATH"] = path
        self.assertIn("git", str(e.exception))
        shutil.rmtree(os.path.join(self.root, ".git"))  # no repo any more, but the checks were recorded in git
        with self.assertRaises(ledger.LedgerError):
            self.verdict()

    def test_nested_repos_and_external_diff_cannot_hide_a_change(self):
        nested = os.path.join(self.root, "vendor", "lib")
        os.makedirs(nested)
        git_repo(nested)
        fp = ledger.fingerprint(self.d)
        with open(os.path.join(nested, "a.txt"), "a") as fh:
            fh.write("changed inside the nested repo\n")
        self.assertNotEqual(ledger.fingerprint(self.d), fp)
        git(self.root, "config", "diff.external", "true")  # an external diff that prints nothing
        fp = ledger.fingerprint(self.d)
        with open(os.path.join(self.root, "a.txt"), "a") as fh:
            fh.write("two\n")
        self.assertNotEqual(ledger.fingerprint(self.d), fp)


OLD_CHECK_KEYS = {"id", "criterion", "kind", "status", "evidence", "by", "cmd", "lead", "fingerprint", "time",
                  "evidence_hash"}


class Beyond(Base):
    """Shared helpers for the runtime, env and live rules."""
    use_git = True

    def write(self, name, text):
        with open(os.path.join(self.root, name), "w", encoding="utf-8") as fh:
            fh.write(text)

    def stale_text(self, res=None):
        return "\n".join((res or self.verdict())["reasons"])


class RuntimePins(Beyond):
    def setUp(self):
        super().setUp()
        self.saved_probes = ledger.PROBES
        self.ver = os.path.join(tempfile.mkdtemp(), "version")
        self.set_version("Python 3.11.9")
        reader = "import sys; print(open(sys.argv[1]).read())"
        ledger.PROBES = dict(ledger.PROBES, python=[[sys.executable, "-c", reader, self.ver]])

    def tearDown(self):
        ledger.PROBES = self.saved_probes
        shutil.rmtree(os.path.dirname(self.ver))
        super().tearDown()

    def set_version(self, v):
        with open(self.ver, "w") as fh:
            fh.write(v + "\n")

    def test_no_pin_file_and_no_env_names_record_and_decide_as_before(self):
        self.all_pass()
        led = ledger.load(self.d)
        self.assertEqual({k for ch in led["checks"] for k in ch}, OLD_CHECK_KEYS)
        self.assertNotIn("env_salt", led)
        res = self.verdict()
        self.assertEqual(res["verdict"], "VERIFIED")
        with open(os.path.join(self.root, "a.txt"), "a") as fh:
            fh.write("two\n")
        reasons = self.verdict()["reasons"]
        self.assertTrue(reasons and all("recorded on an older tree" in r or "--lead" in r for r in reasons), reasons)

    def test_an_ignored_pin_file_that_changes_makes_checks_stale_and_names_it(self):
        self.write(".gitignore", ".python-version\n")
        self.write(".python-version", "3.11\n")
        self.all_pass()
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")
        fp = ledger.fingerprint(self.d)
        self.write(".python-version", "3.12\n")
        self.assertEqual(ledger.fingerprint(self.d), fp, "git ignores the file, so only the pin stamp sees it")
        res = self.verdict()
        self.assertEqual(res["verdict"], "NOT YET")
        self.assertIn("stale", self.row(res, "R1")["flags"])
        self.assertIn("runtime pin file .python-version changed", self.stale_text(res))
        self.assertIsNone(ledger.restamp(self.d, "C1", "restamp clears files only"))
        self.assertEqual(self.verdict()["verdict"], "NOT YET")

    def test_a_different_runtime_version_now_makes_checks_stale(self):
        self.write(".python-version", "3.11\n")
        self.all_pass()
        self.assertEqual(ledger.load(self.d)["checks"][0]["runtime"], {"python": "3.11.9"})
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")
        self.set_version("Python 3.12.1")
        res = self.verdict()
        self.assertEqual(res["verdict"], "NOT YET")
        self.assertIn("runtime python changed: 3.11.9 -> 3.12.1", self.stale_text(res))
        self.all_pass()
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")

    def test_a_pin_file_added_or_removed_after_a_check_is_a_change(self):
        self.all_pass()
        self.write(".nvmrc", "20\n")
        self.assertIn("runtime pin file .nvmrc added", self.stale_text())
        self.all_pass()
        os.remove(os.path.join(self.root, ".nvmrc"))
        self.assertIn("runtime pin file .nvmrc removed", self.stale_text())

    def fake(self, runtime, code):
        """Point a runtime's probe at a small Python script."""
        path = os.path.join(os.path.dirname(self.ver), runtime + ".py")
        with open(path, "w") as fh:
            fh.write("import os, sys\n" + code)
        ledger.PROBES = dict(ledger.PROBES, **{runtime: [[sys.executable, path]]})

    def test_only_the_version_token_is_kept_and_java_option_vars_never_reach_the_probe(self):
        os.environ["JAVA_TOOL_OPTIONS"] = "-Dtoken=" + SECRET + "-9.9.9"
        try:
            # A JVM prints the option var's value before its version; with the var stripped it prints nothing.
            self.fake("java", "v = os.environ.get('JAVA_TOOL_OPTIONS')\n"
                              "v and print('opts ' + v, file=sys.stderr)\n"
                              "print('openjdk version \"21.0.2\" 2024-01-16', file=sys.stderr)\n")
            self.assertEqual(ledger.probe("java", self.root), "21.0.2")
        finally:
            os.environ.pop("JAVA_TOOL_OPTIONS")
        self.fake("java", "print('Picked up SOME_FUTURE_OPTIONS: 9.9.9-" + SECRET + "', file=sys.stderr)\n"
                          "print('java version \"1.8.0_392\"', file=sys.stderr)\n")
        self.assertEqual(ledger.probe("java", self.root), "1.8.0_392")
        self.fake("node", "print('no version here')\n")
        self.assertEqual(ledger.probe("node", self.root), "unavailable (no version in its output)")
        for out, want in (("v20.11.0", "20.11.0"), ("Python 3.13.0rc1", "3.13.0rc1"),
                          ("rustc 1.75.0 (82e1608df 2023-12-21)", "1.75.0"), ("go version go1.22.1 linux/amd64", "1.22.1"),
                          ("ruby 3.2.2 (2023-03-30 revision e51014f9c0) [x86_64-linux]", "3.2.2")):
            self.fake("node", "print(%r)\n" % out)
            self.assertEqual(ledger.probe("node", self.root), want)

    def test_a_jdk_that_prints_a_dotless_version_is_read_and_a_switch_is_stale(self):
        for out, want in (('openjdk version "21" 2023-09-19', "21"), ('openjdk version "17-ea" 2021-09-14', "17-ea"),
                          ('openjdk version "11.0.22" 2024-01-16', "11.0.22")):
            self.fake("java", "print(%r, file=sys.stderr)\nprint('OpenJDK Runtime Environment (build 21+35)')\n" % out)
            self.assertEqual(ledger.probe("java", self.root), want)
        self.write(".tool-versions", "java openjdk-17\n")
        self.fake("java", "print('openjdk version \"17\" 2021-09-14', file=sys.stderr)\n")
        self.all_pass()
        self.fake("java", "print('openjdk version \"21\" 2023-09-19', file=sys.stderr)\n")
        self.assertIn("runtime java changed: 17 -> 21", self.stale_text())

    def test_no_part_of_a_picked_up_line_is_read_as_the_version(self):
        # A value holding a vertical tab, or a Picked up line that does not start the line, is skipped whole.
        self.fake("java", "print('Picked up JAVA_TOOL_OPTIONS: -Dx=' + %r + '\\x0b9.9.9-tail', file=sys.stderr)\n"
                          "print('[0.1s] Picked up _JAVA_OPTIONS: 8.8.8-' + %r, file=sys.stderr)\n"
                          "print('openjdk version \"21\"', file=sys.stderr)\n" % (SECRET, SECRET))
        self.assertEqual(ledger.probe("java", self.root), "21")

    def test_probes_run_with_toolchain_downloads_switched_off(self):
        self.fake("go", "print('go version go1.22.1-' + os.environ.get('GOTOOLCHAIN', 'auto'))\n")
        self.assertEqual(ledger.probe("go", self.root), "1.22.1-local")
        self.fake("rust", "print('rustc 1.75.0-' + os.environ.get('RUSTUP_AUTO_INSTALL', 'x'))\n")
        self.assertEqual(ledger.probe("rust", self.root), "1.75.0-0")

    def test_tool_versions_names_its_runtimes_and_a_missing_one_is_unavailable(self):
        self.write(".tool-versions", "nodejs 20.1.0\npython 3.11  # pinned\nterraform 1.5\n")
        self.assertEqual(ledger.pinned_runtimes(self.root, ledger.pin_files(self.root)), {"node", "python"})
        ledger.PROBES = dict(ledger.PROBES, node=[["oldhand-no-such-runtime", "--version"]])
        check, warning = ledger.record(self.d, "AC1", "e2e", "pass", self.evidence(), "lead:x", cmd="c")
        self.assertEqual(check["runtime"]["node"], "unavailable (oldhand-no-such-runtime not found)")
        self.assertIn("could not read the node version", warning)


SECRET = "s3cr3t-VALUE-xyz"
TOKEN, MODE = "OLDHAND_TEST_TOKEN", "OLDHAND_TEST_MODE"


class EnvManifest(Beyond):
    def setUp(self):
        super().setUp()
        self.write(ledger.ENV_NAMES_FILE, "# names only\r\n%s\r\n\r\n%s  # optional\r\n%s\r\n" % (TOKEN, MODE, TOKEN))
        os.environ[TOKEN] = SECRET
        os.environ.pop(MODE, None)

    def tearDown(self):
        for k in (TOKEN, MODE, "OLDHAND_TEST_NEW"):
            os.environ.pop(k, None)
        super().tearDown()

    def test_a_changed_value_makes_checks_stale_and_the_same_value_is_fresh_again(self):
        self.all_pass()
        self.assertEqual(sorted(ledger.load(self.d)["checks"][0]["env"]), [MODE, TOKEN])
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")
        os.environ[TOKEN] = SECRET + "-rotated"
        res = self.verdict()
        self.assertEqual(res["verdict"], "NOT YET")
        self.assertIn("env var %s changed" % TOKEN, self.stale_text(res))
        os.environ[TOKEN] = SECRET
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")

    def test_a_var_that_becomes_set_or_unset_is_a_change(self):
        self.all_pass()
        os.environ[MODE] = "fast"
        self.assertIn("env var %s was set" % MODE, self.stale_text())
        os.environ.pop(MODE)
        os.environ.pop(TOKEN)
        self.assertIn("env var %s was unset" % TOKEN, self.stale_text())

    def test_a_name_added_or_removed_in_the_manifest_is_a_change(self):
        self.all_pass()
        self.write(ledger.ENV_NAMES_FILE, "%s\n%s\nOLDHAND_TEST_NEW\n" % (TOKEN, MODE))
        self.assertIn("env var OLDHAND_TEST_NEW added to .oldhand-env-names", self.stale_text())
        self.all_pass()
        self.write(ledger.ENV_NAMES_FILE, "%s\n" % TOKEN)
        self.assertIn("env var %s removed from .oldhand-env-names" % MODE, self.stale_text())

    def test_a_manifest_saved_with_a_byte_order_mark_reads_the_same(self):
        for enc in ("utf-8-sig", "utf-16"):
            with open(os.path.join(self.root, ledger.ENV_NAMES_FILE), "w", encoding=enc) as fh:
                fh.write("%s\r\n%s\r\n" % (TOKEN, MODE))
            self.assertEqual(ledger.env_names(self.root), [TOKEN, MODE], enc)

    def test_a_value_never_reaches_the_ledger_the_output_or_an_error(self):
        self.all_pass()
        os.environ[TOKEN] = "other-" + SECRET
        with open(os.path.join(self.d, "ledger.json"), encoding="utf-8") as fh:
            raw = fh.read()
        outputs = [raw, json.dumps(self.verdict()), ledger.verdict_text(self.verdict()),
                   ledger.status_text(self.d), ledger.report_md(self.d)]
        for cmd in ("verdict", "status", "report"):
            outputs += list(cli("oldhand", "ledger", cmd, "--dir", self.d)[1:])
        import hashlib
        plain = hashlib.sha256(SECRET.encode()).hexdigest()[:16]
        for text in outputs:
            self.assertNotIn(SECRET, text)
            self.assertNotIn(plain, text)
        self.write(ledger.ENV_NAMES_FILE, "%s=%s\n" % (TOKEN, SECRET))
        with self.assertRaises(ledger.LedgerError) as e:
            ledger.evaluate(self.d)
        self.assertIn("line 1", str(e.exception))
        self.assertNotIn(SECRET, str(e.exception))
        code, out, err = cli("oldhand", "ledger", "record", "--id", "AC1", "--kind", "e2e", "--status", "pass",
                             "--evidence", "seen", "--by", "x", "--cmd", "c", "--dir", self.d)
        self.assertEqual(code, 4)
        self.assertNotIn(SECRET, out + err)


class LiveExpiry(Beyond):
    def live(self, cid="AC1", max_age=None, lead=True):
        return ledger.record(self.d, cid, "e2e", "pass", self.evidence(), "lead:x", cmd=cid + " live",
                             lead=lead, live=True, max_age=max_age)[0]

    def age(self, check_id, hours):
        led = ledger.load(self.d)
        for ch in led["checks"]:
            if ch["id"] == check_id:
                t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
                ch["time"] = t.isoformat(timespec="seconds")
        ledger.save(self.d, led)

    def test_a_live_check_expires_after_24h_and_a_plain_check_never_does(self):
        live = self.live()
        self.assertEqual(live["live"], {"max_age": 86400})
        self.rec("AC2", "integration")
        self.rec("R1")
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")
        self.age("C2", 24 * 30)
        self.age("C3", 24 * 30)
        self.age(live["id"], 23)
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")
        self.age(live["id"], 25)
        res = self.verdict()
        self.assertEqual(res["verdict"], "NOT YET")
        self.assertIn("live check expired (recorded 25h ago, max 24h)", self.stale_text(res))
        self.assertEqual(self.row(res, "R1")["flags"], [])

    def test_max_age_is_per_check(self):
        live = self.live(max_age="48h")
        self.rec("AC2", "integration")
        self.rec("R1")
        self.age(live["id"], 25)
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")
        self.age(live["id"], 49)
        self.assertIn("max 2d", self.stale_text())
        self.assertIn("(live 2d)", ledger.status_text(self.d))

    def test_bad_max_age_and_max_age_without_live_are_errors(self):
        for bad in ("0", "abc", "1w", "-5h", ""):
            with self.assertRaises(ledger.LedgerError):
                ledger.parse_duration(bad)
        self.assertEqual([ledger.parse_duration(s) for s in ("90m", "24H", "7d", "45", "30s")],
                         [5400, 86400, 604800, 45, 30])
        with self.assertRaises(ledger.LedgerError):
            ledger.record(self.d, "AC1", "e2e", "pass", "seen", "x", cmd="c", max_age="1h")
        code, _, err = cli("oldhand", "ledger", "record", "--id", "AC1", "--kind", "e2e", "--status", "pass",
                           "--evidence", "seen", "--by", "x", "--cmd", "c", "--max-age", "1h", "--dir", self.d)
        self.assertEqual(code, 4)
        self.assertIn("--live", err)
        code, out, err = cli("oldhand", "ledger", "record", "--id", "AC1", "--kind", "e2e", "--status", "pass",
                             "--evidence", "seen", "--by", "x", "--cmd", "c", "--live", "--max-age", "90m",
                             "--dir", self.d)
        self.assertEqual(code, 0, err)
        self.assertIn("live for 90m", out)


    def test_a_live_check_dated_in_the_future_is_stale(self):
        self.all_pass()
        ledger.record(self.d, "R1", "e2e", "pass", self.evidence(), "qa:worker", cmd="R1 e2e", live=True)
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")
        led = ledger.load(self.d)
        ahead = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
        led["checks"][-1]["time"] = ahead.isoformat(timespec="seconds")
        ledger.save(self.d, led)
        self.assertIn("live check is dated in the future", self.stale_text())
        led["checks"][-1]["time"] = (ahead - datetime.timedelta(days=30, seconds=-30)).isoformat(timespec="seconds")
        ledger.save(self.d, led)
        self.assertEqual(self.verdict()["verdict"], "VERIFIED", "half a minute of clock difference is not the future")


class Where(unittest.TestCase):
    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_where_picks_the_newest_ledger(self):
        a = os.path.join(self.root, ".oldhand", "a")
        b = os.path.join(self.root, ".oldhand", "b")
        ledger.init(a, "A")
        ledger.init(b, "B")
        os.utime(os.path.join(a, "ledger.json"), (2000000000, 2000000000))
        os.utime(os.path.join(b, "ledger.json"), (1000000000, 1000000000))
        self.assertEqual(ledger.where(self.root), a)
        code, out, _ = cli("oldhand", "ledger", "where", cwd=self.root)
        self.assertEqual((code, out.strip()), (0, a))

    def test_a_session_in_a_sub_folder_finds_the_same_task(self):
        git_repo(self.root)
        pkg = os.path.join(self.root, "pkg", "api")
        os.makedirs(pkg)
        code, out, err = cli("oldhand", "ledger", "init", "--dir", ".oldhand/t1", "--title", "T1", cwd=pkg)
        self.assertEqual(code, 0, err)
        task = os.path.join(self.root, ".oldhand", "t1")
        self.assertTrue(os.path.isfile(os.path.join(task, "ledger.json")), out)
        self.assertIn(task, out)
        for args in (["where"], ["where", "--dir", ".oldhand/t1"], ["where", "--root", self.root]):
            code, out, err = cli("oldhand", "ledger", *args, cwd=pkg)
            self.assertEqual((code, out.strip()), (0, task), err)
        older = os.path.join(pkg, ".oldhand", "old")  # made in the package folder before this fix
        ledger.init(older, "Old")
        os.utime(os.path.join(task, "ledger.json"), (1000000000, 1000000000))
        self.assertEqual(ledger.where(pkg), older)

    def test_parallel_writers_lose_nothing(self):
        d = os.path.join(self.root, ".oldhand", "p")
        ledger.init(d, "P")
        args = [sys.executable, script("oldhand", "ledger"), "finding", "add", "--dir", d, "--sev", "high",
                "--lens", "x", "--where", "a.py:1", "--text", "t"]
        procs = [subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(6)]
        codes = [p.wait() for p in procs]
        for p in procs:
            p.stdout.close()
            p.stderr.close()
        self.assertEqual(codes, [0] * 6)
        self.assertEqual(sorted(f["id"] for f in ledger.load(d)["findings"]), ["F%d" % i for i in range(1, 7)])

    def test_where_without_tasks_is_an_error_with_a_hint(self):
        with self.assertRaises(ledger.LedgerError) as e:
            ledger.where(self.root)
        self.assertIn("ledger.py init", str(e.exception))
        code, _, err = cli("oldhand", "ledger", "where", cwd=self.root)
        self.assertEqual(code, 4)
        self.assertIn("init", err)


class CommandLine(Base):
    def run_cli(self, *args):
        return cli("oldhand", "ledger", *(list(args) + ["--dir", self.d]))

    def test_exit_codes_json_report_and_status(self):
        code, out, _ = self.run_cli("verdict")
        self.assertEqual(code, 3)
        self.assertTrue(out.startswith("VERDICT: INCOMPLETE"))
        self.evidence()
        for cid, kind, extra in (("AC1", "e2e", ["--lead"]), ("AC2", "integration", []), ("R1", "e2e", [])):
            code, out, err = self.run_cli("record", "--id", cid, "--kind", kind, "--status", "pass",
                                          "--evidence", "ev.txt", "--by", "lead:fable", "--cmd", cid, *extra)
            self.assertEqual(code, 0, err)
        code, out, _ = self.run_cli("verdict", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["verdict"], "VERIFIED")
        code, out, _ = self.run_cli("finding", "add", "--sev", "high", "--lens", "security", "--where", "x.py:1",
                                    "--text", "bad")
        self.assertEqual(code, 0)
        code, out, _ = self.run_cli("verdict")
        self.assertEqual(code, 1)
        self.assertIn("F1 (high, security) is open", out)
        code, out, _ = self.run_cli("report")
        self.assertEqual(code, 0)
        self.assertIn("### Verdict: NOT YET", out)
        self.assertIn("| AC1 |", out)
        code, out, _ = self.run_cli("status")
        self.assertEqual(code, 0)
        self.assertIn("C3", out)

    def test_any_text_prints_on_a_narrow_code_page(self):
        self.contract("Mode: implement\n- AC1: x → y ✓ 漢\n")
        ledger.sync(self.d)
        env = dict(os.environ, PYTHONIOENCODING="cp1252")  # what a Windows pipe gives Python 3.14 and older
        for cmd in ("status", "report", "verdict"):
            code, out, err = cli("oldhand", "ledger", cmd, "--dir", self.d, env=env)
            self.assertNotIn("Traceback", err)
            self.assertIn(code, (0, 3), err)

    def test_errors_exit_4_and_say_what_to_do(self):
        code, _, err = self.run_cli("record", "--id", "AC7", "--kind", "e2e", "--status", "pass",
                                    "--evidence", "x", "--by", "qa:scout", "--cmd", "x")
        self.assertEqual(code, 4)
        self.assertIn("ledger.py sync", err)
        code, _, err = self.run_cli("record", "--id", "AC1", "--kind", "smoke", "--status", "pass",
                                    "--evidence", "x", "--by", "qa:scout", "--cmd", "x")
        self.assertEqual(code, 4)
        code, _, err = cli("oldhand", "ledger", "sync", "--dir", os.path.join(self.root, "nowhere"))
        self.assertEqual(code, 4)
        self.assertIn("ledger.py init", err)


def git_out(cwd, *args):
    return subprocess.run(["git"] + list(args), cwd=cwd, env=dict(os.environ, **GIT_ENV), check=True,
                          stdout=subprocess.PIPE, universal_newlines=True).stdout.strip()


class ContentTree(Beyond):
    """The fingerprint names the files on disk, not the commit they sit on."""

    def edit(self, name="a.txt", text="two\n"):
        with open(os.path.join(self.root, name), "a") as fh:
            fh.write(text)

    def commit(self, *args):
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", *(args or ("-m", "change")))

    def test_the_fingerprint_is_the_commits_tree_id_and_the_verdict_says_so(self):
        head = git_out(self.root, "rev-parse", "HEAD")
        self.assertEqual(ledger.fingerprint(self.d),
                         "tree:%s:%s" % (git_out(self.root, "rev-parse", "HEAD^{tree}"), ledger.NO_EXTRAS))
        res = self.verdict()
        self.assertEqual((res["head"], res["committed"]), (head, True))
        self.assertIn("the files of commit " + head[:10], ledger.verdict_text(res))
        self.edit()
        dirty = ledger.fingerprint(self.d)
        res = self.verdict()
        self.assertFalse(res["committed"])
        self.assertIn("commit %s plus uncommitted changes" % head[:10], ledger.verdict_text(res))
        self.commit()
        self.assertEqual(ledger.fingerprint(self.d), dirty, "committing the files does not change what they are")
        self.assertEqual(dirty.split(":")[1], git_out(self.root, "rev-parse", "HEAD^{tree}"))
        self.assertTrue(self.verdict()["committed"])

    def test_a_commit_an_amend_or_another_branch_with_the_same_files_keeps_checks_fresh(self):
        self.edit()
        self.write("new.py", "x = 1\n")
        self.all_pass()
        for step in (lambda: self.commit(), lambda: git(self.root, "commit", "-q", "--amend", "-m", "reworded"),
                     lambda: git(self.root, "commit", "-q", "--allow-empty", "-m", "empty"),
                     lambda: git(self.root, "checkout", "-q", "-b", "other")):
            step()
            self.assertEqual(self.verdict()["verdict"], "VERIFIED")
        self.edit()
        self.assertEqual(self.verdict()["verdict"], "NOT YET")

    def test_git_diff_settings_do_not_change_the_fingerprint(self):
        self.edit()
        fp = ledger.fingerprint(self.d)
        for key, value in (("diff.noprefix", "true"), ("diff.external", "true"), ("diff.algorithm", "histogram"),
                           ("core.quotepath", "false")):
            git(self.root, "config", key, value)
            self.assertEqual(ledger.fingerprint(self.d), fp, key)

    def test_strict_line_ending_settings_do_not_break_the_fingerprint(self):
        git(self.root, "config", "core.autocrlf", "true")
        git(self.root, "config", "core.safecrlf", "true")
        self.all_pass()
        self.edit(text="unix line\n")  # with safecrlf, `git add` itself refuses this file
        self.assertIn("; changed: a.txt)", self.stale_text())

    def test_the_stale_reason_names_the_files_that_changed(self):
        self.all_pass()
        self.edit()
        self.write("new.py", "x = 1\n")
        self.assertIn("; changed: a.txt, new.py)", self.stale_text())
        self.all_pass()
        self.commit()  # the tree the checks ran on is now a commit: only what differs from it is named
        self.write("b.txt", "b\n")
        self.assertIn("; changed: b.txt)", self.stale_text())
        self.all_pass()
        os.remove(os.path.join(self.root, "a.txt"))
        for n in range(7):
            self.write("f%d.txt" % n, "f\n")
        self.assertIn("; changed: a.txt, f0.txt, f1.txt, f2.txt, f3.txt and 3 more)", self.stale_text())
        self.all_pass()
        self.commit()  # a.txt was already gone when the checks ran: committing that is no change
        self.write("z.txt", "z\n")
        self.assertIn("; changed: z.txt)", self.stale_text())

    def test_a_reason_without_names_when_too_many_paths_differ_or_the_commit_is_gone(self):
        info = ledger.tree_info(self.d)[1]
        self.assertEqual(ledger.changed_files(self.root, info, dict(info, delta={"x": "100644 abc"})), ["x"])
        self.assertIsNone(ledger.changed_files(self.root, None, info))
        self.assertIsNone(ledger.changed_files(self.root, dict(info, delta=None), info))
        self.assertIsNone(ledger.changed_files(self.root, dict(info, head="0" * 40), info), "that commit is gone")
        ledger.TREE_DELTA_MAX, kept = 2, ledger.TREE_DELTA_MAX
        try:
            for n in range(3):
                self.write("f%d.txt" % n, "f\n")
            self.all_pass()
            self.assertIsNone(ledger.load(self.d)["trees"][ledger.fingerprint(self.d)]["delta"])
            self.edit()
            self.assertIn("recorded on an older tree", self.stale_text())
            self.assertNotIn("changed:", self.stale_text())
        finally:
            ledger.TREE_DELTA_MAX = kept

    def test_only_the_trees_checks_still_use_are_kept(self):
        self.all_pass()
        first = ledger.fingerprint(self.d)
        self.edit()
        self.all_pass()
        self.assertEqual(set(ledger.load(self.d)["trees"]), {first, ledger.fingerprint(self.d)})

    def test_a_file_edited_while_marked_assume_unchanged_or_skip_worktree_counts(self):
        self.write("b.txt", "b\n")
        self.commit()
        for mark in ("assume-unchanged", "skip-worktree"):
            self.all_pass()
            git(self.root, "update-index", "--" + mark, "b.txt")
            self.assertEqual(self.verdict()["verdict"], "VERIFIED", "the mark alone changes no file")
            self.edit("b.txt", mark + "\n")
            self.assertEqual(git_out(self.root, "status", "--porcelain"), "", "git itself does not show the edit")
            self.assertIn("; changed: b.txt)", self.stale_text())
            git(self.root, "update-index", "--no-" + mark, "b.txt")
        git(self.root, "update-index", "--assume-unchanged", "a.txt")
        self.all_pass()
        os.remove(os.path.join(self.root, "a.txt"))
        self.assertIn("a.txt", self.stale_text())

    def test_a_fingerprint_writes_nothing_into_the_repository(self):
        def snapshot():
            out = {}
            for folder, _, files in os.walk(os.path.join(self.root, ".git")):
                for name in files:
                    with open(os.path.join(folder, name), "rb") as fh:
                        out[os.path.join(folder, name)] = fh.read()
            return out
        if os.name == "posix":  # a hook the repo has for index writes must not fire for the copy
            hook = os.path.join(self.root, ".git", "hooks", "post-index-change")
            with open(hook, "w") as fh:
                fh.write("#!/bin/sh\ntouch '%s'\n" % os.path.join(self.root, ".git", "hook-ran"))
            os.chmod(hook, 0o755)
        for split in (False, True):
            if split:  # a split index keeps its shared part in .git
                git(self.root, "config", "core.splitIndex", "true")
                git(self.root, "update-index", "--split-index")
                if os.path.exists(os.path.join(self.root, ".git", "hook-ran")):
                    os.remove(os.path.join(self.root, ".git", "hook-ran"))  # that was our own update-index
            self.edit()
            self.write("new%s.py" % split, "x = 1\n")
            before = snapshot()
            self.all_pass()
            self.assertEqual(self.verdict()["verdict"], "VERIFIED")
            self.assertEqual(sorted(snapshot()), sorted(before), "split index: %s" % split)
            self.assertEqual(snapshot(), before)
        self.assertEqual([n for n in os.listdir(tempfile.gettempdir()) if n.startswith("oldhand-tree-")], [])

    def test_an_edit_in_the_same_second_that_keeps_the_size_is_seen(self):
        # git re-reads a file that is not older than its index; the copy of the index must keep that time.
        for attempt in range(20):
            self.write("r.txt", "aaaa\n")
            git(self.root, "add", "r.txt")
            fp = ledger.fingerprint(self.d)
            self.write("r.txt", "bbbb\n")
            index, edited = (os.stat(os.path.join(self.root, x)) for x in (os.path.join(".git", "index"), "r.txt"))
            if int(index.st_mtime) == int(edited.st_mtime):  # the case that matters: same second, same size
                time.sleep(1.1)  # and looked at later, when a fresh copy of the index would be newer than the file
                self.assertNotEqual(ledger.fingerprint(self.d), fp)
                return
        self.fail("could not write within one second in 20 tries")

    @unittest.skipIf(os.name != "posix", "a colon, a quote or a line break in a folder name")
    def test_a_repo_path_with_a_colon_a_quote_or_a_line_break(self):
        for name in ("odd:name here", 'with "quotes" \\ and\na line break', '"quoted"'):
            root = os.path.join(self.root, name)
            os.makedirs(root)
            git_repo(root)
            d = os.path.join(root, ".oldhand", "t")
            ledger.init(d, "Odd")
            self.assertEqual(ledger.fingerprint(d).split(":")[1], git_out(root, "rev-parse", "HEAD^{tree}"), name)

    def test_big_files_and_a_nested_repo_without_a_commit_still_count(self):
        with open(os.path.join(self.root, "big.bin"), "wb") as fh:
            fh.truncate(ledger.BIG + 1)
        fp, info = ledger.tree_info(self.d)
        self.assertEqual(info["extras"], {"big.bin": "size:%d" % (ledger.BIG + 1)})
        self.assertNotIn("big.bin", info["delta"], "a big file is not copied into the temporary object folder")
        with open(os.path.join(self.root, "big.bin"), "wb") as fh:
            fh.truncate(ledger.BIG + 2)
        self.assertNotEqual(ledger.fingerprint(self.d), fp)
        nested = os.path.join(self.root, "vendor", "new")
        os.makedirs(nested)
        git(nested, "init", "-q")
        fp = ledger.fingerprint(self.d)  # git add fails on a repo with no commit; it is fingerprinted on its own
        with open(os.path.join(nested, "x.txt"), "w") as fh:
            fh.write("x\n")
        self.all_pass()
        self.assertNotEqual(ledger.fingerprint(self.d), fp)
        with open(os.path.join(nested, "x.txt"), "a") as fh:
            fh.write("more\n")
        self.assertIn("; changed: vendor/new/)", self.stale_text())

    @unittest.skipIf(os.name != "posix" or os.geteuid() == 0, "needs a file the user cannot read")
    def test_an_unreadable_untracked_file_is_counted_by_name(self):
        fp = ledger.fingerprint(self.d)
        self.write("locked.txt", "x\n")
        os.chmod(os.path.join(self.root, "locked.txt"), 0)
        self.assertEqual(ledger.tree_info(self.d)[1]["extras"], {"locked.txt": "unreadable"})
        self.assertNotEqual(ledger.fingerprint(self.d), fp)

    def test_a_repo_with_no_commit_yet(self):
        root = os.path.join(self.root, "fresh")
        os.makedirs(root)
        git(root, "init", "-q")
        with open(os.path.join(root, "a.txt"), "w") as fh:
            fh.write("one\n")
        d = os.path.join(root, ".oldhand", "t")
        ledger.init(d, "Fresh")
        with open(os.path.join(d, "contract.md"), "w") as fh:
            fh.write("Mode: implement\n- AC1: it works (proof: e2e)\n")
        ledger.sync(d)
        with open(os.path.join(d, "ev.txt"), "w") as fh:
            fh.write("saw it\n")
        ledger.record(d, "AC1", "e2e", "pass", "ev.txt", "lead:x", cmd="c", lead=True)
        res = ledger.evaluate(d)
        self.assertEqual((res["verdict"], res["head"], res["committed"]), ("VERIFIED", None, False))
        self.assertIn("no commit yet", ledger.verdict_text(res))
        for args in (("config", "user.name", "T"), ("config", "user.email", "t@example.test"), ("add", "-A"),
                     ("commit", "-qm", "first")):
            git(root, *args)
        res = ledger.evaluate(d)
        self.assertEqual((res["verdict"], res["committed"]), ("VERIFIED", True))
        with open(os.path.join(root, "a.txt"), "a") as fh:
            fh.write("two\n")
        self.assertIn("; changed: a.txt)", "\n".join(ledger.evaluate(d)["reasons"]))

    def test_a_check_recorded_by_2_1_is_judged_by_its_old_fingerprint(self):
        self.all_pass()
        led = ledger.load(self.d)
        old = ledger._legacy_tree_state(self.root)
        self.assertTrue(ledger.legacy(old) and not ledger.legacy(led["checks"][0]["fingerprint"]))
        for ch in led["checks"]:
            ch["fingerprint"] = old
            del ch["evidence_hash"]
        del led["trees"]
        ledger.save(self.d, led)
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")
        self.assertIsNone(ledger.restamp(self.d, "C1", "nothing changed"))
        git(self.root, "commit", "-q", "--allow-empty", "-m", "empty")
        self.assertEqual(self.verdict()["verdict"], "NOT YET", "the old fingerprint holds the commit id")
        git(self.root, "reset", "-q", "--soft", "HEAD~1")
        self.edit()
        now = ledger._legacy_tree_state(self.root)
        self.assertIn("C1 was recorded on an older tree (%s, now %s): re-run" % (ledger.short_fp(old), ledger.short_fp(now)),
                      self.stale_text())
        led = ledger.load(self.d)  # a restamp 2.1 wrote carries an old-style fingerprint too
        led["restamps"] = [{"check": ch["id"], "reason": "a fixture", "from": old, "fingerprint": now,
                            "time": ledger.now()} for ch in led["checks"]]
        ledger.save(self.d, led)
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")
        self.edit()
        self.assertEqual(self.verdict()["verdict"], "NOT YET")
        for ch in led["checks"]:
            self.assertIsNotNone(ledger.restamp(self.d, ch["id"], "a.txt is a fixture"))
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")


class Evidence(Base):
    """A record remembers what its evidence file held."""

    def overwrite(self, text, name="ev.txt"):
        with open(os.path.join(self.d, name), "w") as fh:
            fh.write(text)

    def test_evidence_that_changed_after_the_record_does_not_count(self):
        self.all_pass()
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")
        for text in ("FAILED\n", ""):
            self.overwrite(text)
            res = self.verdict()
            self.assertEqual(res["verdict"], "INCOMPLETE")
            self.assertIn("evidence changed", self.row(res, "AC1")["flags"])
            self.assertIn("AC1: the evidence of C1 (ev.txt) changed after the check was recorded", "\n".join(res["reasons"]))
            self.assertTrue(any("--lead" in r for r in res["reasons"]), "the lead's pass does not count either")
        self.overwrite("saw it\n")
        self.assertEqual(self.verdict()["verdict"], "VERIFIED", "the same content again is the same evidence")

    def test_evidence_that_was_empty_when_recorded_does_not_count(self):
        self.all_pass()
        self.overwrite("", "blank.txt")
        check, warning = ledger.record(self.d, "R1", "e2e", "pass", "blank.txt", "qa:worker", cmd="blank")
        self.assertEqual(check["evidence_hash"], "empty")
        self.assertIn("empty file", warning)
        res = self.verdict()
        self.assertEqual(res["verdict"], "INCOMPLETE")
        self.assertIn("R1: the evidence of C4 (blank.txt) was an empty file when the check was recorded", "\n".join(res["reasons"]))
        self.overwrite("now it has text\n", "blank.txt")
        self.assertEqual(self.verdict()["verdict"], "INCOMPLETE", "filling it in later proves nothing about the run")

    def test_a_check_without_a_stored_hash_is_only_asked_to_exist(self):
        self.all_pass()
        led = ledger.load(self.d)
        for ch in led["checks"]:
            del ch["evidence_hash"]  # as 2.1 recorded it
        ledger.save(self.d, led)
        self.overwrite("something else\n")
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")

    def test_what_is_hashed(self):
        os.makedirs(os.path.join(self.d, "shots"))
        with open(os.path.join(self.d, "big.log"), "wb") as fh:
            fh.truncate(ledger.BIG + 1)
        log = self.evidence(os.path.join("shots", "console.log"))
        for ev, want in (("pytest -q: 12 passed", None), ("https://example.test/run/3", None), ("shots/", None),
                         ("big.log", "size:%d" % (ledger.BIG + 1)),
                         (log + ":3", ledger.evidence_hash(os.path.join(self.d, log)))):
            self.assertEqual(self.rec("AC1", ev=ev, cmd=ev).get("evidence_hash"), want, ev)
        self.assertEqual(len(want), 16)


PY = sys.executable


class Run(Beyond):
    """`run` executes the command itself: the exit code is the status and the output is the evidence."""

    def setUp(self):
        super().setUp()
        self.cwd = os.getcwd()
        os.chdir(self.root)

    def tearDown(self):
        os.chdir(self.cwd)
        super().tearDown()

    def py(self, cid, code, kind="e2e", **kw):
        return ledger.run(self.d, cid, kind, "lead:x", [PY, "-c", code], **kw)

    def saved(self, check):
        with open(os.path.join(self.d, check["evidence"]), encoding="utf-8") as fh:
            return fh.read()

    def test_the_exit_code_decides_and_the_output_is_the_evidence(self):
        check, warning, tail = self.py("AC1", "print('guest signed up')", lead=True)
        self.assertEqual((check["status"], check["run"]["exit"], check["lead"], warning), ("pass", 0, True, None))
        self.assertTrue(check["evidence"].startswith("runs/") and len(check["evidence_hash"]) == 16)
        self.assertIn("guest signed up", self.saved(check))
        self.assertIn("exit 0: pass", self.saved(check))
        self.assertEqual(tail, ["guest signed up"])
        flaky = "import os, sys; print('boom'); sys.exit(0 if os.path.exists('.oldhand/fixed') else 3)"
        check, _, tail = self.py("AC2", flaky, "integration")
        self.assertEqual((check["status"], check["run"]["exit"], check["run"]["result"]), ("fail", 3, "exit 3"))
        self.assertIn("exit 3: fail", self.saved(check))
        self.py("R1", "print('members sign in')")
        self.assertEqual(self.verdict()["verdict"], "NOT YET")
        open(os.path.join(".oldhand", "fixed"), "w").close()
        self.assertEqual(self.py("AC2", flaky, "integration")[0]["status"], "pass")
        self.assertEqual(self.verdict()["verdict"], "VERIFIED", "a new run of the same command replaces the old one")
        self.assertFalse([n for n in os.listdir(os.path.join(self.d, "runs")) if n.endswith(".tmp")])

    def test_a_command_that_cannot_start_records_nothing(self):
        with self.assertRaises(ledger.LedgerError) as e:
            ledger.run(self.d, "AC1", "e2e", "lead:x", ["oldhand-no-such-command", "--flag"])
        self.assertIn("could not start", str(e.exception))
        self.assertEqual(ledger.load(self.d)["checks"], [])
        self.assertFalse(os.path.exists(os.path.join(self.d, "runs")))

    def test_exit_0_with_no_tests_ran_is_a_fail(self):
        for said in ("Ran 0 tests in 0.000s", "no tests ran in 0.01s"):
            check, _, _ = self.py("AC2", "print(%r)" % said, "unit")
            self.assertEqual((check["status"], check["run"]["result"]),
                             ("fail", "exit 0, but the output says no tests ran"))
        self.assertEqual(self.py("AC2", "print('Ran 10 tests in 0.2s')", "unit")[0]["status"], "pass")

    def test_a_timeout_is_a_fail_and_the_command_is_ended(self):
        code = "import time; open('started', 'w').close(); time.sleep(20); open('finished', 'w').close()"
        started = datetime.datetime.now()
        check, _, _ = self.py("AC1", code, timeout=1)
        self.assertEqual((check["status"], check["run"]["exit"], check["run"]["result"]), ("fail", None, "timed out after 1s"))
        self.assertLess((datetime.datetime.now() - started).total_seconds(), 15)
        self.assertTrue(os.path.exists("started") and not os.path.exists("finished"))

    def test_a_run_from_a_sub_folder_is_stored_from_the_root(self):
        os.makedirs("pkg/api")
        os.chdir("pkg/api")
        check, _, tail = self.py("AC1", "import os; print(os.path.basename(os.getcwd()))")
        self.assertEqual(tail, ["api"])
        self.assertTrue(check["cmd"].startswith("cd ./pkg/api && "), check["cmd"])
        os.chdir(self.root)
        self.assertEqual(ledger.rerun(self.d, check=check["id"])[0][0][3], ["api"])
        one = ledger.run(self.d, "AC1", "e2e", "lead:x", ["echo one && echo two"])
        self.assertEqual((one[0]["cmd"], one[2]), ("echo one && echo two", ["one", "two"]))

    def test_bad_input_stops_before_the_command_runs(self):
        code = "open('ran', 'w').close()"
        for cid, kind, kw in (("AC1", "review", {}), ("AC9", "e2e", {}), ("AC1", "e2e", {"max_age": "1h"}),
                              ("AC1", "e2e", {"live": True, "max_age": "soon"}), ("AC1", "e2e", {"timeout": 0})):
            with self.assertRaises(ledger.LedgerError):
                self.py(cid, code, kind, **kw)
        for argv in ([], ["--"], ["--", " "]):
            with self.assertRaises(ledger.LedgerError):
                ledger.run(self.d, "AC1", "e2e", "lead:x", argv)
        self.write(".oldhand-env-names", "TOKEN=%s\n" % SECRET)
        with self.assertRaises(ledger.LedgerError):
            self.py("AC1", code)
        self.assertFalse(os.path.exists("ran"))
        self.assertEqual(ledger.load(self.d)["checks"], [])

    def test_listed_env_values_are_kept_out_of_the_saved_output(self):
        self.write(".oldhand-env-names", "%s\n%s\n" % (TOKEN, MODE))
        os.environ[TOKEN], os.environ[MODE] = SECRET, "dev"
        kept, ledger.RUN_KEEP = ledger.RUN_KEEP, 1500000
        try:
            # The value at the start, across the 1 MB boundary the output is read in, and at the end.
            code = ("import os, sys; t = os.environ[%r]; sys.stdout.write(t + '\\n' + 'x' * ((1 << 20) - len(t) - 6) + t "
                    "+ '\\n' + 'y' * 3000000 + '\\nmode ' + os.environ[%r] + ' ' + t + '\\n')" % (TOKEN, MODE))
            check, _, tail = self.py("AC1", code)
        finally:
            ledger.RUN_KEEP = kept
            del os.environ[TOKEN], os.environ[MODE]
        text = self.saved(check)
        self.assertEqual(text.count("<%s>" % TOKEN), 3)
        self.assertIn("mode dev <%s>" % TOKEN, text, "a short value is not treated as a secret")
        self.assertIn("bytes left out", text)
        self.assertLess(len(text), 3001000)
        for folder, _, files in os.walk(os.path.join(self.root, ".oldhand")):
            for name in files:
                with open(os.path.join(folder, name), "rb") as fh:
                    self.assertNotIn(SECRET.encode(), fh.read(), name)
        self.assertNotIn(SECRET, "\n".join(tail) + ledger.status_text(self.d) + ledger.report_md(self.d))

    def test_rerun_stale_runs_the_stale_checks_again_and_lists_the_rest(self):
        self.py("AC1", "print(open('a.txt').read())", lead=True)
        self.py("AC2", "print('api up')", "integration", live=True, max_age="2h")
        self.rec("R1")  # recorded by hand: there is no command to run again
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")
        self.assertEqual(ledger.rerun(self.d, stale=True), ([], []))
        with open("a.txt", "a") as fh:
            fh.write("a second line\n")
        self.assertEqual(self.verdict()["stale"], ["C1", "C2", "C3"])
        done, left = ledger.rerun(self.d, stale=True)
        self.assertEqual([(old["id"], new["id"], new["status"]) for old, new, _, _ in done],
                         [("C1", "C4", "pass"), ("C2", "C5", "pass")])
        self.assertEqual([(ch["id"], why[:10]) for ch, why in left], [("C3", "no command")])
        first, second = done[0][1], done[1][1]
        self.assertEqual((first["criterion"], first["kind"], first["lead"], first["by"]), ("AC1", "e2e", True, "lead:x"))
        self.assertEqual((second["kind"], second["live"]), ("integration", {"max_age": 7200}))
        self.assertIn("a second line", self.saved(first))
        res = self.verdict()
        self.assertEqual((res["stale"], [r["counted"] for r in res["criteria"]]), (["C3"], [["C4"], ["C5"], ["C3"]]))
        code, out, _ = cli("oldhand", "ledger", "rerun", "--stale", "--dir", self.d, cwd=self.root)
        self.assertEqual((code, "C3  R1 e2e" in out), (1, True), "nothing failed, but a stale check is left")
        self.rec("R1")
        self.assertEqual(self.verdict()["verdict"], "VERIFIED")

    def test_rerun_one_check_and_what_it_refuses(self):
        check, _, _ = self.py("AC2", "import os, sys; sys.exit(0 if os.path.exists('fixed') else 1)", "unit")
        self.assertEqual(check["status"], "fail")
        open("fixed", "w").close()
        done, left = ledger.rerun(self.d, check="C1", by="lead:y")
        self.assertEqual((done[0][1]["status"], done[0][1]["by"], left), ("pass", "lead:y", []))
        self.rec("R1")
        for kw, said in (({"check": "C3"}, "was not recorded by"), ({"check": "C9"}, "no check C9"), ({}, "--stale")):
            with self.assertRaises(ledger.LedgerError) as e:
                ledger.rerun(self.d, **kw)
            self.assertIn(said, str(e.exception))

    def test_rerun_executes_only_commands_this_user_recorded_here(self):
        check, _, _ = self.py("AC1", "open('ran-again', 'w').close()")
        self.assertEqual(len(check["run"]["signed"]), 64)
        os.remove("ran-again")
        good = ledger.load(self.d)

        def refused(change, said="not recorded by this user in this project on this machine"):
            led = json.loads(json.dumps(good))
            change(led["checks"][0])
            ledger.save(self.d, led)
            with self.assertRaises(ledger.LedgerError) as e:
                ledger.rerun(self.d, check="C1")
            self.assertIn(said, str(e.exception))
            done, left = ledger.rerun(self.d, stale=True)
            self.assertEqual((done, [ch["id"] for ch, _ in left]), ([], ["C1"]))
            self.assertFalse(os.path.exists("ran-again"), "the command must not have run")
        with open("a.txt", "a") as fh:
            fh.write("two\n")  # C1 is stale now, so rerun --stale would pick it up
        refused(lambda ch: ch.update(cmd="touch ran-again"))              # another command under an old signature
        refused(lambda ch: ch.update(criterion="AC2"))                    # the same command for another criterion
        refused(lambda ch: ch["run"].pop("signed"))                       # no signature at all
        refused(lambda ch: ch["run"].update(signed=True))                 # not even a string
        refused(lambda ch: ch["run"].update(signed="\u00e9" * 64))         # nor one a signature could be
        other = tempfile.mkdtemp()                                        # a ledger from another machine or user:
        folders, ledger._key_folders = ledger._key_folders, lambda: [os.path.join(other, "oldhand")]
        try:
            refused(lambda ch: None)                                      # there is no key here at all
            ledger._rerun_key(create=True)
            refused(lambda ch: None)                                      # and this machine's key is another one
            ledger._key_folders = lambda: []
            unsigned, warning, _ = self.py("AC1", "print('no place for a key')")
            self.assertNotIn("signed", unsigned["run"])
            self.assertIn("no folder for the rerun key", warning)
        finally:
            ledger._key_folders = folders
        self.addCleanup(shutil.rmtree, other)
        ledger.save(self.d, good)
        elsewhere = os.path.join(self.root, "another-project")  # our own signed check, copied into another project
        os.makedirs(elsewhere)
        git_repo(elsewhere)
        d2 = os.path.join(elsewhere, ".oldhand", "t")
        ledger.init(d2, "Other")
        shutil.copy(os.path.join(self.d, "contract.md"), d2)
        shutil.copy(os.path.join(self.d, "ledger.json"), d2)
        with self.assertRaises(ledger.LedgerError):
            ledger.rerun(d2, check="C1")
        self.assertFalse(os.path.exists(os.path.join(elsewhere, "ran-again")) or os.path.exists("ran-again"))
        shutil.rmtree(elsewhere)
        code, out, _ = cli("oldhand", "ledger", "rerun", "--stale", "--dir", self.d, cwd=self.root,
                           env=dict(os.environ, XDG_STATE_HOME=other, TMPDIR=other))
        self.assertEqual(code, 1)
        self.assertIn("not shown; run it only if the user asks for it", out)
        self.assertNotIn("ran-again", out, "a command that was not recorded here is not printed for anyone to copy")
        git(self.root, "add", "-f", os.path.join(".oldhand", "t", "ledger.json"))  # our own ledger, tracked or not
        self.assertEqual(ledger.rerun(self.d, stale=True)[0][0][1]["status"], "pass")
        self.assertTrue(os.path.exists("ran-again"))

    @unittest.skipIf(os.name != "posix", "file modes")
    def test_the_rerun_key_is_private_and_a_key_others_could_replace_is_not_used(self):
        folder = ledger._key_folders()[0]
        key = ledger._rerun_key(create=True)
        self.assertEqual((len(key), ledger._rerun_key()), (32, key))
        self.assertEqual(os.stat(os.path.join(folder, "rerun-key")).st_mode & 0o777, 0o600)
        for target, mode in ((folder, 0o777), (os.path.join(folder, "rerun-key"), 0o666),
                             (os.path.join(folder, "rerun-key"), 0o644)):
            kept = os.stat(target).st_mode & 0o777
            os.chmod(target, mode)
            try:
                self.assertIsNone(ledger._rerun_key(), "%s is writable by others" % target)
            finally:
                os.chmod(target, kept)
        self.assertEqual(ledger._rerun_key(), key)
        self.assertEqual(os.listdir(folder), ["rerun-key"], "the key is written whole, with nothing left beside it")
        state, os.environ["XDG_STATE_HOME"] = os.environ["XDG_STATE_HOME"], "relative/state"
        try:  # a relative state folder would land inside the project: only the temp folder is left
            self.assertEqual(len(_saved_env["folders"]()), 1)
        finally:
            os.environ["XDG_STATE_HOME"] = state

    def test_a_listed_value_in_the_command_line_is_refused(self):
        self.write(".oldhand-env-names", TOKEN + "\n")
        os.environ[TOKEN] = SECRET
        try:
            with self.assertRaises(ledger.LedgerError) as e:
                ledger.run(self.d, "AC1", "e2e", "lead:x", ["echo %s > ran" % SECRET])
            self.assertIn("holds the value of " + TOKEN, str(e.exception))
            self.assertNotIn(SECRET, str(e.exception))
            self.assertFalse(os.path.exists("ran"))
            self.assertEqual(ledger.load(self.d)["checks"], [])
            check, _, _ = self.py("AC1", "import os; print('token is', os.environ[%r])" % TOKEN)
        finally:
            del os.environ[TOKEN]
        self.assertIn("token is <%s>" % TOKEN, self.saved(check))

    def test_no_part_of_a_value_is_left_where_long_output_is_cut(self):
        import io
        long, short = b"AAAA-SECRET-ONE-and-its-longer-TAIL", b"AAAA-SECRET-ONE"  # one listed value inside another
        hidden = [("LONG", long), ("SHORT", short)]
        kept, ledger.RUN_KEEP = ledger.RUN_KEEP, 1000
        try:
            for shift in range(-len(long) - 2, len(long) + 3):  # the value slides across both cuts
                for cut in (1000, 9000):
                    data = bytearray(b"x" * 10000)
                    at = cut + shift
                    data[at:at + len(long)] = long
                    out = ledger._output(io.BytesIO(bytes(data)), hidden)
                    for piece in (b"SECRET", b"TAIL", b"longer", b"AAAA"):
                        self.assertNotIn(piece, out, (shift, cut))
            self.assertEqual(ledger._output(io.BytesIO(short + b" and " + long), hidden), b"<SHORT> and <LONG>")
            # Values that overlap each other: every stretch any of them covers goes.
            self.assertEqual(ledger._output(io.BytesIO(b"dceeadgdggfdceeadgdggf."),
                                            [("N0", b"dceeadgdggfdc"), ("N1", b"dceeadgdggf")]), b"<N0>.")
            self.assertEqual(ledger._output(io.BytesIO(b"abcXYZdef abcXYZ"), [("A", b"abcXYZ"), ("B", b"XYZdef")]), b"<A> <A>")
            self.assertEqual(ledger._output(io.BytesIO(b"plain"), []), b"plain")
        finally:
            ledger.RUN_KEEP = kept

    def test_a_file_changed_while_the_command_ran_leaves_the_check_stale(self):
        check, warning, _ = self.py("AC1", "open('a.txt', 'a').write('edited during the run\\n')", lead=True)
        self.assertEqual(check["status"], "pass")
        self.assertIn("files changed while the command ran: a.txt", warning)
        res = self.verdict()
        self.assertEqual(res["stale"], ["C1"])
        self.assertIn("; changed: a.txt)", self.stale_text(res))
        check, warning, _ = self.py("AC1", "open('.oldhand/scratch', 'w').close()", lead=True)
        self.assertEqual((warning, self.verdict()["stale"]), (None, ["C1"]), "a file git ignores is not a change")

    @unittest.skipIf(os.name != "posix", "signals")
    def test_a_stop_signal_ends_the_command_and_leaves_nothing_behind(self):
        import signal
        code = "import os, time; open('pid', 'w').write(str(os.getpid())); time.sleep(60)"
        proc = subprocess.Popen([sys.executable, script("oldhand", "ledger"), "run", "--id", "AC1", "--kind", "e2e", "--by", "x",
                                 "--dir", self.d, "--", PY, "-c", code], cwd=self.root, stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE, universal_newlines=True)
        self.addCleanup(proc.kill)
        child = ""
        for _ in range(100):
            if os.path.exists("pid"):
                with open("pid") as fh:
                    child = fh.read()
            if child:
                break
            time.sleep(0.1)
        child = int(child)
        proc.send_signal(signal.SIGTERM)
        _, err = proc.communicate(timeout=30)
        self.assertEqual(proc.returncode, 4)
        self.assertIn("interrupted", err)
        self.assertEqual(ledger.load(self.d)["checks"], [])
        self.assertFalse(os.path.exists(os.path.join(self.d, "runs")), "no raw output is left on disk")
        with self.assertRaises(ProcessLookupError, msg="the command was ended too"):
            for _ in range(50):
                os.kill(child, 0)
                time.sleep(0.1)

    def test_the_command_line(self):
        def call(*args):
            return cli("oldhand", "ledger", *args, cwd=self.root)
        code, out, err = call("run", "--id", "AC1", "--kind", "e2e", "--by", "lead:x", "--lead", "--dir", self.d,
                              "--", PY, "-c", "print(open('a.txt').read())")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("C1 recorded: AC1 e2e pass (exit 0,", out)
        code, out, err = call("run", "--id", "AC2", "--kind", "integration", "--by", "lead:x", "--dir", self.d,
                              "--", "%s -c \"import sys; print('boom'); sys.exit(2)\"" % PY)
        self.assertEqual(code, 1)
        self.assertIn("AC2 integration fail (exit 2,", out)
        self.assertIn("  | boom", out)
        code, out, err = call("run", "--id", "AC2", "--kind", "unit", "--by", "lead:x", "--dir", self.d,
                              "--", "oldhand-no-such-command")
        self.assertEqual(code, 4)
        self.assertIn("could not start", err)
        self.assertEqual(call("run", "--id", "AC2", "--kind", "mutation", "--by", "x", "--dir", self.d, "--", "true")[0], 4)
        self.assertEqual(call("rerun", "--dir", self.d)[0], 4)
        with open("a.txt", "a") as fh:
            fh.write("two\n")
        code, out, err = call("rerun", "--stale", "--dir", self.d)
        self.assertEqual(code, 1, "AC2's command still fails")
        self.assertIn("C1 -> C3 recorded: AC1 e2e pass", out)
        self.assertIn("C2 -> C4 recorded: AC2 integration fail", out)
        self.rec("R1")
        with open("a.txt", "a") as fh:
            fh.write("three\n")
        code, out, _ = call("rerun", "--stale", "--dir", self.d)
        self.assertEqual(code, 1, "a stale check it could not run is left")
        self.assertIn("Still stale and not run again", out)
        self.assertIn("  C5  R1 e2e by qa:worker (no command: it was not recorded by `ledger.py run`): R1 e2e", out)
        code, out, _ = call("rerun", "--check", "C3", "--dir", self.d)
        self.assertEqual(code, 0)


class Shape(Base):
    """A hand-edited check with a field of the wrong type is an error that names the check and the field."""

    def test_a_wrong_typed_field_names_the_check_and_never_quotes_the_value(self):
        self.all_pass()
        good = ledger.load(self.d)
        for field, value, said in (("live", True, "`live` that is a bool, not a dict"),
                                   ("live", {"max_age": "1h"}, "live `max_age`"), ("live", {"max_age": True}, "live `max_age`"),
                                   ("pins", ["x"], "`pins` that is a list"), ("evidence", 5, "`evidence` that is a int"),
                                   ("env", "s3cr3t-typed-here", "`env` that is a str"), ("time", None, "`time`")):
            led = json.loads(json.dumps(good))
            led["checks"][1][field] = value
            ledger.save(self.d, led)
            with self.assertRaises(ledger.LedgerError) as e:
                self.verdict()
            self.assertIn("check C2 in", str(e.exception))
            self.assertIn(said, str(e.exception))
            self.assertNotIn("s3cr3t", str(e.exception))
        led = json.loads(json.dumps(good))
        del led["checks"][0]["by"]
        led["checks"][2] = "C3"
        ledger.save(self.d, led)
        with self.assertRaises(ledger.LedgerError) as e:
            self.verdict()
        self.assertIn("check C1 in", str(e.exception))
        self.assertIn("has no `by`", str(e.exception))
        code, _, err = cli("oldhand", "ledger", "status", "--dir", self.d)
        self.assertEqual(code, 4)
        self.assertNotIn("unexpected problem", err)
        led["checks"][0]["by"] = "qa:worker"
        led["trees"] = []
        ledger.save(self.d, led)
        with self.assertRaises(ledger.LedgerError) as e:
            self.verdict()
        self.assertIn("check number 3", str(e.exception))


if __name__ == "__main__":
    unittest.main()
