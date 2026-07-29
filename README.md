# Oldhand

**Give your coding agent a definition of done.**

[Website](https://berwinsingh.github.io/oldhand/)

Oldhand is one portable development workflow for Claude Code and ChatGPT
Codex. It accepts a Jira, Asana, monday.com, Linear, or GitHub issue—or just a
plain prompt—then makes the agent understand the real flow, research permissive
open-source prior art, implement the smallest safe change with Ponytail, and
verify the result end to end.

## Install

### Claude Code

Run these as two separate prompts inside Claude Code:

```text
/plugin marketplace add berwinsingh/oldhand
/plugin install oldhand@oldhand
```

Then start a new session and use:

```text
/oldhand:oldhand Implement DOCQ-123
```

### ChatGPT Codex / Codex CLI

```sh
codex plugin marketplace add berwinsingh/oldhand
codex plugin add oldhand@oldhand
```

Restart Codex or start a new task, then use:

```text
$oldhand Implement DOCQ-123
```

That is the complete installation. The plugin contains the skill and its
platform manifests. It does not require a tracker integration or MCP server to
install.

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

### Claude Code

Fable is the orchestrator and final verifier. It may delegate bounded work to
Haiku, Sonnet, or Opus according to complexity and risk. Fable reviews the
integrated result and performs the final end-to-end verification through the
user's browser or computer-use tools. If Fable is unavailable, the workflow
uses Opus as the explicit fallback orchestrator.

### ChatGPT Codex

GPT-5.6 Sol is the orchestrator and final verifier. It may delegate bounded work
to GPT-5.6 Terra or GPT-5.6 Luna according to complexity and risk. Sol reviews
the integrated result and performs the final end-to-end verification through
the browser or computer-use tools. If an exact named model is unavailable or
has been superseded, the workflow uses the latest available equivalent and
names the substitution in the plan.

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

## Verify the package

Repository validation is dependency-free:

```sh
./scripts/smoke-test.sh
claude plugin validate .
```

To test the exact local installation flow before publishing:

```sh
claude plugin marketplace add "$PWD"
claude plugin install oldhand@oldhand

codex plugin marketplace add "$PWD"
codex plugin add oldhand@oldhand
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
