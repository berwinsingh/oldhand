#!/usr/bin/env node
// Fails the build when a file the page imports no longer has the shape the
// page slices: a moved heading would otherwise ship an empty section.
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { readdirSync } from "node:fs";
import { benchData, missing, pageData } from "../src/slices.js";
import { BENCH_RUN } from "../src/bench-run.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const read = (rel) => readFileSync(path.join(root, rel), "utf8");

const data = pageData({
  skill: read("skills/oldhand/SKILL.md"),
  report: read("examples/csv-import-dupes/oldhand/report.md"),
  orchestration: read("skills/oldhand/references/orchestration.md"),
  plugin: JSON.parse(read(".claude-plugin/plugin.json")),
});

const problems = missing(data).map((key) => `${key}: empty slice`);
if (data.hardStops.length < 8) problems.push(`hardStops: only ${data.hardStops.length} items`);
if (!/^\d+\.\d+\.\d+$/.test(data.version || "")) problems.push(`version: ${data.version}`);

const tiers = {};
for (const t of readdirSync(path.join(root, "bench", "tasks"))) tiers[t] = JSON.parse(read(`bench/tasks/${t}/task.json`)).tier;
const bench = benchData(read(`bench/results/${BENCH_RUN}/runs.jsonl`), tiers);
if (bench.arms.length !== 3 || bench.arms.some((a) => !a.runs || !a.tokens)) problems.push("bench: an arm has no runs or no tokens");

if (problems.length) {
  console.error("check-sources: the page would ship an empty section:\n  " + problems.join("\n  "));
  process.exit(1);
}
console.log(
  `check-sources: ok (v${data.version}, bench ${bench.runs} runs, ${data.hardStops.length} hard stops, ${data.criteria.rows.length} criteria, ${data.models.rows.length} hosts, ${data.notVerified.length} not-verified items)`,
);
