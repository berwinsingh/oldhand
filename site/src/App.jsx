import { useEffect, useState } from "react";
import skillText from "../../skills/oldhand/SKILL.md?raw";
import reportText from "../../examples/csv-import-dupes/oldhand/report.md?raw";
import orchestrationText from "../../skills/oldhand/references/orchestration.md?raw";
import plugin from "../../.claude-plugin/plugin.json";
import { applyAnalyticsChoice, readAnalyticsChoice, saveAnalyticsChoice } from "./analytics.js";
import { pageData } from "./slices.js";

const REPO = "https://github.com/berwinsingh/oldhand";
const BLOB = `${REPO}/blob/main/`;
const TESTED = "2026-10-11";
const EXAMPLE = "Fix DOCQ-123. Prove: guest signup, reload, data persists.";

// Every command below was run on this date in a throwaway home folder, from a
// local checkout of this repository; the GitHub source serves the same files.
const installs = [
  {
    key: "any",
    label: "Any agent",
    blocks: ["npx skills add berwinsingh/oldhand --skill '*' -g"],
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
    label: "Git clone",
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
  ["oldhand", "the conductor: routes the request through the stages, keeps one task folder and a ledger, and decides from the verdict"],
  ["oldhand-contract", "the request, with its assumptions and changed requirements, becomes numbered acceptance and regression criteria, each with the proof it needs"],
  ["oldhand-trace", "the real path hop by hop, from entry point to rendered result, and every caller of what will change"],
  ["oldhand-rca", "evidence-first root cause for bugs; read-only refuters try to break it before it is accepted"],
  ["oldhand-research", "before anything new: the codebase, the standard library, the platform, installed dependencies, then open source behind a licence gate"],
  ["oldhand-plan", "the smallest complete change, with blast radius, rollback, delegation and a budget for live runs"],
  ["oldhand-build", "the Ponytail ladder, one focused regression check, proven by mutation: break the fix and the check must fail"],
  ["oldhand-review", "a board of read-only reviewers, one lens each; the chair refutes every finding before it counts"],
  ["oldhand-qa", "one sub-agent per scenario drives the real app and brings back evidence; the lead re-runs the key one"],
  ["oldhand-ship", "the verdict is computed by a script from the ledger; publication only when the request authorized it"],
  ["oldhand-learn", "the non-obvious lessons go where the project keeps its instructions, so the next session does not relearn them"],
];

const data = pageData({ skill: skillText, report: reportText, orchestration: orchestrationText, plugin });

function inline(text) {
  return text.split(/(`[^`]*`)/g).map((part, i) =>
    part.startsWith("`") ? <code key={i}>{part.slice(1, -1)}</code> : part,
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
            <tr key={r}>{row.map((cell, c) => <td key={c}>{inline(cell)}</td>)}</tr>
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
    <div className="install" id="install">
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
        <p className="note">{current.note}</p>
        <dl className="then">
          {current.then.map(([hosts, text]) => (
            <div key={hosts}>
              <dt>Then, in {hosts}, for example</dt>
              <dd><code>{text}</code></dd>
            </div>
          ))}
        </dl>
        <p className="tested">
          {current.tested} Invocation per host:{" "}
          <a href={`${BLOB}skills/oldhand/references/hosts.md`}>hosts.md</a>.
        </p>
      </div>
    </div>
  );
}

export function App() {
  const [analytics, setAnalytics] = useState(readAnalyticsChoice);
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
        <a className="wordmark" href="#top">oldhand</a>
        <span className="meta">v{data.version} · MIT</span>
        <nav aria-label="Sections">
          <a href="#install">Install</a>
          <a href="#how">How it works</a>
          <a href="#example">Example</a>
          <a href="#skill">The skill</a>
          <a href="#models">Models</a>
          <a href={REPO}>GitHub</a>
        </nav>
      </header>

      <main id="top">
        <section className="hero">
          <h1>A definition of done for coding agents.</h1>
          <p className="lede">
            Oldhand is a pack of eleven agent skills. Your agent reads the whole request, traces
            the real code path, reuses before it writes, changes the minimum, has sub-agents review
            and QA the result in the running app, and{" "}
            <a href={`${BLOB}skills/oldhand/scripts/ledger.py`}>a small script</a>, not the model,
            says when it is done. It works with Claude Code, Codex, Cursor, Copilot, Gemini CLI and
            any other agent that reads <code>SKILL.md</code>.
          </p>
          <InstallSwitcher />
        </section>

        <section id="how">
          <h2>How it works</h2>
          <p>
            One request runs through the stages below in order; <code>rca</code> only for bugs,{" "}
            <code>research</code> only when something new is built. Each stage is its own skill,
            reads what the earlier ones wrote into <code>.oldhand/&lt;task&gt;/</code>, and can run
            alone.
          </p>
          <ol className="stages">
            {stages.map(([name, text]) => (
              <li key={name}>
                <a href={`${BLOB}skills/${name}/SKILL.md`}>{name}</a>
                <span>{text}</span>
              </li>
            ))}
          </ol>
          <p>
            Three standard-library Python tools keep it honest:{" "}
            <a href={`${BLOB}skills/oldhand/scripts/ledger.py`}>ledger.py</a> records every check
            against the exact working tree and computes the verdict,{" "}
            <a href={`${BLOB}skills/oldhand-qa/scripts/qa.py`}>qa.py</a> deals the scenario briefs
            and tallies the results, and{" "}
            <a href={`${BLOB}skills/oldhand-build/scripts/mutate.py`}>mutate.py</a> proves a test
            guards the fix.
          </p>
        </section>

        <section id="stops">
          <h2>What it will not do</h2>
          <p>
            The hard stops, as they appear at the top of{" "}
            <a href={`${BLOB}skills/oldhand/SKILL.md`}>the conductor skill</a>. {data.hardStopsIntro}
          </p>
          <ol>{data.hardStops.map((item, i) => <li key={i}>{inline(item)}</li>)}</ol>
        </section>

        <section id="example">
          <h2>Example run</h2>
          <p>
            A seeded bug in a small Python importer: a transient write failure plus a retry stored a
            CSV batch twice. The prompt is in{" "}
            <a href={`${BLOB}examples/README.md`}>examples/README.md</a>; the project and the task
            folder the pack wrote (without its binary SQLite evidence) are in{" "}
            <a href={`${REPO}/tree/main/examples/csv-import-dupes`}>examples/csv-import-dupes</a>.
            The blocks below are read from its <code>report.md</code> at build time.
          </p>
          {data.verdict && <p className="verdict">{data.verdict}</p>}
          <Table data={data.criteria} />
          <h3>Root cause</h3>
          <p>{inline(data.rootCause || "")}</p>
          <h3>Not verified</h3>
          <ul>{data.notVerified.map((item, i) => <li key={i}>{inline(item)}</li>)}</ul>
          {data.computed && <p className="computed">{data.computed}</p>}
        </section>

        <section id="skill">
          <h2>The skill</h2>
          <p>
            The conductor, <code>skills/oldhand/SKILL.md</code>, imported from the repository when
            this page was built. The ten stage skills are linked above.
          </p>
          <div className="skill-actions">
            <CopyButton value={skillText} label="Copy the whole SKILL.md" text="Copy raw" />
            <a href={`${BLOB}skills/oldhand/SKILL.md`}>View on GitHub</a>
          </div>
          <pre className="skill" tabIndex={0} aria-label="SKILL.md source">{skillText}</pre>
        </section>

        <section id="models">
          <h2>Models</h2>
          <p>
            The skills name roles, not models: the lead owns the contract, the review chair, the
            final check and the release decision; workers implement, investigate, review and drive
            QA; scouts sweep files, read logs and run read-only checks. One dated file,{" "}
            <a href={`${BLOB}skills/oldhand/references/orchestration.md`}>orchestration.md</a>,
            maps the roles to current models; this table is read from it ({data.modelsDate}):
          </p>
          <Table data={data.models} />
          <p>
            If a named model is missing, the agent uses the newest one the host offers in the same
            role, never puts the lead below worker tier, and records the model that actually ran.
          </p>
        </section>

        <section id="limits">
          <h2>Honest scope</h2>
          <ul>
            <li>
              It is instructions plus three small scripts, not a runtime. An agent can still ignore
              it; the ledger only refuses to print VERIFIED without evidence on the current tree.
            </li>
            <li>
              It costs turns and tokens. Review lenses and QA scenarios are sub-agents; the{" "}
              <a href={`${BLOB}skills/oldhand/SKILL.md`}>conductor</a> tells you the count before
              spawning more than ten.
            </li>
            <li>
              Browser and desktop QA need a browser or computer-use tool on your host. Without one,{" "}
              <a href={`${BLOB}skills/oldhand-qa/SKILL.md`}>oldhand-qa</a> reports UI scenarios as
              blocked, never as passed.
            </li>
            <li>Skip it for typos, lookups and one-line edits. The skill says so itself.</li>
            <li>
              The example above ran in a host with no sub-agent tool, so its reviews and QA were run
              by one agent in turn. Its report says so.
            </li>
          </ul>
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
