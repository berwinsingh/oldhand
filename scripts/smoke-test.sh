#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

# The python3 on PATH can be a shim that refuses to run; fall back to the system one.
py=python3
if ! python3 -c 'import sys' >/dev/null 2>&1; then
  py=/usr/bin/python3
fi

for f in \
  LICENSE CONTRIBUTING.md CODE_OF_CONDUCT.md SECURITY.md SUPPORT.md assets/logo.png \
  skills/oldhand/agents/openai.yaml \
  .github/PULL_REQUEST_TEMPLATE.md .github/ISSUE_TEMPLATE/bug_report.yml .github/ISSUE_TEMPLATE/config.yml; do
  test -f "$f" || { echo "error: $f is missing" >&2; exit 1; }
done

for f in \
  .claude-plugin/plugin.json .claude-plugin/marketplace.json .codex-plugin/plugin.json \
  .agents/plugins/marketplace.json plugin.json gemini-extension.json; do
  "$py" -m json.tool "$f" >/dev/null || { echo "error: $f is not valid JSON" >&2; exit 1; }
done

"$py" -m unittest discover -s tests

echo "PASS: Oldhand manifests parse and the skill pack tests pass."
