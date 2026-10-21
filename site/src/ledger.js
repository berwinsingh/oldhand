// The verdict rule from skills/oldhand/scripts/ledger.py, simplified for the
// page's demo: every criterion needs a passing check on the current code, and
// the lead must have run one end to end itself. A check recorded before the
// code changed is stale and counts for nothing.

export function verdict(rows) {
  const reasons = [];
  const missing = rows.filter((r) => !r.status);
  if (missing.length) {
    return { word: "INCOMPLETE", reasons: [`${missing.map((r) => r.id).join(", ")} has no check yet`] };
  }
  const failing = rows.filter((r) => r.status === "fail");
  const stale = rows.filter((r) => !r.fresh);
  for (const r of failing) reasons.push(`${r.id} fails`);
  if (stale.length) {
    const n = stale.length;
    reasons.push(`${n} ${n === 1 ? "check is" : "checks are"} stale: the code changed after ${n === 1 ? "it" : "they"} ran`);
  }
  if (!rows.some((r) => r.lead && r.status === "pass" && r.fresh)) {
    reasons.push("the lead has no end-to-end pass on the current code");
  }
  if (reasons.length) return { word: "NOT YET", reasons };
  return {
    word: "VERIFIED",
    reasons: ["every criterion has a passing check on the current code, and the lead ran one end to end"],
  };
}

// Visitor actions. Each returns new rows; nothing is mutated.
export const changeAFile = (rows) => rows.map((r) => ({ ...r, fresh: false }));
export const rerunChecks = (rows) => rows.map((r) => ({ ...r, fresh: true }));
export const toggleCheck = (rows, id) =>
  rows.map((r) => (r.id === id ? { ...r, status: r.status === "pass" ? "fail" : "pass", fresh: true } : r));
