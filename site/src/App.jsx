import { useEffect, useState } from "react";
import { Badge } from "@astryxdesign/core/Badge";
import { Button } from "@astryxdesign/core/Button";
import { Code } from "@astryxdesign/core/Code";
import { CodeBlock } from "@astryxdesign/core/CodeBlock";
import { Collapsible } from "@astryxdesign/core/Collapsible";
import { Heading } from "@astryxdesign/core/Heading";
import { HStack } from "@astryxdesign/core/HStack";
import { Link } from "@astryxdesign/core/Link";
import { Tab, TabList } from "@astryxdesign/core/TabList";
import { Table, proportional } from "@astryxdesign/core/Table";
import { Text } from "@astryxdesign/core/Text";
import { VStack } from "@astryxdesign/core/VStack";
import skillText from "../../skills/oldhand/SKILL.md?raw";
import reportText from "../../examples/csv-import-dupes/oldhand/report.md?raw";
import orchestrationText from "../../skills/oldhand/references/orchestration.md?raw";
import plugin from "../../.claude-plugin/plugin.json";
import { applyAnalyticsChoice, readAnalyticsChoice, saveAnalyticsChoice } from "./analytics.js";
import { BENCH_RUN } from "./bench-run.js";
import { benchData, pageData } from "./slices.js";

const benchRuns = import.meta.glob("../../bench/results/*/runs.jsonl", { query: "?raw", import: "default", eager: true });
const benchTasks = import.meta.glob("../../bench/tasks/*/task.json", { import: "default", eager: true });

const REPO = "https://github.com/berwinsingh/oldhand";
const BLOB = `${REPO}/blob/main/`;
const EXAMPLE_DIR = `${REPO}/tree/main/examples/csv-import-dupes`;
const REPORT = `${BLOB}examples/csv-import-dupes/oldhand/report.md`;
const TESTED = "2026-10-11";
const EXAMPLE = "Fix DOCQ-123. Prove: guest signup, reload, data persists.";
const NPX = "npx skills add berwinsingh/oldhand --skill '*' -g";

// Every command below was run on this date in a throwaway home folder, from a
// local checkout of this repository; the GitHub source serves the same files.
const installs = [
  {
    key: "any",
    label: "npx",
    blocks: [NPX],
    note:
      "Installs all eleven skills under ~/.agents/skills and links them for the agents it finds. Add -a cursor (or codex, github-copilot, gemini-cli, opencode, claude-code) to skip the picker.",
    tested: `Tested ${TESTED} on macOS with skills 1.7.2 for claude-code, codex, cursor, github-copilot, gemini-cli and opencode, from a local checkout of this repository.`,
    then: [
      ["Claude Code, Cursor, Copilot, Kiro, Antigravity", `/oldhand ${EXAMPLE}`],
      ["Codex", `$oldhand ${EXAMPLE}`],
      ["Gemini CLI, OpenCode, Amp, Goose", "Use the oldhand skill: fix DOCQ-123 and prove it end to end."],
    ],
  },
  {
    key: "claude",
    label: "Claude Code plugin",
    blocks: ["/plugin marketplace add berwinsingh/oldhand", "/plugin install oldhand@oldhand"],
    note: "Two separate prompts inside Claude Code, then a new session.",
    tested: `Tested ${TESTED} with Claude Code 2.1.274 (the claude plugin CLI, from a local checkout of this repository).`,
    then: [["Claude Code", `/oldhand:oldhand ${EXAMPLE}`]],
  },
  {
    key: "codex",
    label: "Codex plugin",
    blocks: ["codex plugin marketplace add berwinsingh/oldhand\ncodex plugin add oldhand@oldhand"],
    note: "Then restart Codex or start a new task.",
    tested: `Tested ${TESTED} with Codex CLI 0.146.0, from a local checkout of this repository.`,
    then: [["Codex", `$oldhand ${EXAMPLE}`]],
  },
  {
    key: "git",
    label: "git clone",
    blocks: [
      'git clone https://github.com/berwinsingh/oldhand ~/.oldhand\nmkdir -p ~/.agents/skills ~/.claude/skills\nfor s in ~/.oldhand/skills/*; do ln -sfn "$s" ~/.agents/skills/; ln -sfn "$s" ~/.claude/skills/; done',
    ],
    note:
      "~/.agents/skills is read by Codex, Cursor, Copilot, Gemini CLI, OpenCode, Amp, Roo, Goose, Droid and Junie; ~/.claude/skills by Claude Code. Update with git -C ~/.oldhand pull.",
    tested: `Tested ${TESTED} on macOS with git 2.55.0 and zsh 5.9 against a clone of this branch: eleven links in each folder, and running it twice changes nothing.`,
    then: [
      ["Claude Code, Cursor, Copilot", `/oldhand ${EXAMPLE}`],
      ["Codex", `$oldhand ${EXAMPLE}`],
    ],
  },
];

const stages = [
  ["contract", "The request becomes numbered criteria, each with the proof it needs."],
  ["trace", "The real code path, and every caller of what will change."],
  ["rca", "Root cause for bugs, with refuters trying to break it first."],
  ["research", "Looks for something to reuse in the codebase, the standard library, the platform, then dependencies."],
  ["plan", "The smallest complete change, with blast radius and rollback."],
  ["build", "The fix and one focused test, proven by breaking the fix on purpose and watching the test fail."],
  ["review", "Read-only reviewers, one lens each; the chair refutes every finding."],
  ["qa", "A sub-agent per scenario drives the real app and brings back evidence."],
  ["ship", "A script computes the verdict from the ledger."],
  ["learn", "The non-obvious lessons go where the project keeps its instructions."],
];

const tools = [
  ["ledger.py", "skills/oldhand/scripts/ledger.py", "records every check against the exact tree and computes the verdict"],
  ["qa.py", "skills/oldhand-qa/scripts/qa.py", "deals the scenario briefs and tallies the results"],
  ["mutate.py", "skills/oldhand-build/scripts/mutate.py", "breaks the fix on purpose and expects the test to fail"],
];

const data = pageData({ skill: skillText, report: reportText, orchestration: orchestrationText, plugin });
const bench = benchData(
  benchRuns[`../../bench/results/${BENCH_RUN}/runs.jsonl`],
  Object.fromEntries(Object.values(benchTasks).map((t) => [t.id, t.tier])),
);
const [benchDate, benchModel] = [BENCH_RUN.slice(0, 10), BENCH_RUN.slice(11)];
const maxTokens = Math.max(...bench.arms.map((a) => a.tokens));
const plainArm = bench.arms.find((a) => a.key === "plain");
const verdictWord = (data.verdict || "").replace(/^Verdict:\s*/, "");
const criteriaIds = data.criteria.rows.map((row) => row[0]);
const criteriaPassed = data.criteria.rows.filter((row) => row[3] === "pass").length;
const diff = (data.diffStat || "").match(/(\d+) insertions?, (\d+) deletions? in (\d+) files?/) || [];
const proofLine = (re) => data.proof.find((item) => re.test(item)) || "";
const [f1Id, f1Sev, f1Lens, f1Status] = data.findings.rows[0] || [];
const skillLines = skillText.split("\n").length;

// The run as a list: every value is sliced from report.md at build time, and
// the small line under each is the report's own sentence.
const run = [
  ["contract", `${criteriaIds.length} criteria`, `${criteriaIds.join(", ")}; proof e2e`],
  ["changed", `${diff[3]} files`, `${diff[1]} insertions, ${diff[2]} deletions`],
  ["tests", `${data.unitScore} OK`, proofLine(/unit suite/)],
  ["mutation", data.mutation, proofLine(/KILLED/)],
  ["review", `${f1Id} ${f1Sev}, ${f1Status}`, `${f1Lens} lens; ${data.findings.rows.length} finding in all`],
  ["qa", `${data.qaScore} pass`, proofLine(/QA \d+\/\d+ pass/)],
  ["lead", "own run", proofLine(/^lead's own run/)],
];

function inline(text) {
  return text.split(/(`[^`]*`)/g).map((part, i) =>
    part.startsWith("`") ? <Code key={i} size="inherit">{part.slice(1, -1)}</Code> : part,
  );
}

const pad = (n) => String(n).padStart(2, "0");

// The mark: an open hand, the old hand that signs the work off.
function Mark({ size = 26 }) {
  return (
    <svg className="mark" width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" focusable="false">
      <circle cx="32" cy="32" r="31" fill="currentColor" />
      <g className="mark-hand">
        <rect x="21" y="30" width="25" height="22" rx="7" />
        <rect x="21" y="17" width="5.6" height="20" rx="2.8" />
        <rect x="27.6" y="11" width="5.6" height="26" rx="2.8" />
        <rect x="34.2" y="13" width="5.6" height="24" rx="2.8" />
        <rect x="40.8" y="19" width="5.2" height="18" rx="2.6" />
        <rect x="11" y="33" width="5.6" height="16" rx="2.8" transform="rotate(-40 13.8 41)" />
      </g>
    </svg>
  );
}

// A markdown table slice from report.md or orchestration.md, as an Astryx Table.
function SliceTable({ data: tbl, label }) {
  if (!tbl) return null;
  const rows = tbl.rows.map((row, r) => ({ id: r, row }));
  const columns = tbl.header.map((h, c) => ({
    key: `c${c}`,
    header: h,
    width: proportional(c === 0 ? 1 : 2, { minWidth: 110 }),
    renderCell: (item) => <Text type="inherit">{inline(item.row[c] || "")}</Text>,
  }));
  return (
    <div className="table-wrap" role="region" aria-label={label}>
      <Table data={rows} columns={columns} idKey="id" density="compact" verticalAlign="top" />
    </div>
  );
}

function Chapter({ id, n, kicker, title, children }) {
  return (
    <section id={id} className="chapter" aria-labelledby={`${id}-title`}>
      <header className="chapter-head">
        <span className="chapter-n">§ {pad(n)}</span>
        <span className="chapter-kicker">{kicker}</span>
      </header>
      <div className="chapter-body">
        <Heading level={2} id={`${id}-title`} className="chapter-title">{title}</Heading>
        {children}
      </div>
    </section>
  );
}

// True below 640px: the criteria table folds its Proof and By columns into the first.
function useNarrow() {
  const query = "(max-width: 640px)";
  const [narrow, setNarrow] = useState(() => matchMedia(query).matches);
  useEffect(() => {
    const list = matchMedia(query);
    const onChange = () => setNarrow(list.matches);
    list.addEventListener("change", onChange);
    return () => list.removeEventListener("change", onChange);
  }, []);
  return narrow;
}

function tabFromUrl() {
  const key = new URLSearchParams(window.location.search).get("agent");
  return installs.some((i) => i.key === key) ? key : installs[0].key;
}

function InstallSwitcher() {
  const [tab, setTab] = useState(tabFromUrl);
  const current = installs.find((i) => i.key === tab);

  // TabList moves focus on the arrow keys, Home and End; selection follows
  // focus (automatic activation, as in the WAI-ARIA tabs pattern).
  function onFocus(event) {
    const key = event.target.closest('[role="tab"]')?.id?.replace(/^tab-/, "");
    if (key && key !== tab && installs.some((i) => i.key === key)) setTab(key);
  }

  return (
    <div className="install">
      <div onFocus={onFocus}>
        <TabList value={tab} onChange={setTab} role="tablist" hasDivider aria-label="Install route">
          {installs.map((i) => (
            <Tab key={i.key} id={`tab-${i.key}`} value={i.key} label={i.label} panelId={`panel-${i.key}`} />
          ))}
        </TabList>
      </div>
      <div className="install-panel" role="tabpanel" id={`panel-${current.key}`} aria-labelledby={`tab-${current.key}`}>
        {current.blocks.map((block, n) => (
          <CodeBlock key={block} code={block} language="bash" title={`step ${n + 1}`} width="100%" />
        ))}
        <Text type="supporting" as="p" display="block">{current.note}</Text>
        <dl className="then">
          {current.then.map(([hosts, text]) => (
            <div key={hosts}>
              <dt>Then, in {hosts}</dt>
              <dd><Code>{text}</Code></dd>
            </div>
          ))}
        </dl>
        <Text type="supporting" as="p" display="block">
          {current.tested} Invocation per host:{" "}
          <Link href={`${BLOB}skills/oldhand/references/hosts.md`}>hosts.md</Link>.
        </Text>
      </div>
    </div>
  );
}

// The hero's ledger sheet: the example run printed line by line, then the
// verdict stamped. Plain CSS animation; under reduced motion it is all there.
// Each row carries the report's own sentence; long ones are clamped to two
// lines on screen, with the full text kept in the DOM and in the tooltip.
function LedgerSheet() {
  return (
    <figure className="sheet" aria-labelledby="sheet-title">
      <figcaption className="sheet-head">
        <span id="sheet-title">report · csv-import-dupes</span>
        <Link href={REPORT} color="secondary">report.md ↗</Link>
      </figcaption>
      <p className="sheet-prompt"><span className="sheet-caret">›</span> /oldhand {data.asked}</p>
      <ol className="sheet-rows">
        {run.map(([k, v, d], i) => (
          <li key={k} style={{ "--i": i }}>
            <span className="k">{k}</span>
            <span className="v">{v}</span>
            <span className="d" title={d}>{inline(d)}</span>
          </li>
        ))}
      </ol>
      <div className="sheet-verdict" style={{ "--i": run.length }}>
        <span className="k">verdict</span>
        <span className="stamp" aria-label={`Verdict: ${verdictWord}`}>{verdictWord}</span>
        <span className="d">{data.computed}</span>
      </div>
    </figure>
  );
}

export function App() {
  const [analytics, setAnalytics] = useState(readAnalyticsChoice);
  const narrow = useNarrow();
  useEffect(() => {
    applyAnalyticsChoice(analytics);
  }, [analytics]);

  function toggleAnalytics() {
    const next = analytics === "granted" ? "denied" : "granted";
    saveAnalyticsChoice(next);
    setAnalytics(next);
  }

  const criteriaRows = data.criteria.rows.map(([id, outcome, proof, status, by]) => ({ id, outcome, proof, status, by }));
  const criteriaColumns = [
    {
      key: "id",
      header: "Criterion",
      width: proportional(narrow ? 3 : 5, { minWidth: narrow ? 110 : 150 }),
      renderCell: (r) => (
        <VStack gap={0.5}>
          <Text weight="semibold" type="inherit">{r.id}</Text>
          <Text type="supporting">{inline(r.outcome)}</Text>
          {narrow && <Text type="supporting">proof {r.proof} · by <Code size="inherit">{r.by}</Code></Text>}
        </VStack>
      ),
    },
    !narrow && { key: "proof", header: "Proof", width: proportional(1, { minWidth: 56 }) },
    {
      key: "status",
      header: "Status",
      width: proportional(1, { minWidth: 64 }),
      renderCell: (r) => <Badge label={r.status} variant={r.status === "pass" ? "success" : "error"} />,
    },
    !narrow && { key: "by", header: "By", width: proportional(1.5, { minWidth: 130 }), renderCell: (r) => <Code>{r.by}</Code> },
  ].filter(Boolean);

  return (
    <>
      <header className="top">
        <a className="wordmark" href="#top"><Mark /> <span>oldhand</span></a>
        <nav aria-label="Sections" className="top-nav">
          <a href="#how">How it works</a>
          <a href="#example">Example</a>
          <a href="#benchmark">Benchmark</a>
          <a href="#install">Install</a>
        </nav>
        <Button label="GitHub ↗" href={REPO} size="sm" variant="ghost" />
      </header>

      <main id="top">
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-copy">
            <p className="eyebrow">
              Oldhand v{data.version} · MIT · eleven agent skills
            </p>
            <h1 id="hero-title" className="display">
              Make your coding agent <em>prove</em> it&nbsp;is&nbsp;done.
            </h1>
            <p className="lede">
              For Claude Code, Codex, Cursor, Copilot, Gemini CLI and any agent that reads{" "}
              <Code size="inherit">SKILL.md</Code>. One request runs through ten stages, and a small
              script reads the recorded evidence and prints the verdict, so the model can't declare
              itself done.
            </p>
            <div className="hero-install">
              <CodeBlock code={NPX} language="bash" title="install" width="100%" hasLanguageLabel={false} />
            </div>
            <HStack gap={3} align="center" wrap="wrap" className="hero-actions">
              <Button label="All install options" href="#install" variant="primary" size="lg" />
              <Button label="Read the conductor skill" href={`${BLOB}skills/oldhand/SKILL.md`} variant="ghost" size="lg" />
            </HStack>
            <p className="alt">
              Then type <Code>/oldhand</Code> and describe the work, or <Code>/oldhand --lean</Code> for
              one agent. Also as a <Link href="#install">Claude Code or Codex plugin</Link>.
            </p>
          </div>
          <LedgerSheet />
        </section>

        <p className="stats-caption">From the example run below</p>
        <ul className="stats" aria-label="Numbers from the example run">
          <li><b>{criteriaIds.length}</b><span>criteria, each proved end to end</span></li>
          <li><b>2</b><span>root causes; the request <Link href={`${BLOB}examples/csv-import-dupes/oldhand/rca.md`}>assumed one</Link></span></li>
          <li><b>{data.findings.rows.length}</b><span>review finding, fixed before the verdict</span></li>
          <li><b>{data.qaScore}</b><span>QA scenarios through the real CLI</span></li>
        </ul>

        <Chapter id="how" n={1} kicker="The chain" title="How it works">
          <p className="prose">
            The conductor, <Link href={`${BLOB}skills/oldhand/SKILL.md`}>oldhand</Link>, routes one request
            through ten stage skills in order. <Code>rca</Code> runs only for bugs,{" "}
            <Code>research</Code> only when something new is built. Each stage writes its file into{" "}
            <Code>.oldhand/&lt;task&gt;/</Code> and can run alone.
          </p>
          <ol className="stages">
            {stages.map(([name, text], i) => (
              <li key={name} className={name === "ship" ? "is-ship" : ""}>
                <span className="n">{pad(i + 1)}</span>
                <a className="stage-name" href={`${BLOB}skills/oldhand-${name}/SKILL.md`}>{name}</a>
                <span className="t">{text}</span>
              </li>
            ))}
          </ol>
          <ul className="tools" aria-label="The three scripts">
            {tools.map(([name, path, text]) => (
              <li key={name}>
                <Link href={BLOB + path}><Code>{name}</Code></Link>
                <span>{text}</span>
              </li>
            ))}
          </ul>
        </Chapter>

        <Chapter id="example" n={2} kicker="One recorded run" title="Example run">
          <p className="prose">
            The example is a seeded bug in a small Python importer. A transient write failure plus a
            retry stored a CSV batch twice. The project and the task folder the pack wrote are in{" "}
            <Link href={EXAMPLE_DIR}>examples/csv-import-dupes</Link>; the table is read from its{" "}
            <Link href={REPORT}>report.md</Link> at build time.
          </p>
          <div className="table-wrap">
            <Table data={criteriaRows} columns={criteriaColumns} idKey="id" verticalAlign="top" />
          </div>
          <p className="verdict-line">
            <Badge label={verdictWord} variant={verdictWord === "VERIFIED" ? "success" : "warning"} />
            <span>{criteriaPassed} of {criteriaIds.length} criteria pass on the current tree. {data.computed}</span>
          </p>
          <Collapsible defaultIsOpen={false} trigger={<Text weight="semibold">Review findings, root cause and what was not verified</Text>}>
            <VStack gap={4} paddingBlockStart={3}>
              <Heading level={3}>Review findings</Heading>
              <SliceTable data={data.findings} label="Review findings" />
              <Heading level={3}>Root cause</Heading>
              <p className="prose">{inline(data.rootCause || "")}</p>
              <Heading level={3}>Not verified</Heading>
              <ul className="plain">{data.notVerified.map((item, i) => <li key={i}>{inline(item)}</li>)}</ul>
            </VStack>
          </Collapsible>
        </Chapter>

        <Chapter id="benchmark" n={3} kicker={`${bench.runs} runs, one hidden check`} title="Benchmark">
          <p className="prose">
            {bench.runs} headless Claude Code runs on {bench.tasks} small bug-fix tasks, {bench.hard} of
            them harder multi-file ones, one run per task and route. A hidden check drives the real
            program and decides whether the work was really done; the agent never sees it.
          </p>
          <div className="bench" role="table" aria-label="Benchmark results, medians per run">
            <div className="bench-row bench-head" role="row">
              <span role="columnheader">Route</span>
              <span role="columnheader">Hidden check passed</span>
              <span role="columnheader">False DONE</span>
              <span role="columnheader">Tokens and cost per run</span>
            </div>
            {bench.arms.map((a) => (
              <div key={a.key} className="bench-row" role="row">
                <span role="cell" className="bench-arm">{a.key === "plain" ? a.label : <Code>{a.label}</Code>}</span>
                <span role="cell" data-label="Passed" className="bench-num"><b>{a.passed}</b> / {a.runs}</span>
                <span role="cell" data-label="False DONE">
                  <Badge label={String(a.falseDone)} variant={a.falseDone ? "error" : "neutral"} />
                </span>
                <span role="cell" className="bench-cost">
                  <span className="bench-bar" aria-hidden="true"><i style={{ width: `${(a.tokens / maxTokens) * 100}%` }} /></span>
                  <span className="bench-figs">
                    {Math.floor(a.tokens).toLocaleString("en-US")} tok · ${a.cost.toFixed(2)}
                    {a.key !== "plain" && plainArm ? ` · ${(a.cost / plainArm.cost).toFixed(1)}×` : ""}
                  </span>
                </span>
              </div>
            ))}
          </div>
          <Text type="supporting" as="p" display="block">
            Medians per run. Cost at API prices as Claude Code reports it: ${bench.totalCost.toFixed(2)} for
            all {bench.runs} runs, {benchDate}, model alias <Code>{benchModel}</Code>.
          </Text>
          {bench.falseDone.map((f) => (
            <blockquote key={f.task + f.arm} className="callout">
              The false DONE ({f.arm} agent, <Code>{f.task}</Code>): it tested its change by writing its
              own fixture over the project's <Code>config.json</Code>, deleted it, shipped a program that
              crashes, and reported done. Both Oldhand runs of that task passed.
            </blockquote>
          ))}
          <ul className="plain">
            <li>On small, clearly specified fixes the model is already good, and Oldhand costs several times as much. Use <Code>--lean</Code> or plain prompting for small, low-risk changes.</li>
            <li>One run per task and route is too few to measure a failure rate. It does measure cost, and it caught one real case of the failure Oldhand is built for.</li>
            <li>Every task was small, so <Code>/oldhand</Code> chose the lean route each time, and the full chain with review and QA sub-agents hasn't been measured yet.</li>
          </ul>
          <p className="prose">
            Tasks, method, every run and how to re-run it:{" "}
            <Link href={`${BLOB}bench/README.md`}>bench/README.md</Link>.
          </p>
        </Chapter>

        <Chapter id="install" n={4} kicker={`${installs.length} routes, each tested ${TESTED}`} title="Install">
          <InstallSwitcher />
        </Chapter>

        <Chapter id="stops" n={5} kicker="Hard stops" title="What it will not do">
          <p className="prose">
            The hard stops, as written at the top of{" "}
            <Link href={`${BLOB}skills/oldhand/SKILL.md`}>the conductor skill</Link>. {data.hardStopsIntro}
          </p>
          {/* one span per item: in a grid, a bare <code> child would take the number column */}
          <ol className="stops">{data.hardStops.map((item, i) => <li key={i}><span>{inline(item)}</span></li>)}</ol>
        </Chapter>

        <Chapter id="models" n={6} kicker="Lead, worker, scout" title="Models">
          <p className="prose">
            The skills name roles, and one dated file maps them to models. The lead owns the contract,
            the review chair, the final check and the release decision. Workers implement,
            investigate, review and drive QA. Scouts sweep files, read logs and run read-only checks.{" "}
            <Link href={`${BLOB}skills/oldhand/references/orchestration.md`}>orchestration.md</Link> has the
            current models ({data.modelsDate}).
          </p>
          <SliceTable data={data.models} label="Models per host and role" />
        </Chapter>

        <Chapter id="scope" n={7} kicker="Read before you adopt" title="Limits">
          <ul className="plain">
            <li>It is instructions plus three small scripts, so an agent can still ignore it. The ledger only refuses to print VERIFIED without evidence on the current tree.</li>
            <li>It costs turns and tokens. Review lenses and QA scenarios are sub-agents; the conductor tells you the count before spawning more than ten.</li>
            <li>Browser and desktop QA need a browser or computer-use tool on your host. Without one, UI scenarios are reported as blocked, never as passed.</li>
            <li>Skip it for typos, lookups and one-line edits. The skill says so itself.</li>
            <li>The example ran in a host with no sub-agent tool, so its reviews and QA were run by one agent in turn. Its report says so.</li>
          </ul>
        </Chapter>

        <Chapter id="skill" n={8} kicker="The source" title="The skill">
          <Collapsible
            defaultIsOpen={false}
            trigger={
              <Text weight="semibold">
                The conductor, <Code>skills/oldhand/SKILL.md</Code>: {skillLines} lines, imported when this page was built
              </Text>
            }
          >
            <VStack gap={3} paddingBlockStart={3}>
              <Link href={`${BLOB}skills/oldhand/SKILL.md`}>View on GitHub ↗</Link>
              <CodeBlock code={skillText} language="markdown" title="SKILL.md" width="100%" maxHeight={560} isWrapped />
            </VStack>
          </Collapsible>
        </Chapter>
      </main>

      <footer className="foot">
        <div className="foot-close">
          <p className="foot-line">Install the eleven skills</p>
          <CodeBlock code={NPX} language="bash" title="install" width="100%" hasLanguageLabel={false} />
        </div>
        <div className="foot-row">
          <span>oldhand v{data.version} · MIT · Berwin Singh</span>
          <nav aria-label="Project links">
            <Link href={REPO} color="secondary">GitHub</Link>
            <Link href={`${REPO}/issues`} color="secondary">Issues</Link>
            <Link href={`${REPO}/discussions`} color="secondary">Discussions</Link>
            <Link href={`${BLOB}SECURITY.md`} color="secondary">Security</Link>
          </nav>
        </div>
        <p className="analytics">
          {analytics === "granted" ? "Google Analytics is on." : "Google Analytics is off; nothing is sent."}{" "}
          <button type="button" className="link" onClick={toggleAnalytics}>
            {analytics === "granted" ? "Turn it off" : "Turn on Google Analytics"}
          </button>
          {" · "}
          <Link href="https://policies.google.com/technologies/partner-sites" color="secondary">How Google uses data</Link>
        </p>
      </footer>
    </>
  );
}
