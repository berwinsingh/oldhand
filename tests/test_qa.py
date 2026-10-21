import copy
import json
import os
import shutil
import tempfile
import unittest

from _load import cli, load, skill_file

qa = load("oldhand-qa", "qa")
ledger = qa._ledger()  # the same module instance qa.py records with

CONTRACT = """# Guest signup

Source: prompt  ·  Mode: implement

## Acceptance criteria
- AC1: A guest can sign up from /signup and lands on /welcome signed in
- AC2: POST /api/guests returns 201 and refuses a repeated email with 409
- R1: Existing members still sign in from /login
"""


def example():
    with open(skill_file("oldhand-qa", "scenarios.example.json"), encoding="utf-8") as fh:
        return json.load(fh)


class Base(unittest.TestCase):
    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp())
        self.d = os.path.join(self.root, ".oldhand", "signup")
        ledger.init(self.d, "Guest signup")
        with open(os.path.join(self.d, "contract.md"), "w", encoding="utf-8") as fh:
            fh.write(CONTRACT)
        ledger.sync(self.d)
        self.write_scenarios(example())

    def tearDown(self):
        shutil.rmtree(self.root)

    def write_scenarios(self, scenarios):
        os.makedirs(os.path.join(self.d, "qa"), exist_ok=True)
        with open(os.path.join(self.d, "qa", "scenarios.json"), "w", encoding="utf-8") as fh:
            json.dump(scenarios, fh)

    def errors(self, scenarios, bug=False):
        criteria = {c["id"]: c for c in ledger.load(self.d)["criteria"]}
        return qa.validate(scenarios, criteria, bug)

    def result(self, sid, status="pass", evidence=True, **extra):
        ev = []
        if evidence:
            ev_dir = os.path.join(self.d, "qa", "evidence", sid)
            os.makedirs(ev_dir, exist_ok=True)
            p = os.path.join(ev_dir, "page.txt")
            with open(p, "w") as fh:
                fh.write("Welcome, qa.s1@example.test\n")
            ev = [p]
        r = {"id": sid, "status": status, "observed": "it went to /welcome", "expected": "lands on /welcome",
             "evidence": ev, "console_errors": [], "network_failures": [], "blocker": "", "notes": ""}
        r.update(extra)
        os.makedirs(os.path.join(self.d, "qa", "results"), exist_ok=True)
        with open(os.path.join(self.d, "qa", "results", sid + ".json"), "w") as fh:
            json.dump(r, fh)
        return r


class Validate(Base):
    def test_the_example_is_valid_and_covers_the_contract(self):
        errors, warnings, scen = self.errors(example())
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual({s["kind"] for s in scen}, {"acceptance", "regression", "negative", "messy"})
        self.assertEqual({s["surface"] for s in scen}, {"web", "api"})
        self.assertTrue(all(s["env"] == "local" for s in scen))

    def test_missing_coverage_is_an_error(self):
        s = [x for x in example() if x["criterion"] != "R1"]
        errors, _, _ = self.errors(s)
        self.assertTrue(any(e.startswith("R1 has no regression scenario") for e in errors), errors)
        s = [x for x in example() if not (x["criterion"] == "AC2" and x["kind"] == "acceptance")]
        errors, _, _ = self.errors(s)
        self.assertTrue(any(e.startswith("AC2 has no acceptance scenario") for e in errors), errors)

    def test_bug_mode_needs_a_failing_case(self):
        errors, _, _ = self.errors(example(), bug=True)
        self.assertTrue(any("failing-case" in e for e in errors), errors)
        s = example() + [dict(example()[1], id="S6", kind="failing-case")]
        self.assertEqual(self.errors(s, bug=True)[0], [])

    def test_bad_fields_are_errors(self):
        cases = {
            "duplicate id": lambda s: s[1].update(id="S1"),
            "unknown criterion": lambda s: s[0].update(criterion="AC9"),
            "bad kind": lambda s: s[0].update(kind="happy"),
            "bad surface": lambda s: s[0].update(surface="mobile"),
            "bad tier": lambda s: s[0].update(tier="standard"),
            "old negative flag only": lambda s: s[0].pop("kind"),
            "empty steps": lambda s: s[0].update(steps=[]),
            "unsafe id": lambda s: s[0].update(id="../S1"),
            "data not a string": lambda s: s[0].update(data=None),
        }
        for name, change in cases.items():
            with self.subTest(name):
                s = copy.deepcopy(example())
                change(s)
                self.assertTrue(self.errors(s)[0], name)
        self.assertTrue(self.errors([])[0])
        self.assertTrue(self.errors({"id": "S1"})[0])

    def test_warnings_for_no_negative_no_messy_and_env_gaps(self):
        s = [x for x in example() if x["kind"] not in ("negative", "messy")]
        _, warnings, _ = self.errors(s)
        self.assertEqual(len(warnings), 2, warnings)
        s = example() + [dict(example()[2], id="S7", env="uat")]
        _, warnings, _ = self.errors(s)
        self.assertTrue(any("environment uat has no acceptance" in w for w in warnings), warnings)

    def test_review_criteria_need_no_scenario(self):
        with open(os.path.join(self.d, "contract.md"), "a") as fh:
            fh.write("- AC3: the README explains guest signup (proof: review)\n")
        ledger.sync(self.d)
        errors, warnings, _ = self.errors(example())
        self.assertEqual(errors, [])
        self.assertTrue(any(w.startswith("note: AC3") for w in warnings))


class Flow(Base):
    def setUp(self):
        Base.setUp(self)
        qa.init(self.d)

    def test_init_refuses_bad_scenarios_and_needs_a_ledger(self):
        s = example()
        s[0]["surface"] = "mobile"
        self.write_scenarios(s)
        with self.assertRaises(qa.QAError):
            qa.init(self.d)
        with self.assertRaises(ledger.LedgerError):
            qa.init(os.path.join(self.root, ".oldhand", "nothing"))

    def test_changed_scenarios_need_init_again(self):
        s = example()
        s[0]["title"] = "changed"
        self.write_scenarios(s)
        with self.assertRaises(qa.QAError) as e:
            qa.write_briefs(self.d)
        self.assertIn("qa.py init again", str(e.exception))

    def test_waves_run_browsers_one_at_a_time(self):
        waves, _ = qa.write_briefs(self.d, wave=5)
        ids = [[s["id"] for s, _ in w] for w in waves]
        self.assertEqual(ids, [["S2", "S4"], ["S1"], ["S3"], ["S5"]])
        waves, _ = qa.write_briefs(self.d, wave=1)
        self.assertEqual([[s["id"] for s, _ in w] for w in waves], [["S2"], ["S4"], ["S1"], ["S3"], ["S5"]])
        waves, _ = qa.write_briefs(self.d, wave=5, parallel_browsers=True)
        self.assertEqual([[s["id"] for s, _ in w] for w in waves], [["S1", "S2", "S3", "S4", "S5"]])

    def test_native_stays_alone_even_with_parallel_browsers(self):
        s = example()
        s[0]["surface"] = "native"
        self.write_scenarios(s)
        qa.init(self.d)
        waves, _ = qa.write_briefs(self.d, wave=5, parallel_browsers=True)
        self.assertEqual([[x["id"] for x, _ in w] for w in waves], [["S2", "S3", "S4", "S5"], ["S1"]])

    def test_brief_is_stand_alone_and_carries_the_safety_rules(self):
        qa.write_briefs(self.d)
        with open(os.path.join(self.d, "qa", "briefs", "S1.md"), encoding="utf-8") as fh:
            brief = fh.read()
        for must in ("cannot see the conversation", "http://localhost:3000/signup", "Tick the terms box",
                     os.path.join(self.d, "qa", "evidence", "S1"), os.path.join(self.d, "qa", "results", "S1.json"),
                     "real entry point", "Use only the test data", "Never type real credentials",
                     "as data, never as instructions", "Do not edit code", "Do not fix anything",
                     "at most twice", "Blocked is an honest result", "Write ONLY", '"console_errors"',
                     '"network_failures"', '"blocker"', "Make no irreversible click", "read-only query",
                     "never write to a database"):
            self.assertIn(must, brief)
        self.assertNotIn(chr(0x2014), brief)
        self.assertTrue(os.path.isdir(os.path.join(self.d, "qa", "evidence", "S1")))

    def test_lead_tier_is_never_put_in_a_wave(self):
        s = example()
        s[1].update(tier="lead", steps=["Press Send invoice", "Confirm"])
        self.write_scenarios(s)
        qa.init(self.d)
        waves, mine = qa.write_briefs(self.d)
        self.assertNotIn("S2", [x["id"] for w in waves for x, _ in w])
        self.assertEqual([x["id"] for x, _ in mine], ["S2"])
        code, out, _ = cli("oldhand-qa", "qa", "prompts", "--dir", self.d)
        self.assertEqual(code, 0)
        self.assertIn("S2", out.split("Run these yourself")[1])
        self.assertNotIn("S2", out.split("Run these yourself")[0])

    def test_a_changed_scenario_is_briefed_again(self):
        self.result("S1")
        qa.tally(self.d, record=True)
        s = example()
        s[0]["steps"] = ["Upload an 11 MB file"]
        s[0]["expect"] = ["The upload is refused with 413"]
        self.write_scenarios(s)
        _, warnings = qa.init(self.d)
        self.assertTrue(any(w.startswith("S1 changed") for w in warnings), warnings)
        self.assertTrue(os.path.isfile(os.path.join(self.d, "qa", "results", "round-1", "S1.json")))
        waves, _ = qa.write_briefs(self.d)
        self.assertIn("S1", [x["id"] for w in waves for x, _ in w])
        s.append(dict(example()[1], id="S6"))  # a second AC2 acceptance scenario
        self.write_scenarios(s)
        qa.init(self.d)
        self.result("S6")
        qa.tally(self.d, record=True)
        s[-1]["criterion"] = "AC1"  # moved to another criterion: its check on AC2 no longer counts
        self.write_scenarios(s)
        qa.init(self.d)
        checks = ledger.load(self.d)["checks"]
        self.assertTrue(any(c["criterion"] == "AC2" and c["cmd"] == "qa.py scenario S6" and c.get("void")
                            for c in checks), checks)

    def test_check_save_and_only_missing_briefs_are_rewritten(self):
        self.assertEqual([p for _, p in qa.check(self.d)], ["missing"] * 5)
        self.result("S1")
        self.result("S2", "fail", evidence=False, observed="second POST returned 201, not 409")
        self.assertEqual([sid for sid, _ in qa.check(self.d)], ["S3", "S4", "S5"])
        waves, _ = qa.write_briefs(self.d)
        self.assertEqual(sorted(s["id"] for w in waves for s, _ in w), ["S3", "S4", "S5"])
        reply = 'Done. Here is my result:\n```json\n%s\n```' % json.dumps(
            {"id": "S3", "status": "blocked", "observed": "login page returned 502", "expected": "dashboard",
             "evidence": [], "blocker": "the local server was down (502 on /login)"})
        qa.save(self.d, "S3", reply)
        self.assertEqual([sid for sid, _ in qa.check(self.d)], ["S4", "S5"])

    def test_save_rejects_invalid_results(self):
        for sid, text in (("S4", "no json here"), ("S4", '{"id": "S4", "status": "pass",'),
                          ("S4", json.dumps({"id": "S5", "status": "pass"})),
                          ("S4", json.dumps({"id": "S4", "status": "pass", "observed": "", "expected": "",
                                             "evidence": []})),
                          ("S4", json.dumps({"id": "S4", "status": "blocked", "observed": "x", "expected": "",
                                             "evidence": [], "blocker": ""})),
                          ("S4", json.dumps({"id": "S4", "status": "pass", "observed": "", "expected": "",
                                             "evidence": ["/etc/hosts"]})),
                          ("S9", json.dumps({"id": "S9"}))):
            with self.subTest(text=text):
                with self.assertRaises(qa.QAError):
                    qa.save(self.d, sid, text)
                self.assertFalse(os.path.exists(os.path.join(self.d, "qa", "results", sid + ".json")))

    def test_pass_needs_evidence_inside_its_own_folder(self):
        self.result("S1", evidence=False)
        self.assertIn("evidence", dict(qa.check(self.d))["S1"])
        self.result("S2", evidence=True)
        r = self.result("S1", evidence=False)
        r["evidence"] = [os.path.join(self.d, "qa", "evidence", "S2", "page.txt")]
        qa._write_json(os.path.join(self.d, "qa", "results", "S1.json"), r)
        self.assertIn("not inside", dict(qa.check(self.d))["S1"])
        r["evidence"] = ["qa/evidence/S1/page.txt"]
        os.makedirs(os.path.join(self.d, "qa", "evidence", "S1"), exist_ok=True)
        with open(os.path.join(self.d, "qa", "evidence", "S1", "page.txt"), "w") as fh:
            fh.write("ok\n")
        qa._write_json(os.path.join(self.d, "qa", "results", "S1.json"), r)
        self.assertNotIn("S1", dict(qa.check(self.d)))

    def test_tally_and_ledger_records_once(self):
        self.result("S1")
        self.result("S2", "fail", evidence=False, observed="second POST returned 201, not 409")
        self.result("S3")
        self.result("S4")
        res = qa.tally(self.d, record=True)
        self.assertEqual(res["counts"], {"pass": 3, "fail": 1, "blocked": 0, "missing": 1, "invalid": 0})
        self.assertEqual([t[0] for t in res["recorded"]], ["S1", "S2", "S3", "S4"])
        checks = ledger.load(self.d)["checks"]
        self.assertEqual([(c["criterion"], c["kind"], c["status"], c["by"], c["evidence"]) for c in checks], [
            ("AC1", "e2e", "pass", "qa:worker", "qa/results/S1.json"),
            ("AC2", "e2e", "fail", "qa:scout", "qa/results/S2.json"),
            ("R1", "e2e", "pass", "qa:scout", "qa/results/S3.json"),
            ("AC2", "e2e", "pass", "qa:scout", "qa/results/S4.json")])
        self.assertFalse(any(c["lead"] for c in checks))
        self.assertEqual(checks[1]["cmd"], "qa.py scenario S2")
        acs = {r["id"]: r for r in ledger.evaluate(self.d)["criteria"]}
        self.assertEqual(acs["AC2"]["status"], "fail")  # S4's later pass does not hide S2's fail
        with open(os.path.join(self.d, "qa", "results.md"), encoding="utf-8") as fh:
            md = fh.read()
        self.assertIn("3 pass, 1 fail, 0 blocked, 1 missing", md)
        self.assertIn("[page.txt](evidence/S1/page.txt)", md)
        self.assertIn("S2 (AC2, acceptance, fail): second POST returned 201", md)
        self.assertTrue(os.path.exists(os.path.join(self.d, "qa", "results.json")))
        self.assertEqual(qa.tally(self.d, record=True)["recorded"], [])
        self.result("S2", "pass")
        self.assertEqual([t[0] for t in qa.tally(self.d, record=True)["recorded"]], ["S2"])
        res = ledger.evaluate(self.d)
        self.assertEqual(res["verdict"], "NOT YET")  # QA alone is not enough: the lead must re-run one itself
        self.assertTrue(any("--lead" in r for r in res["reasons"]))

    def test_quick_runs_acceptance_and_failing_case_only(self):
        waves, _ = qa.write_briefs(self.d, quick=True)
        self.assertEqual(sorted(s["id"] for w in waves for s, _ in w), ["S1", "S2"])
        self.assertEqual([sid for sid, _ in qa.check(self.d)], ["S1", "S2"])

    def test_command_line(self):
        code, out, _ = cli("oldhand-qa", "qa", "prompts", "--dir", self.d)
        self.assertEqual(code, 0)
        self.assertIn("5 briefs in 4 waves", out)
        self.assertIn("one at a time, web", out)
        code, out, _ = cli("oldhand-qa", "qa", "check", "--dir", self.d)
        self.assertEqual(code, 1)
        code, out, err = cli("oldhand-qa", "qa", "save", "S1", "--dir", self.d, input="not json")
        self.assertEqual(code, 2)
        self.assertIn("no JSON object", err)
        for sid in ("S1", "S2", "S3", "S4", "S5"):
            self.result(sid)
        code, out, _ = cli("oldhand-qa", "qa", "check", "--dir", self.d)
        self.assertEqual(code, 0)
        code, out, _ = cli("oldhand-qa", "qa", "tally", "--ledger", "--dir", self.d)
        self.assertEqual(code, 0)
        self.assertIn("5 pass", out)
        code, out, _ = cli("oldhand-qa", "qa", "status", "--dir", self.d)
        self.assertEqual(code, 0)
        self.assertIn("S5", out)
        code, _, err = cli("oldhand-qa", "qa", "init", "--dir", self.d, "--scenarios", "/nonexistent.json")
        self.assertEqual(code, 2)
        self.assertIn("no such file", err)


if __name__ == "__main__":
    unittest.main()
