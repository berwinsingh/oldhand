# Adaptive Development Workflow Skills

Two portable development skills that turn a tracker item, document, or plain
prompt into a researched, minimally implemented, and realistically verified
change.

- `codex/ticket-to-browser-delivery`: ChatGPT Codex and Codex CLI
- `claude/dev-workflow`: Claude Code

Both skills:

- accept Jira, Asana, monday.com, Linear, GitHub Issues, another tracker, a
  document, or a plain prompt;
- inspect the project and trace the real flow before editing;
- research maintained MIT or Apache-2.0 implementations before building;
- apply Ponytail's smallest-correct-change discipline without overwriting
  unrelated work; and
- require automated checks plus end-to-end browser or computer-use QA before
  declaring implementation complete.

No ticketing system is required. When there is no ticket, the user's prompt and
supplied files become the source of truth.

## Install

Clone this private repository, then copy the skill for the platform you use:

```sh
git clone git@github.com:berwinsingh/adaptive-development-workflow-skills.git
cd adaptive-development-workflow-skills
```

### ChatGPT Codex / Codex CLI

User-wide installation:

```sh
mkdir -p "$HOME/.codex/skills"
cp -R codex/ticket-to-browser-delivery "$HOME/.codex/skills/"
```

Start a new Codex task after installation. Invoke it in Codex CLI or the IDE:

```text
$ticket-to-browser-delivery Implement DOCQ-123
```

In ChatGPT desktop, type `@` and choose **Adaptive Development Workflow**.

The skill assigns GPT-5.6 Sol as orchestrator and final verifier. It may
delegate bounded low-risk work to GPT-5.6 Luna and standard work to GPT-5.6
Terra. Sol reviews the integrated result and performs the final realistic
browser/computer-use verification. If an exact named model is unavailable or
superseded, the skill requires the latest available equivalent to be named in
the plan.

References:

- [Build and invoke Codex skills](https://learn.chatgpt.com/docs/build-skills)
- [GPT-5.6 model family](https://developers.openai.com/api/docs/guides/latest-model)
- [Browser in ChatGPT](https://learn.chatgpt.com/docs/browser)
- [Computer use](https://learn.chatgpt.com/docs/computer-use)
- [Plugins](https://learn.chatgpt.com/docs/plugins)
- [MCP in Codex](https://learn.chatgpt.com/docs/extend/mcp)

### Claude Code

User-wide installation:

```sh
mkdir -p "$HOME/.claude/skills"
cp -R claude/dev-workflow "$HOME/.claude/skills/"
```

Start a new Claude Code session, then invoke:

```text
/dev-workflow DOCQ-123
```

For browser QA, start Claude with Chrome enabled:

```sh
claude --chrome
```

You can also enable it inside a session with `/chrome`.

The skill assigns Fable as orchestrator and final verifier. Fable may delegate
bounded work to Haiku, Sonnet, or Opus according to complexity and risk, then
reviews the integrated result and verifies it end to end through the user's
browser. If Fable is unavailable, the skill explicitly promotes Opus to
orchestrator instead of silently falling back to a mid-tier model.

References:

- [Claude Code skills and slash commands](https://code.claude.com/docs/en/slash-commands)
- [Claude in Chrome](https://code.claude.com/docs/en/chrome)
- [Claude Code subagents](https://code.claude.com/docs/en/sub-agents)
- [Connect Claude Code to MCP servers](https://code.claude.com/docs/en/mcp)

## Required and optional integrations

The tracker integrations are conditional, not universal requirements. Install
only the connector for the system that contains the work item. If the request
is a prompt or local document, no tracker MCP is needed.

| Capability | Requirement | Setup |
| --- | --- | --- |
| Git checkout and shell | Required for code changes | Install [Git](https://git-scm.com/downloads) and the relevant host: [Codex](https://learn.chatgpt.com/docs/codex) or [Claude Code](https://code.claude.com/docs/en/overview) |
| Ponytail | Required for the implementation discipline referenced by both skills | Install from [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) |
| Browser or computer use | Required to pass the final E2E gate; not needed for planning-only work | Codex: [Browser](https://learn.chatgpt.com/docs/browser) or [Computer use](https://learn.chatgpt.com/docs/computer-use). Claude: [Claude in Chrome](https://code.claude.com/docs/en/chrome) or an available computer-use MCP |
| Tracker connector | Only for the tracker being used | Choose one from the table below |
| Context7 | Recommended when current library documentation is needed | [Context7 MCP](https://github.com/upstash/context7) |
| Playwright MCP | Optional browser fallback for hosts without a first-party browser tool | [Microsoft Playwright MCP](https://github.com/microsoft/playwright-mcp) |
| GitHub integration | Needed only for remote repository, PR, issue, or review actions | [GitHub MCP server](https://github.com/github/github-mcp-server) |

Install Ponytail on each host where the skill will run:

```text
# Claude Code
/plugin marketplace add DietrichGebert/ponytail
/plugin install ponytail@ponytail

# Codex
codex plugin marketplace add DietrichGebert/ponytail
codex plugin add ponytail@ponytail
```

Ponytail's hooks require Node.js on `PATH`. See its repository for current
platform requirements.

### Tracker MCPs

| System | Official endpoint or integration | Documentation |
| --- | --- | --- |
| Jira / Atlassian | `https://mcp.atlassian.com/v1/mcp` | [Atlassian Rovo MCP](https://developer.atlassian.com/cloud/rovo-mcp/) |
| Asana | `https://mcp.asana.com/v2/mcp` | [Asana MCP server](https://developers.asana.com/docs/using-asanas-mcp-server) |
| monday.com | `https://mcp.monday.com/mcp` | [monday MCP integration](https://developer.monday.com/api-reference/docs/integrate-with-monday-mcp) |
| Linear | `https://mcp.linear.app/mcp` | [Linear MCP](https://linear.app/docs/mcp) |
| GitHub Issues | GitHub's official MCP server | [github/github-mcp-server](https://github.com/github/github-mcp-server) |

For a Streamable HTTP server, the host commands have these forms:

```sh
# Codex
codex mcp add NAME --url https://example.com/mcp

# Claude Code; --scope user makes it available across projects
claude mcp add --transport http --scope user NAME https://example.com/mcp
```

Use the provider's documentation for authentication and any provider-specific
headers. Verify configured servers with `codex mcp list` or `claude mcp list`;
complete OAuth with `codex mcp login NAME` or `/mcp` in Claude Code when the
provider requires it.

Example for Linear:

```sh
codex mcp add linear --url https://mcp.linear.app/mcp
claude mcp add --transport http --scope user linear https://mcp.linear.app/mcp
```

## Verify the installation

Run the repository's dependency-free clean-install smoke test:

```sh
./scripts/smoke-test.sh
```

Then verify discovery without authorizing edits:

```sh
codex exec --ephemeral -C "$PWD" \
  'Use $ticket-to-browser-delivery. Do not edit files. Reply with the skill name, orchestrator, and accepted request sources.'

claude --print --no-session-persistence \
  '/dev-workflow Do not edit files. Reply with the skill name and its five phases.'
```

A real delivery test should use a disposable sample application and prove the
actual acceptance flow in Browser, Chrome, or computer use. A command being
recognized is only the installation check; it is not a substitute for the
skill's release gate.

## Safety contract

Neither skill authorizes remote or destructive actions by itself. Commits,
pushes, PRs, tracker comments/status changes, and deployments still require the
user's authorization. Existing dirty worktrees are preserved, and blocked
browser QA must be reported as blocked rather than claimed as passed.
