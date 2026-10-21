# Rebuild the Oldhand website for the 2.0 pack: report

### Verdict: VERIFIED

| criterion | outcome | proof | counted checks | status | by | evidence | flags |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC1 | The page renders the conductor skill's own text (skills/oldhand/SKILL.md imported at build time, not a copy) in a scrollable block with "Copy raw" and "View on GitHub" controls, and the hard stops section shown above it is sliced from that same import | e2e | C39 | pass | lead:fable | qa/evidence/S1/lead-1.txt |  |
| AC2 | An install switcher offers one tab per install route that was tested on this machine (Any agent via npx skills, Claude Code plugin, Codex plugin, git clone), each with the exact commands, a copy control that copies that exact text, the line to type afterwards per host, and the tool version and date it was tested; no untested command is shown | e2e | C16, C24 | pass | qa:worker | qa/results/S10.json |  |
| AC3 | The page contains no invented artifact: no fake ids, stamps, fake screenshots, decorative checkmarks or status badges, and every factual claim links to its source file in the repository | review | C34 | pass | lead:fable | review.md |  |
| AC4 | The page is readable in light and dark (prefers-color-scheme) at 1440 and 375 wide with no horizontal page scroll, no text under 13px, and text and the primary control meet WCAG AA contrast | e2e | C36, C38 | pass | qa:worker | qa/results/S11.json |  |
| AC5 | Google Analytics is not loaded on first visit; the only control is a footer toggle; choosing it loads GA and the choice persists across reload; there is no overlay or banner | e2e | C18 | pass | qa:worker | qa/results/S4.json |  |
| AC6 | An "Example run" section shows the real examples/csv-import-dupes run: its verdict line, criteria table and "Not verified" section sliced from the committed report.md, with a link to the files | e2e | C19 | pass | qa:worker | qa/results/S5.json |  |
| AC7 | The page lists the 11 stages in chain order, one line each, every line linking to that stage's SKILL.md on GitHub, and a model routing table by role (lead, worker, scout) per host with the substitution note, dated | e2e | C20 | pass | qa:scout | qa/results/S6.json |  |
| R1 | `npm run build` and `npm run test:sites` pass; dist/client/index.html, dist/server/index.js and dist/.openai/hosting.json still exist | integration | C32, C37 | pass | qa:scout | qa/results/S7.json |  |
| R2 | The GitHub Pages workflow still works unchanged: it builds site/, previews on 127.0.0.1:4173, and screenshots `?social-preview=1` at 1200x627 into dist/client/og-image.png, so the social-preview hook in index.html must survive | review | C35 | pass | lead:fable | review.md |  |
| R3 | The existing opt-in analytics code path keeps consent default denied and never loads gtag before a stored "granted" choice | unit | C23, C31 | pass | lead:fable | build/unit.txt |  |

**Why:**
- every live criterion has a passing check of its proof kind on the current tree and the lead recorded an e2e pass; no open high or medium findings

**Review findings**

| id | sev | lens | where | status | finding | note |
| --- | --- | --- | --- | --- | --- | --- |
| F1 | high | contract | site/src/App.jsx:51 | fixed | Git clone tab shown as tested with 'git 2.x' and no recorded run | git clone route run on 2026-10-11 (git 2.55.0, zsh 5.9, clone of this branch, 11 links, idempotent); tested line names the versions; contract tested-routes list updated |
| F2 | medium | contract | site/src/App.jsx:17-40 | fixed | tested lines imply the GitHub-source commands were run; the runs used a local checkout | every tested line says 'from a local checkout of this repository' |
| F3 | medium | contract | site/src/App.jsx:325-327 | fixed | example intro says the prompt and every file are in the example folder; prompt is in examples/README.md and binary evidence was left out | intro links examples/README.md for the prompt and says the binary SQLite evidence is left out |
| F4 | medium | contract | site/src/App.jsx:21-53,276-281,379-396 | fixed | host lists, invocation lines, honest-scope bullets and the hero claim have no link to their source files (AC3) | hosts.md linked from the install panel; scope bullets link the conductor and oldhand-qa; hero links ledger.py |
| F5 | medium | correctness | .github/workflows/pages.yml:6-8 | fixed | Pages deploys only on site/** so changes to the imported SKILL.md, report.md and plugin.json never redeploy the page | paths trigger extended to the imported files (trigger only; steps unchanged); contract scope updated by the chair |
| F6 | medium | correctness | site/src/App.jsx:82-88,247-255 | fixed | a moved heading makes section() return '' and the page ships an empty hard-stops list; nothing fails the build | slicing moved to src/slices.js with prefix heading matches; scripts/check-sources.mjs runs before vite build and fails on any empty slice; tests/slices.test.mjs covers the committed files and a moved heading |
| F7 | medium | correctness | site/src/App.jsx:131-146 | fixed | CopyButton shows Copied when execCommand('copy') returned false, and the fallback drops keyboard focus | execCommand result read; failure shows 'Copy failed: select the text'; focus returned to the button; status span has role=status |
| F8 | medium | simplicity | site/src/App.jsx:73-80,351-374 | fixed | model table hand-copied from orchestration.md with a typed-in date; drifts on the next lineup change | orchestration.md imported; the table and its date are sliced from the 'Current models per host' heading; check-sources asserts it |

**Notes**
- C3 (R3 mutation) was voided and does not count: first mutation did not parse (dangling else); replaced by the if(true) mutation
- C4 mutation check on R3: KILLED
- C9 mutation check on R3: KILLED
- C12 mutation check on R3: KILLED
- C28 mutation check on R3: KILLED
- C33 mutation check on R3: KILLED

Computed by ledger.py from ledger.json at 2026-10-11T07:29:19+00:00 on tree 00747f3a27:91dcb9a6:7d47a232. Not written by hand.

## Asked
Rebuild https://berwinsingh.github.io/oldhand/ for the 2.0 pack so it shows real artifacts and reads as a credible developer page, in light and dark, at desktop and phone widths, with analytics off unless a visitor opts in; keep the Pages deploy, the Sites handoff files and the opt-in analytics path working. Ten criteria: AC1 to AC7 (e2e, AC3 by review) and R1 to R3 (integration, review, unit). Mode implement; commit, push and PR authorized.

## Root cause
(traced, trace.md and plan.md) `site/AGENTS.md` told agents that a generated mock was the source of truth, so the page copied an image model's composition and invented its own evidence. The fix point is the content source: the page now imports `skills/oldhand/SKILL.md`, `skills/oldhand/references/orchestration.md`, `examples/csv-import-dupes/oldhand/report.md` and `.claude-plugin/plugin.json` at build time, slices them with `site/src/slices.js`, fails the build (`site/scripts/check-sources.mjs`) when a slice comes back empty, and shows only install routes that were run on this machine, with the tool version and date.

## Changed
- `site/src/App.jsx` (rewritten), `site/src/styles.css` (rewritten), `site/src/slices.js` (new), `site/src/analytics.js` (the three helpers moved out of App.jsx so a node test can import them), `site/scripts/check-sources.mjs` (new), `site/tests/analytics.test.mjs` and `site/tests/slices.test.mjs` (new), `site/index.html` (title, description, social tags, fonts link; the `?social-preview` hook kept), `site/vite.config.mjs` (dev-server allow-list for the three imported folders), `site/package.json` and lock (`@phosphor-icons/react` removed; `test` script; `build` runs the source check first), `site/AGENTS.md` (the content rule).
- Deleted: `site/public/assets/*.png` (2.9 MB), `site/design/`, `site/design-qa.md`, the comparison and implementation PNGs.
- `.github/workflows/pages.yml`: trigger paths only (the imported files), added by the review chair; steps unchanged.
- `README.md`: Install, invocation, Models and Examples sections for the pack.
- `examples/site-rebuild/`: this task folder, copied in at ship time.

## Proof
- observed: `npm test` 10/10 (analytics 5, slicing 5); `npm run build` with `check-sources: ok`; `npm run test:sites` 4/4; dist/client 262 KB with no PNG but the favicon (build/unit.txt, build/build.txt).
- observed: mutation `if (choice === "granted")` -> `if (true)` on `analytics.js`: KILLED (build/mutation.txt). A first mutation that left a dangling `else` was ERROR by design and is voided (C3).
- observed: QA panel, see qa/results.md: one sub-agent per scenario through the host's browser pane or a headless Chrome of its own, each with a transcript and screenshots under qa/evidence/. S3 found the phone-width overflow of the install command block (fixed in CSS, re-run); S9 and S4 failed once on stale expectations (test count, footer wording) and passed after the scenario text was corrected. S6, S7 and S9 ran twice because the CSS fix landed after their first run.
- observed, lead's own run: S1 re-run by the lead with screenshots (qa/evidence/S1/lead-*), recorded with --lead.
- review (AC3, R2): four lenses, eight findings fixed, lows folded or deferred; review.md.

## Prior art
Research skipped: nothing new was added. One dependency removed. Fonts via Google Fonts (contract default). The build-time import pattern is Vite's `?raw` import; the slicing is three small functions, not a Markdown renderer (contract: out of scope).

## Review
Contract, correctness, security, simplicity (worker tier, Sonnet class). F1 high (git clone route shown as tested without a run) and F2 to F8 medium fixed in one round; 20 lows listed as follow-ups in the pull request. Chair refuted one (README scope).

## Live runs
0 paid runs. Google Analytics received a few real page_view hits from localhost while QA agents tested the opt-in toggle (property G-75YW6HE9FT, the owner's own).

## Not verified
- Real screen readers, Safari and Firefox: the accessibility checks are Chrome measurements plus ARIA rules.
- The deployed page itself: links target `main`, where 17 of the 19 linked paths exist only after this branch merges; the Pages build and the og-image screenshot run in CI, not here.
- The three install commands with `berwinsingh/oldhand` as source were run from a local checkout of this branch; the GitHub source serves 2.0 only after the merge.
- Independence: the lead wrote the scenarios and chaired the review; review memos and QA runs were independent sub-agents, except the lead's own S1 re-run, recorded as such.

## Follow-ups
See the pull request's follow-ups comment (21 items: 14 for the pack from its review, 7 for the site).

## Published
Commits 00747f3 (pack) and e5df4f9 (site) on branch enhance/oldhand-2. The push from the berwinsingh account was refused because its token lacks the `workflow` scope (both commits touch .github/workflows); the pull request against main is opened once the scope is granted. Pages deploys after the merge.