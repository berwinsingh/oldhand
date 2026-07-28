#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test_root=$(mktemp -d "${TMPDIR:-/tmp}/adaptive-workflow-skills.XXXXXX")
trap 'rm -rf "$test_root"' EXIT HUP INT TERM

mkdir -p "$test_root/.codex/skills" "$test_root/.claude/skills"
cp -R "$repo_root/codex/ticket-to-browser-delivery" "$test_root/.codex/skills/"
cp -R "$repo_root/claude/dev-workflow" "$test_root/.claude/skills/"

codex_skill="$test_root/.codex/skills/ticket-to-browser-delivery/SKILL.md"
claude_skill="$test_root/.claude/skills/dev-workflow/SKILL.md"

test -f "$codex_skill"
test -f "$test_root/.codex/skills/ticket-to-browser-delivery/agents/openai.yaml"
test -f "$claude_skill"

grep -q '^name: ticket-to-browser-delivery$' "$codex_skill"
grep -q '^name: dev-workflow$' "$claude_skill"
grep -q 'GPT-5.6 Sol' "$codex_skill"
grep -q 'GPT-5.6 Terra' "$codex_skill"
grep -q 'GPT-5.6 Luna' "$codex_skill"
grep -q 'Use Fable as orchestrator and final verifier' "$claude_skill"
grep -q 'Haiku' "$claude_skill"
grep -q 'Sonnet' "$claude_skill"
grep -q 'Opus' "$claude_skill"
grep -q 'Jira, Asana, Monday, Linear, GitHub Issues' "$codex_skill"
grep -q 'Jira, Asana,' "$claude_skill"
grep -q 'plain user prompt' "$codex_skill"
grep -q 'plain user' "$claude_skill"
grep -Eqi 'browser.*computer-use|computer-use.*browser' "$codex_skill"
grep -Eqi 'browser.*computer|computer.*browser' "$claude_skill"

if grep -R -q '/Users/' "$repo_root/codex" "$repo_root/claude"; then
  echo "error: packaged skills contain a machine-specific path" >&2
  exit 1
fi

echo "PASS: Codex and Claude skills install cleanly and contain the required workflow gates."
