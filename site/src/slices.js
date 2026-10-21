// Slices of the Markdown files the page imports at build time. There is no
// Markdown renderer: the files have fixed shapes, and scripts/check-sources.mjs
// fails the build when a slice comes back empty, so a moved heading cannot
// ship an empty section.

export function section(text, headingPrefix) {
  const lines = text.split("\n");
  const start = lines.findIndex((line) => line.startsWith(headingPrefix));
  if (start < 0) return null;
  const level = lines[start].match(/^#+/)[0].length;
  let end = lines.findIndex(
    (line, i) => i > start && /^#{1,6} /.test(line) && line.match(/^#+/)[0].length <= level,
  );
  if (end < 0) end = lines.length;
  return {
    heading: lines[start].replace(/^#+\s*/, ""),
    body: lines.slice(start + 1, end).join("\n").trim(),
  };
}

// "1. item" or "- item" lines; indented continuation lines join their item.
// Returns the text before the first item as intro.
export function list(text) {
  const items = [];
  const intro = [];
  for (const line of text.split("\n")) {
    const m = line.match(/^(?:\d+\.|-)\s+(.*)$/);
    if (m) items.push(m[1]);
    else if (items.length && line.trim()) items[items.length - 1] += " " + line.trim();
    else if (!items.length && line.trim()) intro.push(line.trim());
  }
  return { intro: intro.join(" "), items };
}

// The first pipe table whose header row starts with headerStart, as trimmed cells.
export function table(text, headerStart) {
  const lines = text.split("\n");
  const first = lines.findIndex((line) => line.startsWith(headerStart));
  if (first < 0) return null;
  let end = lines.findIndex((line, i) => i > first && !line.startsWith("|"));
  if (end < 0) end = lines.length;
  const rows = lines
    .slice(first, end)
    .map((line) => line.replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim()))
    .filter((row) => !row.every((cell) => /^-+$/.test(cell)));
  return { header: rows[0], rows: rows.slice(1) };
}

// Keep only the named columns, in that order. Null when one is missing.
export function columns(tbl, names) {
  if (!tbl) return null;
  const index = names.map((name) => tbl.header.indexOf(name));
  if (index.some((i) => i < 0)) return null;
  return { header: names, rows: tbl.rows.map((row) => index.map((i) => row[i] || "")) };
}

function line(text, re) {
  const m = text.match(re);
  return m ? m[1] : null;
}

// Everything the page shows from the imported files, in one place.
export function pageData({ skill, report, orchestration, plugin }) {
  const stops = section(skill, "## Hard stops");
  const stopsList = stops ? list(stops.body) : { intro: null, items: [] };
  const notVerified = section(report, "## Not verified");
  const models = section(orchestration, "## Current models per host");
  return {
    version: plugin.version,
    hardStopsIntro: stopsList.intro,
    hardStops: stopsList.items,
    verdict: line(report, /^### (Verdict: .+)$/m),
    criteria: columns(table(report, "| criterion"), ["criterion", "outcome", "proof", "status", "by"]),
    rootCause: section(report, "## Root cause")?.body || null,
    notVerified: notVerified ? list(notVerified.body).items : [],
    computed: line(report, /^(Computed by ledger\.py .+)$/m),
    modelsDate: models ? line(models.heading, /\((as of [^)]+)\)/) : null,
    models: models ? columns(table(models.body, "| host"), ["host", "lead", "worker", "scout"]) : null,
  };
}

// Names of the slices that came back empty.
export function missing(data) {
  return Object.entries(data)
    .filter(([, value]) => {
      if (value == null || value === "") return true;
      if (Array.isArray(value)) return value.length === 0;
      if (value.rows) return value.rows.length === 0;
      return false;
    })
    .map(([key]) => key);
}
