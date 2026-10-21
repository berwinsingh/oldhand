# Rebuild the Oldhand website for the 2.0 pack

Source: prompt  ·  Mode: implement

## Problem / expected behaviour
Current: https://berwinsingh.github.io/oldhand/ describes the 1.x single skill for two hosts and
reads as AI-made: a fake work-order id, a generated "DELIVERED" stamp, a made-up dashboard screenshot
labelled PASSED, static checkmarks, twelve identical icon cards, slogans for headings, uppercase mono
micro-labels under 11px, a GA consent box covering the first screen, no dark mode, stale model names
(GPT-5.6 Sol/Terra), and 2.9 MB of decorative PNGs.
Expected: a plain, credible developer page for the 2.0 pack that shows real artifacts (the real
conductor SKILL.md imported at build time, the real install commands with the date and version they
were tested, the real example run from examples/), works in light and dark, at 1440 and 375, loads
fast, and keeps analytics off unless the visitor opts in from the footer.

## Acceptance criteria
- AC1: The page renders the conductor skill's own text (skills/oldhand/SKILL.md imported at build time, not a copy) in a scrollable block with "Copy raw" and "View on GitHub" controls, and the hard stops section shown above it is sliced from that same import (proof: e2e)
- AC2: An install switcher offers one tab per install route that was tested on this machine (Any agent via npx skills, Claude Code plugin, Codex plugin, git clone), each with the exact commands, a copy control that copies that exact text, the line to type afterwards per host, and the tool version and date it was tested; no untested command is shown (proof: e2e)
- AC3: The page contains no invented artifact: no fake ids, stamps, fake screenshots, decorative checkmarks or status badges, and every factual claim links to its source file in the repository (proof: review)
- AC4: The page is readable in light and dark (prefers-color-scheme) at 1440 and 375 wide with no horizontal page scroll, no text under 13px, and text and the primary control meet WCAG AA contrast (proof: e2e)
- AC5: Google Analytics is not loaded on first visit; the only control is a footer toggle; choosing it loads GA and the choice persists across reload; there is no overlay or banner (proof: e2e)
- AC6: An "Example run" section shows the real examples/csv-import-dupes run: its verdict line, criteria table and "Not verified" section sliced from the committed report.md, with a link to the files (proof: e2e)
- AC7: The page lists the 11 stages in chain order, one line each, every line linking to that stage's SKILL.md on GitHub, and a model routing table by role (lead, worker, scout) per host with the substitution note, dated (proof: e2e)
- R1: `npm run build` and `npm run test:sites` pass; dist/client/index.html, dist/server/index.js and dist/.openai/hosting.json still exist (proof: integration)
- R2: The GitHub Pages workflow still works unchanged: it builds site/, previews on 127.0.0.1:4173, and screenshots `?social-preview=1` at 1200x627 into dist/client/og-image.png, so the social-preview hook in index.html must survive (proof: review)
- R3: The existing opt-in analytics code path keeps consent default denied and never loads gtag before a stored "granted" choice (proof: unit)

## In scope / out of scope
In: site/index.html, site/src/App.jsx, site/src/styles.css, site/vite.config.mjs, site/package.json
(dropping @phosphor-icons/react), site/public/assets (delete decorative PNGs), site/AGENTS.md,
site/design-qa.md and the design/comparison PNGs (delete), README.md install section alignment.
Also in (added by the review chair on 2026-10-11): the `paths` trigger list of
.github/workflows/pages.yml, because the page imports files outside site/ and would not redeploy
when they change; the build and screenshot steps stay as they are.
Out: the skills themselves, the manifests, the Pages workflow's steps, the Sites worker and its
tests, any new dependency, a Markdown renderer.

## Context the user gave (assumptions, changed requirements, constraints, partial work, files, links)
- The user: "improve the website's UI, because right now it looks kind of like AI slop" and the
  skill "needs to work both on Claude Code, Cursor, Codex, all the major AI platforms and should be
  accessible properly and easily."
- Design brief from the research pass (scratchpad research_website-critique.md): show the artifact
  itself; borrow from htmx (version in header, real invocation in hero), uv (highlights linking to
  sections, platform tabs), bun (every claim links to its source), superpowers (per-host install).
- Tested install routes on 2026-10-11 (isolated HOME): npx skills 1.7.2 `add ./oldhand --skill '*' -g`
  for claude-code, codex, cursor, github-copilot, gemini-cli, opencode (11 skills into ~/.agents/skills
  + ~/.claude/skills symlinks); `claude plugin marketplace add` + `install oldhand@oldhand` on Claude
  Code 2.1.274 (11 skills, version 2.0.0); `codex plugin marketplace add` + `codex plugin add
  oldhand@oldhand` on codex-cli 0.146.0 from a local marketplace (11 skills, 2.0.0); the git clone
  and symlink loop with git 2.55.0 and zsh 5.9 against a clone of this branch (11 links in each
  folder, idempotent; added 2026-10-11 after the contract review). Not tested: gh skill install,
  copilot plugin install, gemini extensions install, agy plugin install.
- Example run: examples/csv-import-dupes (a seeded duplicate-batch bug; run by one agent with no
  sub-agent tool, which its report says under "Not verified").
- Partial work: none on the site. Branch enhance/oldhand-2 holds the uncommitted 2.0 pack.

## Affected users, roles, tenants, data, integrations, environments
Visitors of the GitHub Pages site; the social preview image generated in CI; Google Analytics
property G-75YW6HE9FT (opt-in only). No accounts, no server state.

## Open questions and assumptions (each: what, why it matters, default taken)
- Keep Vite + React or go plain HTML? Vite lets the page import SKILL.md and report.md at build
  time so they cannot drift, and the Pages workflow already builds it. Default: keep Vite + React,
  drop the icon dependency.
- Fonts: the brief proposes IBM Plex Sans + Mono from Google Fonts. Default: use them via a
  preconnected <link>; system fallback stack.
- Which hosts get a tab? Only tested routes. Cursor, Copilot, Gemini CLI and OpenCode are covered by
  the "Any agent" npx tab with their invocation lines. Default: four tabs.
- GA: keep the opt-in; move the control to the footer. Default: yes.

## Authorized actions (commit? push? PR? tracker? deploy? migration? live paid runs and how many?)
commit: yes (user: "push it to a PR once the site is done"); push: yes, branch enhance/oldhand-2 to
origin as the berwinsingh account; PR: yes, against main, no auto-merge; tracker: no; deploy: no
(Pages deploys from main after merge, by the user); migration: n/a; live paid runs: 0; message: no.
