import { useState } from "react";
import {
  ArrowDown,
  ArrowRight,
  Browser,
  Check,
  CheckCircle,
  ClipboardText,
  Code,
  Copy,
  FileText,
  GitBranch,
  GithubLogo,
  MagnifyingGlass,
  PlugsConnected,
  SealCheck,
  Sparkle,
  Stack,
  TerminalWindow,
  Wrench,
  X,
} from "@phosphor-icons/react";

const installs = {
  claude: [
    "/plugin marketplace add berwinsingh/oldhand",
    "/plugin install oldhand@oldhand",
  ],
  codex: [
    "codex plugin marketplace add berwinsingh/oldhand",
    "codex plugin add oldhand@oldhand",
  ],
};

const failures = [
  {
    title: "Starts before understanding",
    body: "A ticket title becomes a plan. Constraints and linked work get missed.",
    icon: ClipboardText,
  },
  {
    title: "Reinvents solved work",
    body: "No search for existing code, native features, or maintained prior art.",
    icon: Stack,
  },
  {
    title: "Overwrites the codebase",
    body: "A small fix expands into a refactor and unrelated work gets disturbed.",
    icon: GitBranch,
  },
  {
    title: "Stops at unit tests",
    body: "Green checks replace proof that the real browser flow works.",
    icon: Browser,
  },
];

const steps = [
  {
    eyebrow: "01 / INTAKE",
    title: "Understand",
    body: "Read the request, comments, files, dependencies, and acceptance criteria.",
    icon: ClipboardText,
  },
  {
    eyebrow: "02 / TRACE",
    title: "Map the path",
    body: "Follow UI, API, auth, services, persistence, and integrations end to end.",
    icon: GitBranch,
  },
  {
    eyebrow: "03 / PRIOR ART",
    title: "Reuse",
    body: "Study real MIT and Apache-2.0 implementations before inventing.",
    icon: MagnifyingGlass,
  },
  {
    eyebrow: "04 / CHANGE",
    title: "Stay minimal",
    body: "Use Ponytail to land the smallest safe change in the shared fix point.",
    icon: Wrench,
  },
  {
    eyebrow: "05 / INSPECT",
    title: "Prove it",
    body: "Run the real journey in your browser and keep fixing until it passes.",
    icon: SealCheck,
  },
];

const sources = [
  ["Jira issue", "PROJ-1234"],
  ["Asana task", "Launch / improve signup"],
  ["monday.com item", "Fix onboarding flow"],
  ["Linear issue", "ENG-4567"],
  ["GitHub issue", "owner/repo#812"],
  ["Document", "PRD, ADR, runbook"],
  ["Plain prompt", "Make the search faster"],
];

function CopyButton({ value, label = "Copy command" }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = value;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      textarea.remove();
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  return (
    <button className="copy-button" type="button" onClick={copy} aria-label={label}>
      {copied ? <Check size={18} weight="bold" /> : <Copy size={18} />}
      <span aria-live="polite">{copied ? "Copied" : "Copy"}</span>
    </button>
  );
}

function InstallPanel({ compact = false }) {
  const [platform, setPlatform] = useState("claude");

  return (
    <div
      className={`install-panel ${compact ? "install-panel--compact" : ""}`}
      data-testid={compact ? "hero-install-panel" : "final-install-panel"}
    >
      <div className="install-tabs" role="tablist" aria-label="Install platform">
        <button
          type="button"
          className={platform === "claude" ? "is-active" : ""}
          onClick={() => setPlatform("claude")}
          role="tab"
          aria-selected={platform === "claude"}
        >
          Claude Code
        </button>
        <button
          type="button"
          className={platform === "codex" ? "is-active" : ""}
          onClick={() => setPlatform("codex")}
          role="tab"
          aria-selected={platform === "codex"}
        >
          ChatGPT Codex
        </button>
      </div>

      <div className="command-list" role="tabpanel">
        {installs[platform].map((command) => (
          <div className="command-row" key={command}>
            <code>{command}</code>
            <CopyButton value={command} label={`Copy ${command}`} />
          </div>
        ))}
      </div>

      <div className="install-note">
        <CheckCircle size={18} weight="fill" />
        Complete install. Add tracker or browser integrations only when you need them.
      </div>
    </div>
  );
}

export function App() {
  const [selectedSources, setSelectedSources] = useState([0, 6]);
  const asset = (name) => `${import.meta.env.BASE_URL}assets/${name}`;

  function toggleSource(index) {
    setSelectedSources((current) =>
      current.includes(index)
        ? current.filter((item) => item !== index)
        : [...current, index],
    );
  }

  function scrollToInstall() {
    document.querySelector("#install")?.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <main>
      <header className="site-header">
        <a className="brand" href="#top" aria-label="Oldhand home">
          <span>OLDHAND</span>
          <small>/ verified delivery</small>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#process">How it works</a>
          <a href="#orchestration">Models</a>
          <a href="#proof">Proof</a>
          <a href="#install">Install</a>
        </nav>
        <a
          className="header-github"
          href="https://github.com/berwinsingh/oldhand"
          target="_blank"
          rel="noreferrer"
        >
          <GithubLogo size={19} weight="fill" />
          GitHub
        </a>
      </header>

      <section className="hero sheet" id="top">
        <div className="work-order" aria-label="Work order">
          <div>
            <span>WORK ORDER</span>
            <strong>OH-24-0517</strong>
          </div>
          <div>
            <span>STATUS</span>
            <strong>READY TO PROVE</strong>
          </div>
          <div className="work-order-accent">BUILD WITH CONFIDENCE.</div>
        </div>

        <div className="hero-grid">
          <div className="hero-copy">
            <p className="kicker">Development discipline for coding agents</p>
            <h1>From vague request to verified change.</h1>
            <p className="lede">
              Oldhand turns any ticket, document, or prompt into understood,
              researched, minimally implemented, browser-proven work.
            </p>
            <div className="hero-actions">
              <button className="button button--primary" type="button" onClick={scrollToInstall}>
                Install Oldhand
                <ArrowDown size={19} weight="bold" />
              </button>
              <a
                className="button button--secondary"
                href="https://github.com/berwinsingh/oldhand#readme"
                target="_blank"
                rel="noreferrer"
              >
                Read the skill
                <ArrowRight size={19} />
              </a>
            </div>
          </div>

          <div className="stamp-wrap">
            <img
              src={asset("delivered-stamp.png")}
              alt="Delivered: end-to-end proof, signed Oldhand, not just code"
            />
          </div>
        </div>

        <div className="hero-install">
          <div className="section-bar">
            <span>Two commands. Then give it the work.</span>
            <span>NO CLONE · NO COPY · NO CONFIG FILE</span>
          </div>
          <InstallPanel compact />
        </div>
      </section>

      <section className="section shell" aria-labelledby="failures-title">
        <div className="section-heading">
          <p className="kicker">The problem</p>
          <h2 id="failures-title">The handoff is where agents fail.</h2>
          <p>
            Speed is useful. Speed without context, restraint, and proof is just
            faster rework.
          </p>
        </div>
        <div className="failure-grid">
          {failures.map(({ title, body, icon: Icon }, index) => (
            <article className="failure-card" key={title}>
              <div className="failure-index">0{index + 1}</div>
              <Icon size={34} weight="duotone" />
              <h3>{title}</h3>
              <p>{body}</p>
              <X className="failure-x" size={19} weight="bold" />
            </article>
          ))}
        </div>
      </section>

      <section className="section shell" id="process" aria-labelledby="process-title">
        <div className="section-heading section-heading--row">
          <div>
            <p className="kicker">Oldhand inspection process</p>
            <h2 id="process-title">One discipline. Every project.</h2>
          </div>
          <p>Understand first. Reuse what works. Prove the result.</p>
        </div>
        <div className="process-grid">
          {steps.map(({ eyebrow, title, body, icon: Icon }) => (
            <article className="process-step" key={title}>
              <div className="process-icon">
                <Icon size={30} weight="duotone" />
              </div>
              <span>{eyebrow}</span>
              <h3>{title}</h3>
              <p>{body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section shell split-section" id="orchestration">
        <div className="intake-card" data-testid="source-intake">
          <div className="card-title">
            <span>ADAPTABLE SOURCES / INTAKE</span>
            <small>{selectedSources.length} selected</small>
          </div>
          <div className="source-table" role="group" aria-label="Example work sources">
            {sources.map(([source, example], index) => {
              const checked = selectedSources.includes(index);
              return (
                <button
                  type="button"
                  className={checked ? "source-row is-selected" : "source-row"}
                  onClick={() => toggleSource(index)}
                  aria-pressed={checked}
                  key={source}
                >
                  <span className="source-check">{checked && <Check size={15} weight="bold" />}</span>
                  <strong>{source}</strong>
                  <span>{example}</span>
                </button>
              );
            })}
          </div>
          <p className="intake-note">
            No tracker? No problem. A plain prompt is still a valid source of truth.
          </p>
        </div>

        <div className="orchestration-card">
          <div className="card-title">
            <span>ORCHESTRATION CREW</span>
            <small>Final verification returns to the lead</small>
          </div>

          <article className="model-card model-card--orange">
            <div>
              <span>CLAUDE CODE</span>
              <strong>Fable orchestrates</strong>
            </div>
            <p>Routes Haiku, Sonnet, and Opus by complexity, then reviews the integrated result.</p>
            <div className="model-status">
              <span><Check size={15} />Understood</span>
              <span><Check size={15} />Reused</span>
              <span><Check size={15} />Browser verified</span>
            </div>
          </article>

          <article className="model-card model-card--green">
            <div>
              <span>CHATGPT CODEX</span>
              <strong>GPT-5.6 Sol orchestrates</strong>
            </div>
            <p>Routes GPT-5.6 Terra and Luna by complexity, then owns the final proof.</p>
            <div className="model-status">
              <span><Check size={15} />Understood</span>
              <span><Check size={15} />Reused</span>
              <span><Check size={15} />Browser verified</span>
            </div>
          </article>
        </div>
      </section>

      <section className="section shell" id="proof" aria-labelledby="proof-title">
        <div className="section-heading section-heading--row">
          <div>
            <p className="kicker">Browser inspection / proof receipt</p>
            <h2 id="proof-title">Done means observed.</h2>
          </div>
          <div className="status-badge">
            <CheckCircle size={21} weight="fill" />
            Browser verified
          </div>
        </div>

        <div className="proof-card">
          <div className="proof-metadata">
            <dl>
              <div><dt>CHECK ID</dt><dd>OH-24-0517-0912</dd></div>
              <div><dt>URL</dt><dd>/signup</dd></div>
              <div><dt>VIEWPORT</dt><dd>Desktop 1280 × 800</dd></div>
              <div><dt>MODE</dt><dd>Real browser / clean session</dd></div>
            </dl>
            <ol>
              <li>Navigate from the real entry point</li>
              <li>Complete the form with valid data</li>
              <li>Submit and observe the success state</li>
              <li>Reload and verify persisted behavior</li>
            </ol>
            <div className="proof-result">
              <CheckCircle size={26} weight="fill" />
              PASSED
            </div>
          </div>

          <figure className="browser-evidence">
            <div className="browser-bar">
              <span />
              <span />
              <span />
              <code>staging.example.com/signup</code>
            </div>
            <img
              src={asset("browser-proof.png")}
              alt="Successful signup flow shown in a real browser verification capture"
            />
            <figcaption>
              Screenshot captured after the final integrated flow passed.
            </figcaption>
          </figure>
        </div>

        <div className="evidence-strip">
          <span><FileText size={20} />screenshot.png</span>
          <span><TerminalWindow size={20} />console.log</span>
          <span><PlugsConnected size={20} />network.har</span>
          <span><Code size={20} />diff.patch</span>
          <span><ClipboardText size={20} />delivery-notes.md</span>
        </div>
      </section>

      <section className="section shell principles" aria-labelledby="principles-title">
        <div className="section-heading">
          <p className="kicker">Built-in restraint</p>
          <h2 id="principles-title">Less code. More proof.</h2>
        </div>
        <div className="principle-grid">
          <article>
            <MagnifyingGlass size={34} weight="duotone" />
            <span>01</span>
            <h3>Research before inventing</h3>
            <p>
              Compare real, maintained MIT and Apache-2.0 implementations before
              adding a new pattern or dependency.
            </p>
          </article>
          <article>
            <Sparkle size={34} weight="duotone" />
            <span>02</span>
            <h3>Ponytail the change</h3>
            <p>
              Reuse the codebase, standard library, native platform, and installed
              dependencies before writing anything new.
            </p>
          </article>
          <article>
            <SealCheck size={34} weight="duotone" />
            <span>03</span>
            <h3>Keep ownership at the top</h3>
            <p>
              Delegation helps with speed. The orchestrator still integrates,
              verifies, and owns the final answer.
            </p>
          </article>
        </div>
      </section>

      <section className="section install-section" id="install" aria-labelledby="install-title">
        <div className="shell">
          <div className="install-heading">
            <div>
              <p className="kicker">Install Oldhand</p>
              <h2 id="install-title">Two commands. That’s it.</h2>
            </div>
            <p>
              The skill, manifests, model routing, research gates, and browser
              definition of done arrive together.
            </p>
          </div>
          <InstallPanel />
          <div className="install-footer">
            <strong>Give it the work. Get back proof.</strong>
            <a
              href="https://github.com/berwinsingh/oldhand#integrations"
              target="_blank"
              rel="noreferrer"
            >
              Optional integrations and MCPs
              <ArrowRight size={18} />
            </a>
          </div>
        </div>
      </section>

      <footer className="site-footer">
        <div>
          <strong>OLDHAND</strong>
          <span>Development discipline for Claude Code and ChatGPT Codex.</span>
        </div>
        <div>
          <a href="https://github.com/berwinsingh/oldhand" target="_blank" rel="noreferrer">
            GitHub
          </a>
          <a href="https://github.com/berwinsingh/oldhand/blob/main/LICENSE" target="_blank" rel="noreferrer">
            MIT License
          </a>
        </div>
      </footer>
    </main>
  );
}
