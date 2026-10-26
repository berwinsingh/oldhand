import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import test from "node:test";
import { BENCH_RUN } from "../src/bench-run.js";
import { benchData, columns, list, missing, pageData, section, table } from "../src/slices.js";

const root = new URL("../../", import.meta.url);
const read = (rel) => readFileSync(new URL(rel, root), "utf8");

test("section matches a heading by prefix and stops at the next heading of the same level", () => {
  const text = "# T\n\n## Hard stops (v2)\n\nintro\n\n1. a\n   more a\n2. b\n\n### sub\n\nstill inside\n\n## Next\n\nno";
  const s = section(text, "## Hard stops");
  assert.equal(s.heading, "Hard stops (v2)");
  assert.match(s.body, /still inside$/);
  assert.equal(section(text, "## Gone"), null);
});

test("list keeps the intro and joins continuation lines", () => {
  const { intro, items } = list("intro line\n\n1. a\n   more a\n2. b\n- c");
  assert.equal(intro, "intro line");
  assert.deepEqual(items, ["a more a", "b", "c"]);
});

test("table reads the first matching pipe table, also when it ends the file", () => {
  const t = table("x\n| id | n |\n| --- | --- |\n| A | 1 |\n| B | 2 |", "| id");
  assert.deepEqual(t.header, ["id", "n"]);
  assert.deepEqual(t.rows, [["A", "1"], ["B", "2"]]);
  assert.equal(columns(t, ["n", "id"]).rows[0].join(), "1,A");
  assert.equal(columns(t, ["id", "missing"]), null);
  assert.equal(table("none", "| id"), null);
});

test("the committed sources slice completely", () => {
  const data = pageData({
    skill: read("skills/oldhand/SKILL.md"),
    report: read("examples/csv-import-dupes/oldhand/report.md"),
    orchestration: read("skills/oldhand/references/orchestration.md"),
    plugin: JSON.parse(read(".claude-plugin/plugin.json")),
  });
  assert.deepEqual(missing(data), []);
  assert.ok(data.hardStops.length >= 8);
  assert.equal(data.criteria.header.join(), "criterion,outcome,proof,status,by");
  assert.match(data.modelsDate, /^as of /);
  assert.ok(data.models.rows.length >= 4);
  assert.equal(data.findings.header.join(), "id,sev,lens,status");
  assert.match(data.qaScore, /^\d+\/\d+$/);
  assert.equal(data.mutation, "KILLED");
  assert.match(data.leadRun, /^S\d/);
  assert.ok(data.proof.every((item) => !item.startsWith("observed")));
});

test("a moved heading is reported, not silently empty", () => {
  const data = pageData({
    skill: "# x\n\n## Hard rules\n\n1. a\n",
    report: "# r\n\n### Verdict: VERIFIED\n\n| criterion | outcome | proof | status | by |\n| - | - | - | - | - |\n| AC1 | ok | e2e | pass | lead |\n\nComputed by ledger.py now.\n",
    orchestration: "## Models\n",
    plugin: { version: "2.0.0" },
  });
  assert.deepEqual(missing(data).sort(), ["asked", "diffStat", "findings", "hardStops", "hardStopsIntro", "leadRun", "models", "modelsDate", "mutation", "notVerified", "proof", "qaScore", "rootCause", "unitScore"]);
});

test("benchData takes medians per route and lists the false DONE runs", () => {
  const row = (task, arm, pass, falseDone, tokens, cost) =>
    JSON.stringify({ task, arm, hidden_check: pass ? "pass" : "fail", false_done: falseDone, tokens, cost_usd: cost, minutes: 1, subagents: 0 });
  const text = [
    row("a", "plain", true, false, 100, 0.1), row("b", "plain", false, true, 300, 0.3),
    row("a", "lean", true, false, 1000, 1), row("b", "lean", true, false, 2000, 2),
  ].join("\n") + "\n";
  const b = benchData(text, { a: "basic", b: "hard" });
  assert.equal(b.runs, 4);
  assert.equal(b.tasks, 2);
  assert.equal(b.hard, 1);
  assert.deepEqual(b.falseDone, [{ task: "b", arm: "plain" }]);
  assert.deepEqual(b.arms.map((a) => [a.key, a.passed, a.falseDone, a.tokens]), [["plain", 1, 1, 200], ["lean", 2, 0, 1500]]);
});

test("the published benchmark slices", () => {
  const tiers = {};
  for (const t of readdirSync(new URL("bench/tasks", root))) tiers[t] = JSON.parse(read(`bench/tasks/${t}/task.json`)).tier;
  const b = benchData(read(`bench/results/${BENCH_RUN}/runs.jsonl`), tiers);
  assert.equal(b.arms.length, 3);
  assert.ok(b.arms.every((a) => a.runs > 0 && a.tokens > 0));
});
