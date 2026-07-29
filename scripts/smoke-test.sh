#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
skill="$repo_root/skills/oldhand/SKILL.md"

test -f "$repo_root/.claude-plugin/marketplace.json"
test -f "$repo_root/.claude-plugin/plugin.json"
test -f "$repo_root/.codex-plugin/plugin.json"
test -f "$repo_root/assets/logo.png"
test -f "$repo_root/.agents/plugins/marketplace.json"
test -f "$skill"
test -f "$repo_root/skills/oldhand/agents/openai.yaml"
test -f "$repo_root/LICENSE"

grep -q '^name: oldhand$' "$skill"
grep -q 'Fable is the orchestrator and final verifier' "$skill"
grep -q 'Haiku' "$skill"
grep -q 'Sonnet' "$skill"
grep -q 'promote Opus to orchestrator \*\*and final verifier\*\*' "$skill"
grep -q 'GPT-5.6 Sol is the orchestrator and final verifier' "$skill"
grep -q 'GPT-5.6 Terra' "$skill"
grep -q 'GPT-5.6 Luna' "$skill"
grep -q 'Jira, Asana, monday.com, Linear, GitHub Issues' "$skill"
grep -q 'context-rich plain prompts' "$skill"
grep -q 'If there is no ticket' "$skill"
grep -q 'assumptions, changed requirements' "$skill"
grep -q 'ticket is optional' "$skill"
grep -Eqi 'browser.*computer-use|computer-use.*browser' "$skill"
grep -q '"name": "oldhand"' "$repo_root/.claude-plugin/marketplace.json"
grep -q '"name": "oldhand"' "$repo_root/.codex-plugin/plugin.json"
grep -q '"version": "1.1.1"' "$repo_root/.claude-plugin/plugin.json"
grep -q '"version": "1.1.1"' "$repo_root/.codex-plugin/plugin.json"
grep -q '"composerIcon": "./assets/logo.png"' "$repo_root/.codex-plugin/plugin.json"
grep -q '"logo": "./assets/logo.png"' "$repo_root/.codex-plugin/plugin.json"
grep -q '"name": "oldhand"' "$repo_root/.agents/plugins/marketplace.json"

if grep -R -q '/Users/' \
  "$repo_root/skills" \
  "$repo_root/.claude-plugin" \
  "$repo_root/.codex-plugin" \
  "$repo_root/.agents"; then
  echo "error: plugin contains a machine-specific path" >&2
  exit 1
fi

python3 -m json.tool "$repo_root/.claude-plugin/marketplace.json" >/dev/null
python3 -m json.tool "$repo_root/.claude-plugin/plugin.json" >/dev/null
python3 -m json.tool "$repo_root/.codex-plugin/plugin.json" >/dev/null
python3 -m json.tool "$repo_root/.agents/plugins/marketplace.json" >/dev/null

echo "PASS: Oldhand contains both plugin marketplaces and the portable workflow skill."
