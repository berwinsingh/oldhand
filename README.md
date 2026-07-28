# Oldhand

**Give your coding agent a definition of done.**

Oldhand is one portable development workflow for Claude Code and ChatGPT
Codex. It accepts a Jira, Asana, monday.com, Linear, or GitHub issue—or just a
plain prompt—then makes the agent understand the real flow, research permissive
open-source prior art, implement the smallest safe change with Ponytail, and
verify the result end to end.

## Install

### Claude Code

Run these as two separate prompts inside Claude Code:

```text
/plugin marketplace add berwinsingh/adaptive-development-workflow-skills
/plugin install oldhand@oldhand
```

Then start a new session and use:

```text
/oldhand:oldhand Implement DOCQ-123
```

### ChatGPT Codex / Codex CLI

```sh
codex plugin marketplace add berwinsingh/adaptive-development-workflow-skills
codex plugin add oldhand@oldhand
```

Restart Codex or start a new task, then use:

```text
$oldhand Implement DOCQ-123
```

That is the complete installation. The plugin contains the skill and its
platform manifests. It does not require a tracker integration or MCP server to
install.

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

## License

MIT
