import { useEffect, useState } from "react";
import skillText from "../../skills/oldhand/SKILL.md?raw";
import reportText from "../../examples/csv-import-dupes/oldhand/report.md?raw";
import orchestrationText from "../../skills/oldhand/references/orchestration.md?raw";
import plugin from "../../.claude-plugin/plugin.json";
import { applyAnalyticsChoice, readAnalyticsChoice, saveAnalyticsChoice } from "./analytics.js";
import { changeAFile, rerunChecks, toggleCheck, verdict } from "./ledger.js";
import { pageData } from "./slices.js";

const REPO = "https://github.com/berwinsingh/oldhand";
const BLOB = `${REPO}/blob/main/`;
const data = pageData({ skill: skillText, report: reportText, orchestration: orchestrationText, plugin });

// Short names for the example run's criteria; the full wording is in its report.md.
const SHORT = {
  AC1: "A retried batch is stored once",
  AC2: "Messy CSV and TSV files are stored once",
  R1: "A clean import behaves as before",
  R2: "A dry run writes nothing",
  R3: "The command keeps its flags",
  R4: "A bad row still stops the import",
};

const exampleRows = (data.criteria?.rows || []).map(([id, outcome, proof, status, by]) => ({
  id,
  label: SHORT[id] || outcome.split(/[:(]/)[0].slice(0, 60),
  proof,
  status: status === "pass" || status === "fail" ? status : null,
  fresh: true,
  lead: by.startsWith("lead:"),
}));

// Run against GitHub main in clean home folders on this date before being listed here.
const TESTED = "2026-10-21";
const routes = [
  {
    id: "any",
    name: "Any agent",
    who: "Claude Code, Codex, Cursor, GitHub Copilot, Gemini CLI, OpenCode, and other agents that read ~/.agents/skills",
    install: ["npx skills add berwinsingh/oldhand --skill '*' -g"],
    update: ["npx skills update -g"],
    tested: "skills 1.7.2",
  },
  {
    id: "claude",
    name: "Claude Code plugin",
    who: "Claude Code only; stages appear as /oldhand:oldhand-qa and so on",
    install: ["claude plugin marketplace add berwinsingh/oldhand\nclaude plugin install oldhand@oldhand"],
    update: ["claude plugin marketplace update oldhand\nclaude plugin update oldhand@oldhand"],
    tested: "Claude Code 2.1.274",
  },
  {
    id: "codex",
    name: "Codex plugin",
    who: "Codex only; stages appear as $oldhand-qa and so on",
    install: ["codex plugin marketplace add berwinsingh/oldhand\ncodex plugin add oldhand@oldhand"],
    update: ["codex plugin marketplace upgrade oldhand\ncodex plugin add oldhand@oldhand"],
    tested: "Codex CLI 0.146.0",
  },
  {
    id: "git",
    name: "Git clone",
    who: "any agent; links the skills into ~/.agents/skills and ~/.claude/skills",
    install: [
      'git clone https://github.com/berwinsingh/oldhand ~/.oldhand\nmkdir -p ~/.agents/skills ~/.claude/skills\nfor s in ~/.oldhand/skills/*; do ln -sfn "$s" ~/.agents/skills/; ln -sfn "$s" ~/.claude/skills/; done',
    ],
    update: ["git -C ~/.oldhand pull"],
    tested: "git 2.55.0",
  },
];

const invocations = [
  ["Claude Code (plugin)", "/oldhand:oldhand Fix DOCQ-123 and prove it end to end"],
  ["Claude Code (skills folder), Cursor, Copilot, Kiro, Antigravity", "/oldhand Fix DOCQ-123 and prove it end to end"],
  ["Codex", "$oldhand Fix DOCQ-123 and prove it end to end"],
  ["Gemini CLI, OpenCode, Amp, Goose", "Use the oldhand skill to fix DOCQ-123 and prove it end to end"],
];

const stages = [
  ["oldhand", "Routes the request through the stages below, keeps the ledger, and makes the release call from the verdict.", "nothing of its own"],
  ["oldhand-contract", "Turns the ticket or prompt, with its assumptions and changed requirements, into numbered acceptance and regression criteria.", "contract.md, ledger.json"],
  ["oldhand-trace", "Follows the real path from entry point to rendered result, and finds every caller of what will change.", "trace.md"],
  ["oldhand-rca", "For bugs: finds the root cause from evidence, then has read-only agents try to break it.", "rca.md"],
  ["oldhand-research", "Before anything new: the codebase, the standard library, installed packages, then open source behind a licence check.", "research.md"],
  ["oldhand-plan", "The smallest complete change, with blast radius, rollback and a budget for live runs.", "plan.md"],
  ["oldhand-build", "Makes the change and one focused test, then breaks the fix on purpose to prove the test catches it.", "build.md"],
  ["oldhand-review", "A panel of read-only reviewers, one lens each; every finding has to survive an attempt to refute it.", "review.md, review/"],
  ["oldhand-qa", "One agent per scenario drives the real app and brings back evidence; the lead re-runs the key one.", "qa/"],
  ["oldhand-ship", "Runs ledger.py for the verdict, writes the report, and publishes only what you authorised.", "report.md"],
  ["oldhand-learn", "Writes down what the next session would otherwise have to rediscover.", "learned.md"],
];

function sentence(parts) {
  const text = parts.join("; ");
  return text.charAt(0).toUpperCase() + text.slice(1) + ".";
}

function inline(text) {
  return text.split(/(`[^`]*`)/g).map((part, i) =>
    part.startsWith("`") ? <code key={i}>{part.slice(1, -1)}</code> : part,
  );
}

function CopyButton({ value, label, text = "Copy" }) {
  const [state, setState] = useState("");
  async function copy(event) {
    const button = event.currentTarget;
    let ok = false;
    try {
      await navigator.clipboard.writeText(value);
      ok = true;
    } catch {
      const area = document.createElement("textarea");
      area.value = value;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      ok = document.execCommand("copy");
      area.remove();
      button.focus();
    }
    setState(ok ? "Copied" : "Copy failed: select the text");
    window.setTimeout(() => setState(""), 1800);
  }
  return (
    <span className="copy">
      <button type="button" onClick={copy} aria-label={label}>{text}</button>
      <span role="status" className="copy-status">{state}</span>
    </span>
  );
}

function Command({ text, label }) {
  return (
    <div className="command">
      <pre tabIndex={0}><code>{text}</code></pre>
      <CopyButton value={text} label={label} />
    </div>
  );
}

function Ledger() {
  const [rows, setRows] = useState(exampleRows);
  const v = verdict(rows);
  const settled = v.word === "VERIFIED";
  return (
    <figure className="ledger" aria-labelledby="ledger-title">
      <figcaption id="ledger-title">
        The example run's ledger. <a href={`${REPO}/tree/main/examples/csv-import-dupes`}>See the run</a>
      </figcaption>
      <table>
        <thead>
          <tr><th scope="col">Criterion</th><th scope="col">By</th><th scope="col">Check</th></tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <th scope="row"><span className="id">{r.id}</span> {r.label}</th>
              <td>{r.lead ? "the lead" : "a QA agent"}</td>
              <td>
                <button
                  type="button"
                  className={`check ${r.fresh ? r.status : "stale"}`}
                  onClick={() => setRows(toggleCheck(rows, r.id))}
                  aria-label={`${r.id}: ${r.fresh ? r.status : "stale"}. Record a ${r.status === "pass" ? "fail" : "pass"} instead.`}
                >
                  {r.fresh ? r.status : "stale"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className={settled ? "total in-black" : "total in-red"}>
            <th scope="row" colSpan={2}>Verdict</th>
            <td aria-live="polite"><strong>{v.word}</strong></td>
          </tr>
        </tfoot>
      </table>
      <p className="reasons">{sentence(v.reasons)}</p>
      <div className="actions">
        <button type="button" onClick={() => setRows(changeAFile(rows))}>Change a file</button>
        <button type="button" onClick={() => setRows(rerunChecks(rows))}>Re-run the checks</button>
      </div>
      <p className="ledger-note">
        Change a file, re-run the checks, or click a check to fail it. This is the rule{" "}
        <a href={`${BLOB}skills/oldhand/scripts/ledger.py`}>ledger.py</a> applies, simplified, on the
        example run's six criteria.
      </p>
    </figure>
  );
}

function Table({ data: tbl, label }) {
  if (!tbl) return null;
  return (
    <div className="scroll" tabIndex={0} role="region" aria-label={label}>
      <table className="ruled">
        <thead>
          <tr>{tbl.header.map((cell) => <th key={cell} scope="col">{cell}</th>)}</tr>
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

export function App() {
  const [analytics, setAnalytics] = useState(readAnalyticsChoice);
  useEffect(() => applyAnalyticsChoice(analytics), [analytics]);
  useEffect(() => {
    // React renders after the browser's own jump to #section, and the web fonts
    // reflow the page once more when they arrive, so scroll now and again then.
    const target = window.location.hash && document.getElementById(window.location.hash.slice(1));
    if (!target) return;
    target.scrollIntoView();
    document.fonts?.ready.then(() => target.scrollIntoView());
  }, []);

  function toggleAnalytics() {
    const next = analytics === "granted" ? "denied" : "granted";
    saveAnalyticsChoice(next);
    setAnalytics(next);
  }

  return (
    <>
      <header className="top">
        <a className="wordmark" href="#top">oldhand</a>
        <span className="meta">version {data.version}, MIT licence</span>
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
          <div className="hero-text">
            <h1>Your agent says it is done. Oldhand makes it prove it.</h1>
            <p className="lede">
              Eleven agent skills for Claude Code, Codex, Cursor, Copilot, Gemini CLI and any agent that
              reads <code>SKILL.md</code>. Your agent reads the whole request, follows the real code
              path and makes the smallest change. Other agents review it and test it in the running
              app. Then a small script, not the model, decides whether the work is done.
            </p>
            <Command text={routes[0].install[0]} label="Copy the install command" />
            <p className="hero-after">
              On Claude Code or Codex you can <a href="#install">install it as a plugin</a> instead.
              Then type <code>/oldhand</code> (or <code>$oldhand</code> in Codex) and describe the work.
            </p>
          </div>
          <Ledger />
        </section>

        <section id="how">
          <h2>How it works</h2>
          <p>
            A request runs through these stages in order. <code>oldhand-rca</code> runs only for bugs and{" "}
            <code>oldhand-research</code> only when something new is added. Each stage is its own skill,
            writes its file into <code>.oldhand/&lt;task&gt;/</code> in your project, and can be run alone.
          </p>
          <div className="scroll" tabIndex={0} role="region" aria-label="The stages">
            <table className="ruled stages">
              <thead>
                <tr><th scope="col">Stage</th><th scope="col">What it does</th><th scope="col">What it leaves</th></tr>
              </thead>
              <tbody>
                {stages.map(([name, does, leaves]) => (
                  <tr key={name}>
                    <th scope="row"><a href={`${BLOB}skills/${name}/SKILL.md`}>{name}</a></th>
                    <td>{does}</td>
                    <td>{leaves}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p>
            Three standard-library Python scripts keep it honest.{" "}
            <a href={`${BLOB}skills/oldhand/scripts/ledger.py`}>ledger.py</a> stamps every check with the
            exact state of your code and computes the verdict.{" "}
            <a href={`${BLOB}skills/oldhand-qa/scripts/qa.py`}>qa.py</a> writes one brief per test scenario
            and tallies the results.{" "}
            <a href={`${BLOB}skills/oldhand-build/scripts/mutate.py`}>mutate.py</a> breaks the fix on
            purpose to prove a test catches it.
          </p>
        </section>

        <section id="stops">
          <h2>What it will not do</h2>
          <p>
            These rules sit at the top of <a href={`${BLOB}skills/oldhand/SKILL.md`}>the conductor
            skill</a> and hold for every stage and every agent it starts. {data.hardStopsIntro}
          </p>
          <ol className="stops">{data.hardStops.map((item, i) => <li key={i}>{inline(item)}</li>)}</ol>
        </section>

        <section id="example">
          <h2>Example run</h2>
          <p>
            A small Python importer with a planted bug: a write failure followed by a retry stored a CSV
            batch twice. The prompt is in <a href={`${BLOB}examples/README.md`}>examples/README.md</a>,
            and everything the pack wrote is in{" "}
            <a href={`${REPO}/tree/main/examples/csv-import-dupes`}>examples/csv-import-dupes</a>. What
            follows is read from its <code>report.md</code> when this page is built.
          </p>
          {data.verdict && <p className="verdict">{data.verdict}</p>}
          <Table data={data.criteria} label="The example run's criteria" />
          <h3>Root cause</h3>
          <p>{inline(data.rootCause || "")}</p>
          <h3>What the run could not verify</h3>
          <ul>{data.notVerified.map((item, i) => <li key={i}>{inline(item)}</li>)}</ul>
          {data.computed && <p className="computed">{data.computed}</p>}
        </section>

        <section id="install">
          <h2>Install</h2>
          <p>
            Install the whole pack, all eleven skills, with one of these, then start a new session. Use
            one route per agent; a plugin and a skills-folder copy of the same pack show up twice. Each
            command below was run against GitHub in a clean home folder on {TESTED}.
          </p>
          {routes.map((r) => (
            <div className="route" key={r.id}>
              <h3>{r.name}</h3>
              <p className="route-who">For {r.who}. Tested with {r.tested}.</p>
              {r.install.map((c) => <Command key={c} text={c} label={`Copy the ${r.name} install commands`} />)}
              <p className="route-step">To update it later:</p>
              {r.update.map((c) => <Command key={c} text={c} label={`Copy the ${r.name} update commands`} />)}
            </div>
          ))}
          <h3>Then describe the work</h3>
          <div className="scroll" tabIndex={0} role="region" aria-label="How to start it on each agent">
            <table className="ruled">
              <thead><tr><th scope="col">Agent</th><th scope="col">Type</th></tr></thead>
              <tbody>
                {invocations.map(([agent, text]) => (
                  <tr key={agent}><td>{agent}</td><td><code>{text}</code></td></tr>
                ))}
              </tbody>
            </table>
          </div>
          <p>
            The scripts need Python 3.8 or newer. Per-agent details and fallbacks are in{" "}
            <a href={`${BLOB}skills/oldhand/references/hosts.md`}>hosts.md</a>.
          </p>
        </section>

        <section id="skill">
          <h2>The skill</h2>
          <p>
            The conductor, <code>skills/oldhand/SKILL.md</code>, exactly as it is in the repository when
            this page is built. The ten stage skills are linked under How it works.
          </p>
          <div className="skill-actions">
            <CopyButton value={skillText} label="Copy the whole SKILL.md" text="Copy the file" />
            <a href={`${BLOB}skills/oldhand/SKILL.md`}>Open it on GitHub</a>
          </div>
          <pre className="skill" tabIndex={0} aria-label="SKILL.md">{skillText}</pre>
        </section>

        <section id="models">
          <h2>Models</h2>
          <p>
            The skills name roles, not models. The lead writes the contract, chairs the review, runs the
            final check and makes the release call. Workers implement, review and drive tests. Scouts
            search files and run read-only checks. One dated file,{" "}
            <a href={`${BLOB}skills/oldhand/references/orchestration.md`}>orchestration.md</a>, maps the
            roles to models; this table is read from it ({data.modelsDate}).
          </p>
          <Table data={data.models} label="Models per role and agent" />
          <p>When a named model is missing, the rule is: {data.substitutionRule}</p>
        </section>

        <section id="limits">
          <h2>What to expect</h2>
          <ul>
            <li>
              It is instructions plus three small scripts, not a runtime. An agent can still ignore it.
              The ledger only refuses to print VERIFIED without evidence on the current code.
            </li>
            <li>
              It costs turns and tokens: reviews and tests run as separate agents. The conductor tells
              you the count before it starts more than ten.
            </li>
            <li>
              Browser and desktop tests need a browser or computer-use tool in your agent. Without one,
              those tests are reported as blocked, never as passed.
            </li>
            <li>It skips itself for typos, lookups and one-line edits.</li>
            <li>
              The example above ran without sub-agents, so one agent played every reviewer and tester in
              turn, and its report says so.{" "}
              <a href={`${REPO}/tree/main/examples/site-rebuild`}>examples/site-rebuild</a> is a run with
              real sub-agents; it shipped the previous version of this page.
            </li>
          </ul>
        </section>
      </main>

      <footer>
        <p>
          Oldhand {data.version} is MIT licensed and made by Berwin Singh. This page was designed with
          Anthropic's <a href="https://github.com/anthropics/skills/tree/main/skills/frontend-design">frontend-design</a> skill.
        </p>
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
          </button>{" "}
          (<a href="https://policies.google.com/technologies/partner-sites">how Google uses data</a>)
        </p>
      </footer>
    </>
  );
}
