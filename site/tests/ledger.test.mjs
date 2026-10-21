import assert from "node:assert/strict";
import test from "node:test";
import { changeAFile, rerunChecks, toggleCheck, verdict } from "../src/ledger.js";

const rows = [
  { id: "AC1", status: "pass", fresh: true, lead: true },
  { id: "AC2", status: "pass", fresh: true, lead: false },
  { id: "R1", status: "pass", fresh: true, lead: false },
];

test("all passing on the current code, with a lead run, is VERIFIED", () => {
  assert.equal(verdict(rows).word, "VERIFIED");
});

test("changing a file makes every check stale and the verdict NOT YET", () => {
  const v = verdict(changeAFile(rows));
  assert.equal(v.word, "NOT YET");
  assert.match(v.reasons.join(" "), /3 checks are stale/);
  assert.match(v.reasons.join(" "), /lead has no end-to-end pass/);
});

test("re-running the checks after a change restores VERIFIED", () => {
  assert.equal(verdict(rerunChecks(changeAFile(rows))).word, "VERIFIED");
});

test("one failing check blocks the verdict, and toggling it back clears it", () => {
  const failed = toggleCheck(rows, "AC2");
  assert.equal(verdict(failed).word, "NOT YET");
  assert.deepEqual(verdict(failed).reasons, ["AC2 fails"]);
  assert.equal(verdict(toggleCheck(failed, "AC2")).word, "VERIFIED");
});

test("a failing lead check also removes the lead's end-to-end pass", () => {
  const v = verdict(toggleCheck(rows, "AC1"));
  assert.deepEqual(v.reasons, ["AC1 fails", "the lead has no end-to-end pass on the current code"]);
});

test("a criterion with no check is INCOMPLETE", () => {
  assert.equal(verdict([...rows, { id: "R2", status: null, fresh: true }]).word, "INCOMPLETE");
});

test("actions never mutate their input", () => {
  const before = JSON.stringify(rows);
  changeAFile(rows);
  toggleCheck(rows, "AC1");
  assert.equal(JSON.stringify(rows), before);
});
