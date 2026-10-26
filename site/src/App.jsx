import { useEffect, useRef, useState } from "react";
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
    part.startsWith("`") ? <code key={i}>{part.slice(1, -1)}</code> : part,
  );
}

// The mark: an open hand, the old hand that signs the work off.
function Mark({ size = 22 }) {
  return (
    <svg className="mark" width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" focusable="false">
      <circle cx="32" cy="32" r="31" fill="currentColor" />
      <g fill="var(--bg)">
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

function Table({ data: tbl }) {
  if (!tbl) return null;
  return (
    <div className="scroll" tabIndex={0}>
      <table>
        <thead>
          <tr>{tbl.header.map((cell) => <th key={cell}>{cell}</th>)}</tr>
        </thead>
        <tbody>
          {tbl.rows.map((row, r) => (
            <tr key={r}>{row.map((cell, c) => <td key={c} data-col={tbl.header[c]}>{inline(cell)}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CopyButton({ value, label, text = "Copy" }) {
  const [state, setState] = useState("idle");
  async function copy(event) {
    const button = event.currentTarget;
    let ok = false;
    try {
      await navigator.clipboard.writeText(value);
      ok = true;
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = value;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      ok = document.execCommand("copy");
      textarea.remove();
      button.focus();
    }
    setState(ok ? "copied" : "failed");
    window.setTimeout(() => setState("idle"), 1600);
  }
  const shown = state === "copied" ? "Copied" : state === "failed" ? "Copy failed: select the text" : text;
  return (
    <button className="copy" type="button" onClick={copy} aria-label={label}>
      <span role="status">{shown}</span>
    </button>
  );
}

function Command({ text, index }) {
  return (
    <div className="command">
      <pre><code>{text}</code></pre>
      <CopyButton value={text} label={`Copy command ${index}`} />
    </div>
  );
}

function tabFromUrl() {
  const key = new URLSearchParams(window.location.search).get("agent");
  return installs.some((i) => i.key === key) ? key : installs[0].key;
}

function InstallSwitcher() {
  const [tab, setTab] = useState(tabFromUrl);
  const current = installs.find((i) => i.key === tab);

  function onKeyDown(event) {
    if (event.metaKey || event.altKey || event.ctrlKey || event.shiftKey) return;
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    event.preventDefault();
    const index = installs.findIndex((i) => i.key === tab);
    const next = installs[(index + step + installs.length) % installs.length].key;
    setTab(next);
    document.getElementById(`tab-${next}`)?.focus();
  }

  return (
    <div className="install">
      <div className="tabs" role="tablist" aria-label="Install route" onKeyDown={onKeyDown}>
        {installs.map((i) => (
          <button
            key={i.key}
            id={`tab-${i.key}`}
            role="tab"
            type="button"
            aria-selected={i.key === tab}
            aria-controls={`panel-${i.key}`}
            tabIndex={i.key === tab ? 0 : -1}
            className={i.key === tab ? "is-active" : ""}
            onClick={() => setTab(i.key)}
          >
            {i.label}
          </button>
        ))}
      </div>
      <div className="panel" role="tabpanel" id={`panel-${current.key}`} aria-labelledby={`tab-${current.key}`}>
        {current.blocks.map((block, n) => <Command key={block} text={block} index={n + 1} />)}
        <p className="small">{current.note}</p>
        <dl className="then">
          {current.then.map(([hosts, text]) => (
            <div key={hosts}>
              <dt>Then, in {hosts}</dt>
              <dd><code>{text}</code></dd>
            </div>
          ))}
        </dl>
        <p className="small">
          {current.tested} Invocation per host:{" "}
          <a href={`${BLOB}skills/oldhand/references/hosts.md`}>hosts.md</a>.
        </p>
      </div>
    </div>
  );
}

// The ten stages as a stack of plates in 3D, contract at the bottom. The
// plate whose row is hovered in the list below lifts out of the stack.
function Stack({ active }) {
  return (
    <div className="stack" aria-hidden="true">
      <div className="stack-scene">
        {stages.map(([name], i) => (
          <div
            key={name}
            className={`plate${i === active ? " is-active" : ""}${name === "ship" ? " is-ship" : ""}`}
            style={{ "--i": i }}
          >
            <span className="plate-n">{String(i + 1).padStart(2, "0")}</span>
            <span className="plate-name">{name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// A field of dots on a slow 3D wave behind the hero, drawn on a canvas in
// perspective. One still frame when the reader asks for less motion; it
// stops drawing while it is off screen.
function DotField() {
  const ref = useRef(null);
  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas.getContext("2d");
    const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const cols = 64;
    const rows = 26;
    let w = 0;
    let h = 0;
    let color = "0,0,0";
    let frame = 0;
    let visible = true;

    function resize() {
      const dpr = Math.min(devicePixelRatio || 1, 2);
      w = canvas.clientWidth;
      h = canvas.clientHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const rgb = getComputedStyle(canvas).color.match(/\d+/g) || [0, 0, 0];
      color = rgb.slice(0, 3).join(",");
    }

    function draw(t) {
      ctx.clearRect(0, 0, w, h);
      const focal = h * 1.1;
      const horizon = h * 0.02;
      for (let r = 0; r < rows; r++) {
        // rows run from far (r = 0) to near (r = rows - 1)
        const z = 2.6 - (r / (rows - 1)) * 2.2;
        for (let c = 0; c < cols; c++) {
          const x = (c / (cols - 1) - 0.5) * 6;
          const y = Math.sin(x * 1.3 + t * 0.6) * 0.18 + Math.cos(z * 2.2 - t * 0.8) * 0.16;
          const scale = focal / (z + 0.6);
          const sx = w / 2 + x * scale * 0.55;
          const sy = horizon + (0.9 - y) * scale * 0.42;
          if (sx < -4 || sx > w + 4 || sy > h + 4) continue;
          const near = 1 - z / 2.6;
          ctx.fillStyle = `rgba(${color},${(0.08 + near * 0.32 + y * 0.4).toFixed(3)})`;
          ctx.beginPath();
          ctx.arc(sx, sy, 0.6 + near * 1.5, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    }

    function loop(now) {
      frame = 0;
      draw(now / 1000);
      if (visible) frame = requestAnimationFrame(loop);
    }

    resize();
    draw(0);
    const observer = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (visible && !still && !frame) frame = requestAnimationFrame(loop);
    });
    observer.observe(canvas);
    const onResize = () => {
      resize();
      if (still) draw(0);
    };
    addEventListener("resize", onResize);
    const scheme = matchMedia("(prefers-color-scheme: dark)");
    scheme.addEventListener("change", onResize);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      removeEventListener("resize", onResize);
      scheme.removeEventListener("change", onResize);
    };
  }, []);
  return <canvas className="dots" ref={ref} aria-hidden="true" />;
}

// Tilts the run card back in 3D and stands it up as it scrolls into view;
// the pointer adds a small lean. Off when the reader asks for less motion.
function useTilt(ref) {
  useEffect(() => {
    const el = ref.current;
    if (!el || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let px = 0;
    let py = 0;
    let frame = 0;
    const paint = () => {
      frame = 0;
      const box = el.getBoundingClientRect();
      const progress = Math.min(1, Math.max(0, (innerHeight - box.top) / (innerHeight * 0.75)));
      el.style.setProperty("--rx", `${(1 - progress) * 22 + py * -4}deg`);
      el.style.setProperty("--ry", `${px * 5}deg`);
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(paint);
    };
    const move = (event) => {
      const box = el.getBoundingClientRect();
      px = (event.clientX - box.left) / box.width - 0.5;
      py = (event.clientY - box.top) / box.height - 0.5;
      schedule();
    };
    const leave = () => {
      px = 0;
      py = 0;
      schedule();
    };
    paint();
    addEventListener("scroll", schedule, { passive: true });
    addEventListener("resize", schedule);
    el.addEventListener("pointermove", move);
    el.addEventListener("pointerleave", leave);
    return () => {
      cancelAnimationFrame(frame);
      removeEventListener("scroll", schedule);
      removeEventListener("resize", schedule);
      el.removeEventListener("pointermove", move);
      el.removeEventListener("pointerleave", leave);
    };
  }, [ref]);
}

export function App() {
  const [analytics, setAnalytics] = useState(readAnalyticsChoice);
  const [active, setActive] = useState(-1);
  const shotRef = useRef(null);
  useTilt(shotRef);
  useEffect(() => {
    applyAnalyticsChoice(analytics);
  }, [analytics]);

  function toggleAnalytics() {
    const next = analytics === "granted" ? "denied" : "granted";
    saveAnalyticsChoice(next);
    setAnalytics(next);
  }

  return (
    <>
      <header className="top">
        <a className="wordmark" href="#top"><Mark /> oldhand</a>
        <nav aria-label="Sections">
          <a href="#how">How it works</a>
          <a href="#example">Example</a>
          <a href="#benchmark">Benchmark</a>
          <a href="#install">Install</a>
          <a href={REPO}>GitHub</a>
        </nav>
      </header>

      <main id="top">
        <section className="hero">
          <DotField />
          <p className="eyebrow">v{data.version} · MIT · eleven agent skills</p>
          <h1>Make your coding agent prove it is done.</h1>
          <p className="sub">
            For Claude Code, Codex, Cursor, Copilot, Gemini CLI and any agent that reads{" "}
            <code>SKILL.md</code>. One request runs through ten stages, and a small script reads the
            recorded evidence and prints the verdict, so the model can't declare itself done.
          </p>
          <Command text={NPX} index={1} />
          <p className="alt">
            Then type <code>/oldhand</code> and describe the work, or <code>/oldhand --lean</code> for
            one agent. Also as a{" "}
            <a href="#install">Claude Code or Codex plugin</a>.
          </p>
        </section>

        <section className="shot" aria-labelledby="shot-title" ref={shotRef}>
          <div className="card">
            <div className="card-head">
              <span id="shot-title">One run, from its report</span>
              <a href={REPORT}>report.md</a>
            </div>
            <p className="prompt">
              <span className="clamp">/oldhand {data.asked}</span>
            </p>
            <ol className="run">
              {run.map(([k, v, d]) => (
                <li key={k}>
                  <span className="k">{k}</span>
                  <span className="v">{v}</span>
                  <span className="d">{inline(d)}</span>
                </li>
              ))}
              <li className="verdict">
                <span className="k">verdict</span>
                <span className="v">{verdictWord}</span>
                <span className="d">{data.computed}</span>
              </li>
            </ol>
          </div>
        </section>

        <ul className="stats" aria-label="Numbers from the example run">
          <li><b>{criteriaIds.length}</b><span>criteria, each proved end to end</span></li>
          <li><b>2</b><span>root causes; the request <a href={`${BLOB}examples/csv-import-dupes/oldhand/rca.md`}>assumed one</a></span></li>
          <li><b>{data.findings.rows.length}</b><span>review finding, fixed before the verdict</span></li>
          <li><b>{data.qaScore}</b><span>QA scenarios through the real CLI</span></li>
        </ul>

        <section id="how">
          <h2>How it works</h2>
          <p>
            The conductor, <a href={`${BLOB}skills/oldhand/SKILL.md`}>oldhand</a>, routes one request
            through ten stage skills in order. <code>rca</code> runs only for bugs,{" "}
            <code>research</code> only when something new is built. Each stage writes its file into{" "}
            <code>.oldhand/&lt;task&gt;/</code> and can run alone.
          </p>
          <Stack active={active} />
          <ol className="stages" onMouseLeave={() => setActive(-1)}>
            {stages.map(([name, text], i) => (
              <li key={name} onMouseEnter={() => setActive(i)} onFocus={() => setActive(i)}>
                <span className="n">{String(i + 1).padStart(2, "0")}</span>
                <a href={`${BLOB}skills/oldhand-${name}/SKILL.md`}>{name}</a>
                <span className="t">{text}</span>
              </li>
            ))}
          </ol>
          <ul className="tools" aria-label="The three scripts">
            {tools.map(([name, path, text]) => (
              <li key={name}><a href={BLOB + path}>{name}</a> {text}</li>
            ))}
          </ul>
        </section>

        <section id="example">
          <h2>Example run</h2>
          <p>
            The example is a seeded bug in a small Python importer. A transient write failure plus a
            retry stored a CSV batch twice. The project and the task folder the pack wrote are in{" "}
            <a href={EXAMPLE_DIR}>examples/csv-import-dupes</a>; the table is read from its{" "}
            <a href={REPORT}>report.md</a> at build time.
          </p>
          <div className="scroll" tabIndex={0}>
            <table className="ledger">
              <thead>
                <tr><th>Criterion</th><th>Proof</th><th>Status</th><th>By</th></tr>
              </thead>
              <tbody>
                {data.criteria.rows.map(([id, outcome, proof, status, by]) => (
                  <tr key={id}>
                    <td><b>{id}</b><span className="outcome">{inline(outcome)}</span></td>
                    <td>{proof}</td>
                    <td className={`st st-${status}`}>{status}</td>
                    <td>{by}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="small">
            {data.verdict}: {criteriaPassed} of {criteriaIds.length} criteria pass on the current tree.{" "}
            {data.computed}
          </p>
          <details>
            <summary>Review findings, root cause and what was not verified</summary>
            <h3>Review findings</h3>
            <Table data={data.findings} />
            <h3>Root cause</h3>
            <p>{inline(data.rootCause || "")}</p>
            <h3>Not verified</h3>
            <ul>{data.notVerified.map((item, i) => <li key={i}>{inline(item)}</li>)}</ul>
          </details>
        </section>

        <section id="benchmark">
          <h2>Benchmark</h2>
          <p>
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
                <span role="cell" className="bench-arm">{a.key === "plain" ? a.label : <code>{a.label}</code>}</span>
                <span role="cell" data-label="Passed"><b>{a.passed}</b> of {a.runs}</span>
                <span role="cell" data-label="False DONE" className={a.falseDone ? "bench-bad" : ""}><b>{a.falseDone}</b></span>
                <span role="cell" className="bench-cost">
                  <span className="bench-bar" aria-hidden="true"><i style={{ width: `${(a.tokens / maxTokens) * 100}%` }} /></span>
                  <span>
                    {Math.floor(a.tokens).toLocaleString("en-US")}, ${a.cost.toFixed(2)}
                    {a.key !== "plain" && plainArm ? `, ${(a.cost / plainArm.cost).toFixed(1)}x` : ""}
                  </span>
                </span>
              </div>
            ))}
          </div>
          <p className="small">
            Medians per run. Cost at API prices as Claude Code reports it: ${bench.totalCost.toFixed(2)} for
            all {bench.runs} runs, {benchDate}, model alias <code>{benchModel}</code>.
          </p>
          {bench.falseDone.map((f) => (
            <p key={f.task + f.arm}>
              The false DONE ({f.arm} agent, <code>{f.task}</code>): it tested its change by writing its
              own fixture over the project's <code>config.json</code>, deleted it, shipped a program that
              crashes, and reported done. Both Oldhand runs of that task passed.
            </p>
          ))}
          <ul className="plain">
            <li>On small, clearly specified fixes the model is already good, and Oldhand costs several times as much. Use <code>--lean</code> or plain prompting for small, low-risk changes.</li>
            <li>One run per task and route is too few to measure a failure rate. It does measure cost, and it caught one real case of the failure Oldhand is built for.</li>
            <li>Every task was small, so <code>/oldhand</code> chose the lean route each time, and the full chain with review and QA sub-agents hasn't been measured yet.</li>
          </ul>
          <p>
            Tasks, method, every run and how to re-run it:{" "}
            <a href={`${BLOB}bench/README.md`}>bench/README.md</a>.
          </p>
        </section>

        <section id="install">
          <h2>Install</h2>
          <InstallSwitcher />
        </section>

        <section id="stops">
          <h2>What it will not do</h2>
          <p>
            The hard stops, as written at the top of{" "}
            <a href={`${BLOB}skills/oldhand/SKILL.md`}>the conductor skill</a>. {data.hardStopsIntro}
          </p>
          {/* one span per item: in a grid, a bare <code> child would take the number column */}
          <ol className="stops">{data.hardStops.map((item, i) => <li key={i}><span>{inline(item)}</span></li>)}</ol>
        </section>

        <section id="models">
          <h2>Models</h2>
          <p>
            The skills name roles, and one dated file maps them to models. The lead owns the contract,
            the review chair, the final check and the release decision. Workers implement,
            investigate, review and drive QA. Scouts sweep files, read logs and run read-only checks.{" "}
            <a href={`${BLOB}skills/oldhand/references/orchestration.md`}>orchestration.md</a> has the
            current models ({data.modelsDate}).
          </p>
          <Table data={data.models} />
        </section>

        <section id="scope">
          <h2>Limits</h2>
          <ul className="plain">
            <li>It is instructions plus three small scripts, so an agent can still ignore it. The ledger only refuses to print VERIFIED without evidence on the current tree.</li>
            <li>It costs turns and tokens. Review lenses and QA scenarios are sub-agents; the conductor tells you the count before spawning more than ten.</li>
            <li>Browser and desktop QA need a browser or computer-use tool on your host. Without one, UI scenarios are reported as blocked, never as passed.</li>
            <li>Skip it for typos, lookups and one-line edits. The skill says so itself.</li>
            <li>The example ran in a host with no sub-agent tool, so its reviews and QA were run by one agent in turn. Its report says so.</li>
          </ul>
        </section>

        <section id="skill">
          <h2>The skill</h2>
          <details>
            <summary>
              The conductor, <code>skills/oldhand/SKILL.md</code>: {skillLines} lines, imported when this page was built
            </summary>
            <div className="skill-actions">
              <CopyButton value={skillText} label="Copy the whole SKILL.md" text="Copy raw" />
              <a href={`${BLOB}skills/oldhand/SKILL.md`}>View on GitHub</a>
            </div>
            <pre className="skill" tabIndex={0} aria-label="SKILL.md source">{skillText}</pre>
          </details>
        </section>
      </main>

      <footer>
        <span>oldhand v{data.version} · MIT · Berwin Singh</span>
        <nav aria-label="Project links">
          <a href={REPO}>GitHub</a>
          <a href={`${REPO}/issues`}>Issues</a>
          <a href={`${REPO}/discussions`}>Discussions</a>
          <a href={`${BLOB}SECURITY.md`}>Security</a>
        </nav>
        <p className="analytics">
          {analytics === "granted" ? "Google Analytics is on." : "Google Analytics is off; nothing is sent."}{" "}
          <button type="button" className="link" onClick={toggleAnalytics}>
            {analytics === "granted" ? "Turn it off" : "Turn on Google Analytics"}
          </button>
          {" · "}
          <a href="https://policies.google.com/technologies/partner-sites">How Google uses data</a>
        </p>
      </footer>
    </>
  );
}
