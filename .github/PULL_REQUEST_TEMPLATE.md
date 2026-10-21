## Problem

What is broken, missing, or unclear?

## Change

What is the smallest change that solves it? Which skills in the pack does it touch?

## Verification

- [ ] `./scripts/smoke-test.sh` (manifests parse, `python3 -m unittest discover -s tests` passes)
- [ ] I ran the affected skill in at least one agent (Claude Code, Codex, or another host) and checked the files it wrote under `.oldhand/<task>/`
- [ ] I tested the website when changing `site/`

## Scope

- [ ] No unrelated refactor or dependency
- [ ] Every platform manifest stays aligned, and versions changed together
- [ ] Documentation matches the behavior
- [ ] No secrets, private data, or generated build output
