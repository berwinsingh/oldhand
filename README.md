# Oldhand

**Give your coding agent a definition of done.**

[Website](https://berwinsingh.github.io/oldhand/)

Oldhand is a pack of 11 Agent Skills for any coding agent that reads
`SKILL.md` files: Claude Code, Codex, GitHub Copilot, Cursor, Gemini CLI and
Antigravity, OpenCode and more. A conductor (`oldhand`) routes a Jira, Asana,
monday.com, Linear or GitHub issue, a document or a plain prompt through ten
stages: contract, trace, rca, research, plan, build, review, qa, ship and learn.
Each stage does one job and writes to a shared task folder, and small scripts,
not the model, decide when the work is verified.

## Install

Install the whole pack. Every stage calls `skills/oldhand/scripts/ledger.py`,
so a single stage installed on its own stops and asks for the rest. Pick one
install method per host: a plugin plus a skill-folder install shows twice.

| host | install |
| --- | --- |
| any agent | `npx skills add berwinsingh/oldhand --skill '*' -g` (all eleven skills; add `-a cursor`, `-a codex` and so on to skip the picker) |
| Claude Code plugin | `/plugin marketplace add berwinsingh/oldhand`, then `/plugin install oldhand@oldhand` (two separate prompts) |
| Codex plugin | `codex plugin marketplace add berwinsingh/oldhand`, then `codex plugin add oldhand@oldhand` |
| git clone | see below |

```sh
git clone https://github.com/berwinsingh/oldhand ~/.oldhand
mkdir -p ~/.agents/skills ~/.claude/skills
for s in ~/.oldhand/skills/*; do ln -sfn "$s" ~/.agents/skills/; ln -sfn "$s" ~/.claude/skills/; done
```

`~/.agents/skills` is read by Codex, Cursor, Copilot, Gemini CLI, OpenCode,
Amp, Roo, Goose, Droid and Junie; `~/.claude/skills` by Claude Code. An
installer that takes one skill at a time must be given all eleven.

Start a new session after installing. Then invoke it:

| host | invoke |
| --- | --- |
| Claude Code plugin | `/oldhand:oldhand Implement DOCQ-123` (a stage: `/oldhand:oldhand-qa`) |
| Claude Code skill folder | `/oldhand Implement DOCQ-123` |
| Codex | `$oldhand Implement DOCQ-123` |
| Cursor, Copilot, Kiro, Cline, Factory Droid, Junie, Antigravity app and `agy` | `/oldhand Implement DOCQ-123` |
| Devin Desktop (was Windsurf) | `@oldhand Implement DOCQ-123` |
| Gemini CLI, OpenCode, Roo Code, Amp, Goose, Antigravity IDE | automatic from the description, or "use the oldhand skill to implement DOCQ-123" |

A stage runs alone the same way: replace `oldhand` with `oldhand-<stage>`.
Per-host details and fallbacks are in
[skills/oldhand/references/hosts.md](skills/oldhand/references/hosts.md). No
tracker integration or MCP server is needed to install.

## Give it the real context

A ticket key is optional, and `implement` is not the only useful instruction.
Include assumptions, decisions, changed requirements, constraints, partial
work, exclusions, relevant files or links, and the proof you expect.

### Claude Code

```text
/oldhand:oldhand Implement DOCQ-123.
Changes since the ticket: support guest users without changing the admin flow.
Assumptions: the current session cookie remains authoritative.
Prove: finish guest signup, reload, and confirm persistence.
```

### ChatGPT Codex

```text
$oldhand No ticket. Fix intermittent CSV imports.
Current behavior: files over 20 MB sometimes create duplicate rows.
Context: retry logic changed last week in src/imports/worker.ts.
Constraints: no schema migration; preserve queued jobs.
Acceptance: one import produces one persisted batch even after a retry.
```

### Plan only with corrected requirements

```text
$oldhand Plan only for ENG-456; do not edit files.
The ticket is stale: use OAuth instead of API keys and assume mobile is out of scope.
State every material assumption and map the plan to observable acceptance checks.
```

Oldhand treats the user's latest explicit context as authoritative, reconciles
it with older ticket text, and asks only when an unresolved choice would be
unsafe or materially change the result.

## What it changes

Without Oldhand, coding agents often:

- start coding from a ticket title before reading its comments or dependencies;
- solve one file while breaking a sibling route or downstream integration;
- invent a new parser, retry loop, component, or framework that already exists;
- overwrite unrelated work or expand a small fix into a large refactor; and
- stop at unit tests even when the browser flow is broken.

Oldhand makes the agent:

1. establish a work contract from any tracker, document, or plain prompt;
2. trace the actual UI, API, service, persistence, and integration path;
3. compare maintained MIT or Apache-2.0 implementations before inventing one;
4. apply Ponytail's smallest-correct-change discipline;
5. preserve dirty worktrees and unrelated user changes; and
6. keep fixing until the real browser, native, or external path passes.

## Model orchestration

The skills name roles, not models. The lead (the strongest model on the host)
writes the contract, chairs the review, runs the final end-to-end check and
makes the release decision. Workers (the standard tier) take implementation
slices, lens reviews and QA flows; scouts (the fast tier) take sweeps and
read-only checks. A sub-agent's report is evidence, never verification.

The current model for each role on each host, and the substitution rule when
one is missing, are in
[skills/oldhand/references/orchestration.md](skills/oldhand/references/orchestration.md):
the one file to update when model lineups change.

## Integrations

Oldhand works without any of these. Add only the integration that gives the
agent access to the work in front of it.

| Need | Integration | Link |
| --- | --- | --- |
| Minimal implementation | Ponytail | [Repository and install](https://github.com/DietrichGebert/ponytail) |
| Jira / Confluence | Atlassian Rovo MCP | [Documentation](https://developer.atlassian.com/cloud/rovo-mcp/) |
| Asana | Asana MCP | [Documentation](https://developers.asana.com/docs/using-asanas-mcp-server) |
| monday.com | monday MCP | [Documentation](https://developer.monday.com/api-reference/docs/integrate-with-monday-mcp) |
| Linear | Linear MCP | [Documentation](https://linear.app/docs/mcp) |
| GitHub issues and PRs | GitHub MCP server | [Repository](https://github.com/github/github-mcp-server) |
| Current library docs | Context7 MCP | [Repository](https://github.com/upstash/context7) |
| Browser fallback | Playwright MCP | [Repository](https://github.com/microsoft/playwright-mcp) |
| Claude browser QA | Claude in Chrome | [Documentation](https://code.claude.com/docs/en/chrome) |
| Codex browser or native QA | Browser / computer use | [Codex documentation](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan) |

If a connected tracker is unavailable, paste the ticket text or provide an
accessible link. If there is no ticket, write the request normally. Oldhand
derives the smallest observable acceptance criteria and proceeds.

## Examples

[examples/csv-import-dupes](examples/csv-import-dupes) is a real run on a
seeded bug (a transient write failure plus a retry stored a CSV batch twice),
kept exactly as the pack wrote it: contract, trace, two root causes, the
review memo that caught a test gap, nine QA transcripts and the computed
verdict. [examples/site-rebuild](examples/site-rebuild) is the task folder of
the run that shipped the website. [examples/README.md](examples/README.md)
says what to read first and what each run could not verify.

## Verify the package

Repository validation is dependency-free:

```sh
./scripts/smoke-test.sh
claude plugin validate .
```

To test this checkout before publishing with Claude Code:

```sh
claude plugin marketplace add "$PWD"
claude plugin install oldhand@oldhand
```

The Codex marketplace in `.agents/plugins/marketplace.json` installs GitHub
`main`, not this checkout. For Codex, point a throwaway marketplace at the
checkout with a local source:

```sh
m=$(mktemp -d) && mkdir -p "$m/.agents/plugins" && ln -s "$PWD" "$m/oldhand"
cat > "$m/.agents/plugins/marketplace.json" <<'EOF'
{"name": "oldhand-local", "plugins": [{"name": "oldhand",
  "source": {"source": "local", "path": "./oldhand"},
  "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
  "category": "Productivity"}]}
EOF
codex plugin marketplace add "$m"
codex plugin add oldhand@oldhand-local
```

Command discovery proves installation only. A development task is complete
only after Oldhand passes its proportional automated checks and realistic
end-to-end gate.

## Safety

The skill never grants authority by itself. Remote writes, commits, pushes,
pull requests, tracker changes, deployments, migrations, and destructive
actions still require the authority supplied by the user's request. A blocked
end-to-end gate is reported as blocked, never as passed.

## Community

Ask questions and share ideas in [Discussions](https://github.com/berwinsingh/oldhand/discussions). Use [Issues](https://github.com/berwinsingh/oldhand/issues) for reproducible bugs and read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Report vulnerabilities through GitHub's [private reporting form](https://github.com/berwinsingh/oldhand/security/advisories/new).

## License

MIT
