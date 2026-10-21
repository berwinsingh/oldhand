import json
import os
import shutil
import subprocess
import sys
import tempfile
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
    for k, v in GIT_ENV.items():
        _saved_env[k] = os.environ.get(k)
        os.environ[k] = v


def tearDownModule():
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


if __name__ == "__main__":
    unittest.main()
