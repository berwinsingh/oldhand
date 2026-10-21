# Plan: rebuild the Oldhand website

## Root cause and fix point
`site/AGENTS.md` made a generated mock the source of truth, so the page copied an image model's
composition and invented its own evidence. The fix point is the content source: the page imports the
real skill, the real example report and the real version at build time, and shows only install
routes that were run.

## Files and why
- `site/index.html`: title "Oldhand", 2.0 description and OG text, Google Fonts `<link>` with
  preconnect (replaces the CSS `@import`), keep the `?social-preview` hook; hide nothing but the
  footer toggle in preview mode.
- `site/src/App.jsx`: rewrite (target under 260 lines). Sections: header (wordmark, version from
  plugin.json, MIT, nav); hero (H1, one sentence, install switcher, "then type" line); the 11 stages
  as one-line links; hard stops sliced from the SKILL.md import; example run sliced from report.md;
  the whole SKILL.md in a scrollable `<pre>` with Copy raw and View on GitHub; model routing table
  (dated, with the substitution note); honest scope bullets; footer with the analytics toggle.
- `site/src/analytics.js`: the three analytics helpers moved out of App.jsx unchanged, so a node
  test can import them.
- `site/src/styles.css`: rewrite with the brief's tokens (light and dark), IBM Plex Sans/Mono, no
  text under 13px, max 72ch prose, tabs that scroll inside themselves on narrow screens.
- `site/vite.config.mjs`: `server.fs.allow: ['..']`; `test` script.
- `site/package.json` + lock: remove `@phosphor-icons/react`; add `"test": "node --test tests/"`.
- `site/tests/analytics.test.mjs`: the regression check for R3 (gtag never injected before a
  stored "granted"; consent default denied; choice persists).
- Delete: `site/public/assets/*.png`, `site/design/`, `site/design-qa.md`,
  `site/design-comparison-*.png`, `site/implementation-*.png`.
- `site/AGENTS.md`: replace the mock rule with "content comes from the skill files, README and
  examples; never invent ids, screenshots or results; show only tested install commands".
- `README.md`: align the Install section with the tabs (reconcile with the pack fixer's M14 edit).

## Regression check
`site/tests/analytics.test.mjs` run by `npm test`; then `mutate.py` on `analytics.js`: replace
`choice === "granted"` with `true` and expect KILLED.

## Scenarios (QA stage writes the cards)
- S1 web acceptance AC1: hard stops and the full SKILL.md block render from the import; Copy raw copies the file text; the GitHub link targets skills/oldhand/SKILL.md.
- S2 web acceptance AC2: each tab shows its commands, tested-with line and "then type" line; the copy control copies exactly the shown command; `?agent=codex` preselects; a bogus `?agent=` falls back (messy).
- S3 web acceptance AC4: 1440 and 375, light and dark: no horizontal scroll, computed font sizes >= 13px, contrast of body text and the primary control >= 4.5:1 (computed from the tokens).
- S4 web acceptance AC5: fresh profile: no gtag script and no request to googletagmanager; footer toggle loads it; reload keeps the choice; turning it off stops further loads.
- S5 web acceptance AC6: the verdict line, criteria table and "Not verified" text equal the committed report.md sections.
- S6 cli acceptance AC7 + negative: every GitHub link in the built page maps to a path that exists in the repo (new files are not on main until the merge, so check the working tree); exactly 11 stage links in chain order.
- S7 cli regression R1: `npm run build` and `npm run test:sites` pass; the three dist files exist; dist is under 1 MB.
- S8 web regression R2: `?social-preview=1` at 1200x627 shows the hero and no toggle.
- S9 cli regression R3: `npm test` passes and the mutation is KILLED.
- S10 web messy AC4: zoom 200% at 375 still has no horizontal scroll; a very long command wraps or scrolls inside its block.

## Negative paths
Bogus `?agent=`; localStorage throwing (covered by try/catch, checked by reading the code in review); clipboard denied (execCommand fallback kept).

## Environments
Local Vite dev server (preview tooling) for QA; the built `dist/client` served by `vite preview` for the social-preview check.

## Blast radius and rollback
Only the public site and its social image. Rollback: revert the site commit on main; Pages redeploys.

## Delegation
Lead (Fable): contract, trace, plan, build, review chair, lead QA re-run, verdict, ship.
Review: three read-only sub-agents (worker tier, Sonnet): contract, correctness + accessibility,
simplicity. QA: scouts (Haiku) for S6, S7, S9 in parallel; web scenarios S1 to S5, S8, S10 one at a
time by a worker (Sonnet) through the host browser pane, or by the lead if sub-agents cannot drive
it; the lead re-runs S1 and S2 and records them with `--lead`.

## Live and paid runs
0.

## Out of scope, listed as follow-ups
Untested install routes (gh skill install, copilot plugin install, gemini extensions install, agy
plugin install) stay off the site until run once; a second example run with real sub-agents.
