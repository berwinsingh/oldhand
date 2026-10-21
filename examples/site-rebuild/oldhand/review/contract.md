# contract lens
Reviewer: worker:sonnet-5.5 · Read: brief, lenses, contract.md, plan.md, trace.md, build/*.txt, git diff of site/ and README.md, site/src/App.jsx, analytics.js, analytics.test.mjs, styles.css, index.html, pages.yml, SKILL.md, report.md, examples/README.md, orchestration.md, hosts.md · Ran: in a temp copy (scratchpad/review-site/contract): `npm ci`, `npm run build`, `npm run test:sites`, `npm test`, a headless Chrome screenshot of `?social-preview=1` at 1200x627, the git-clone link loop twice in a throwaway HOME, WCAG contrast of the CSS tokens, `ls` of every file the page links to

## Findings

### 1. The "Git clone" tab does not carry a tool version, and no test of that route is on record
- Severity: high · Confidence: high (the missing version), low (that the route was never run)
- Where: site/src/App.jsx:51
- Failure: AC2 requires "the tool version and date it was tested" on every tab. The git tab prints `Tested 2026-10-11 on macOS with git 2.x and zsh.` "2.x" is not a version and no zsh version is given. contract.md:42-46 lists the routes actually tested on 2026-10-11 (npx skills 1.7.2, Claude Code 2.1.274, codex-cli 0.146.0) and git clone is not among them, while the AC2 text counts it as tested. I found no transcript of it in .oldhand/site-rebuild. I reproduced the loop in a throwaway HOME against a copy of the pack and it works, is idempotent and links 11 skills, so the command is probably sound; the page's claim and its version line are the gap.
- Evidence: `tested: \`Tested ${TESTED} on macOS with git 2.x and zsh.\`` (App.jsx:51); contract.md:42-46.
- Smallest fix: print the real `git --version` and `zsh --version` from the machine, and keep the record of the run next to the other three (or drop the tab until it is recorded).

### 2. The commands shown are not the commands that were tested (the source argument differs), yet the tabs say "Tested"
- Severity: medium · Confidence: high
- Where: site/src/App.jsx:17, 30, 38 with the tested lines at 20, 32, 40
- Failure: AC2 says "no untested command is shown". contract.md:42-46 records `npx skills add ./oldhand --skill '*' -g` (a local path), the `claude plugin marketplace add` CLI form from a local checkout, and `codex plugin marketplace add` "from a local marketplace". The page shows `berwinsingh/oldhand` as the source in all three, and the Claude tab shows the in-session `/plugin ...` form where the CLI form was run. Until the branch merges, `berwinsingh/oldhand` serves the 1.x pack, so the exact text cannot have been run with the 2.0 result the tabs describe. A visitor reads "Tested 2026-10-11 with Claude Code 2.1.274" next to a command nobody ran in that form.
- Evidence: App.jsx:17 `npx skills add berwinsingh/oldhand --skill '*' -g`; contract.md:42 `add ./oldhand --skill '*' -g`.
- Smallest fix: add to each tested line "from a local checkout of this branch; the GitHub source is the same command with the repo name", or re-run the exact commands after the merge and re-date them.

### 3. The Example run intro claims more than the repository holds
- Severity: medium · Confidence: high
- Where: site/src/App.jsx:325-327
- Failure: the page says "The prompt, the project and every file the pack wrote are in examples/csv-import-dupes" and links that folder. The prompt text is in examples/README.md (one level up), not in that folder (its README.md is the importer's own). examples/README.md also says "The binary SQLite evidence files were left out of the repo", so "every file" is false. A visitor who follows the link looking for the prompt does not find it. AC3 requires each factual claim to be true to its source.
- Evidence: App.jsx:325-326; examples/README.md: "The binary SQLite evidence files were left out of the repo."
- Smallest fix: "The prompt is in examples/README.md; the project and the task folder the pack wrote (minus binary SQLite evidence) are in examples/csv-import-dupes", with both links.

### 4. Claims with no link to their source, against AC3 "every factual claim links to its source file"
- Severity: medium · Confidence: high
- Where: site/src/App.jsx:50 (hosts that read `~/.agents/skills`), 21-25 / 33 / 41 / 53 (the line to type per host), 379-396 (Honest scope bullets), 276-281 (hero: "a small script, not the model, says when it is done")
- Failure: the host lists and invocation lines come from README.md and skills/oldhand/references/hosts.md (Kiro, Antigravity, Amp and Goose were not among the six agents the npx route was tested for), and the Honest scope claims come from SKILL.md and oldhand-qa/SKILL.md. None of them links to those files. I checked the claims against the sources and they hold (SKILL.md:206-207 for the ten-agent count; hosts.md:77, 97, 100-101 for invocations), so this is a missing link, not a false claim. A reviewer applying AC3 literally fails these sections.
- Evidence: the only links in those blocks are the stage, script, orchestration.md and example links elsewhere on the page.
- Smallest fix: link `references/hosts.md` once from the install panel and SKILL.md / oldhand-qa/SKILL.md from the scope list.

### 5. A source drift guard the contract asks for is missing: the page rebuilds only when `site/**` changes
- Severity: medium · Confidence: high
- Where: .github/workflows/pages.yml:6-8 (workflow is out of scope), consumed at site/src/App.jsx:2-4
- Failure: AC1 imports SKILL.md at build time precisely so the page cannot drift, and AC6 and the version badge do the same with report.md and plugin.json. The Pages workflow triggers on `site/**` and its own file only. A later push to main that edits skills/oldhand/SKILL.md, the example report or plugin.json (a version bump) does not redeploy, so the live page keeps showing the old skill text and version until someone touches `site/`. The contract forbids changing the workflow, so I cannot ask for the fix in this PR.
- Evidence: pages.yml:6-8 `paths: - "site/**" - ".github/workflows/pages.yml"`.
- Smallest fix: list it as a follow-up (add `skills/oldhand/SKILL.md`, `examples/**`, `.claude-plugin/plugin.json` to the `paths:` filter, a DPE-style change to a file this PR must not touch) and say so in the PR body.

### 6. A renamed heading or changed table header silently empties a section instead of failing the build
- Severity: medium · Confidence: high
- Where: site/src/App.jsx:83-84 (`section()` returns ""), 247-255, 329, 330
- Failure: the AC1 hard-stops block, the AC6 verdict, criteria table, root cause and "Not verified" list are all found by exact heading or header text. If SKILL.md's `## Hard stops` is renamed, "What it will not do" renders with an empty list; if report.md's `### Verdict:` line changes the verdict paragraph is simply not rendered (`{verdict && ...}`); a renamed table column is dropped by `.filter((i) => i >= 0)` (App.jsx:114). `npm run build`, `test:sites` and `npm test` all still pass, so R1 would stay green while AC1 or AC6 stops being true. No test in the repo covers the slicing.
- Evidence: `if (start < 0) return "";` (App.jsx:84); `{verdict && <p className="verdict">{verdict}</p>}` (App.jsx:329).
- Smallest fix: throw at module load when a slice is empty (`if (!hardStops || !verdict || !notVerified) throw new Error(...)`), so the build fails instead of shipping an empty section.

### 7. The AC1 control is labelled "Copy", not "Copy raw"
- Severity: low · Confidence: high
- Where: site/src/App.jsx:149 (visible text), 345 (aria-label "Copy the whole SKILL.md")
- Failure: AC1 and plan.md name the controls "Copy raw" and "View on GitHub". The visible name is "Copy". An e2e check that looks up a control called "Copy raw" finds none. The copied text is the correct whole file.
- Smallest fix: pass a `text` prop and show "Copy raw" on the skill block.

### 8. The invented ticket id `DOCQ-123` appears seven times as the example prompt
- Severity: low · Confidence: medium
- Where: site/src/App.jsx:22-24, 33, 41, 53
- Failure: AC3 says "no fake ids"; the old page's complaint included a fake work-order id. `DOCQ-123` does not exist anywhere and the "Then, in ..." label does not say it is an example. It is the same placeholder README.md already uses, so the intent is clear, but a literal reading of AC3 flags it.
- Smallest fix: label the lines "for example" or use `<ticket>`.

### 9. The footer says "Anonymous Google Analytics" with no disclosure link
- Severity: low · Confidence: medium
- Where: site/src/App.jsx:409-412
- Failure: with `analytics_storage` granted, GA4 sets a client-id cookie, which is pseudonymous rather than anonymous. The old consent text carried a "How Google uses data" link and this wording dropped it, so the one place a visitor consents to Google tracking has an unsourced claim and no link. The toggle itself behaves correctly (AC5 met).
- Smallest fix: say "Google Analytics" and link https://policies.google.com/technologies/partner-sites.

### 10. Google Fonts load on first visit, before any choice, next to a footer that says "Analytics are off"
- Severity: low · Confidence: high
- Where: site/index.html:16-20
- Failure: a first-time visitor's browser requests fonts.googleapis.com and fonts.gstatic.com, so Google receives the visit, while the footer says analytics are off. The contract chose this font route (Open questions, "Fonts"), and AC5 covers Google Analytics only, so no criterion fails; I note it because the page's own wording invites the question.
- Smallest fix: none required by the contract. Self-hosting the two fonts would remove it, but that needs a font file added to the repo.

### 11. The social card crops the install panel mid-row
- Severity: low · Confidence: high
- Where: site/src/App.jsx:273-283 inside the 1200x627 box set at site/index.html:49-58
- Failure: R2 holds (the hook survived, the preview rendered the hero with the header nav and footer hidden, and `test -s` would pass), but at 1200x627 the card shows the heading, the lede and the npx command, then cuts the "Then, in Codex" row in half and drops the tested line. The og:image:alt promises "the install commands"; one command is visible.
- Smallest fix: none needed for R2. Shorten the lede or the note if the card should end on a clean row.

### 12. README hunks reach beyond "install section alignment"
- Severity: low · Confidence: low
- Where: README.md intro paragraph, "Model orchestration" and the local-testing block (git diff)
- Failure: the contract scopes README.md to the install section. The diff also rewrites the intro, replaces the Model orchestration section and the local-test instructions. These may come from the 2.0 pack's own work (the working tree holds the whole uncommitted pack, so the diff against HEAD cannot separate them). If the site PR carries them, they widen it beyond the stated scope. Would confirm: `git log` on the pack branch for who wrote those hunks.
- Smallest fix: split the non-install README hunks into the pack PR if they are not part of this one.

## Checked and found fine
- AC1: `skillText` is a `?raw` import of skills/oldhand/SKILL.md (App.jsx:2), shown whole in a `max-height: 70vh; overflow: auto` block (styles.css:364-375) with a Copy control carrying `skillText` and a View on GitHub link to blob/main/skills/oldhand/SKILL.md. The hard stops come from the same import via `section(skillText, "## Hard stops")`; I traced the real file (SKILL.md:29-53): one intro paragraph plus ten numbered items with indented continuation lines parse into the right `<ol>`; the section sits above the skill block on the page.
- AC2: four tabs, one per route, the exact command text is what `Copy` receives (the same `text` prop feeds `<pre>` and the clipboard, App.jsx:154-161), the per-host "then" lines match README.md and hosts.md, `?agent=` is validated against the tab keys with a localStorage fallback and a safe default (App.jsx:163-174). The git loop works and is idempotent in a throwaway HOME.
- AC4 tokens: contrast of the CSS colours, computed. Light: text 16.5 on bg, muted 6.6 on bg and 6.1 on surface, accent 5.3 on bg and 4.9 on surface. Dark: text 15.4, muted 7.1 and 6.5, accent 7.5 and 6.8. All at or above 4.5. Smallest font: inline code at 0.9em inside 15px text is 13.5px; nothing is set below 13px in styles.css. Tables use `display:block; overflow-x:auto` and the skill block wraps, so no page-wide horizontal scroll from content (not run in a browser by me; that is QA S3).
- AC5/R3: `applyAnalyticsChoice` loads only on "granted" (analytics.js:57-62); null and "denied" with no gtag load nothing; consent default is pushed denied before the grant; the App reads the stored choice once and applies it in an effect (App.jsx:236-239); there is no banner or overlay anywhere in App.jsx or styles.css. The three helpers moved from App.jsx unchanged apart from taking optional `storage`/`win`/`doc` arguments. `npm test`: 5 pass; the recorded mutation (build/mutation.txt) was KILLED.
- AC6: the report parses correctly for this file: `### Verdict: VERIFIED`, the criteria table (columns criterion, outcome, proof, status, by exist in the header), `## Root cause`, `## Not verified` with its four bullets, and the "Computed by ledger.py" line. No cell contains a pipe and no sliced block holds `**` or link syntax that `inline()` would show raw. The example section link points to examples/csv-import-dupes.
- AC7: 11 stage links in the README's chain order (conductor first), each `blob/main/skills/<name>/SKILL.md`; the model table agrees with orchestration.md row by row for the six hosts it shows (names shortened, Devin Desktop and the vision column omitted, neither required by AC7); dated "as of October 2026" like the source; the substitution note matches the source rule.
- AC3: no fake stamp, screenshot, checkmark or badge remains; the PNGs, design/ and design-qa.md are deleted and nothing references them (grep clean). Every link target on the page exists in the working tree (ledger.py, qa.py, mutate.py, orchestration.md, hosts.md, SECURITY.md, the example folder). All but SECURITY.md are untracked or modified and reach main only with this merge, as plan.md notes.
- R1: in a temp copy `npm ci`, `npm run build` (3 files, 252 KB in dist/client), `npm run test:sites` (4 pass) and `npm test` (5 pass); dist/client/index.html, dist/server/index.js and dist/.openai/hosting.json all exist.
- R2: .github/workflows/pages.yml is unchanged (`git diff` empty); the `?social-preview` inline script and the 1200x627 CSS are intact in index.html; the preview rendered at 1200x627 and the og-image step needs only a non-empty file.
- Constraints: no new dependency (@phosphor-icons/react removed from package.json and the lock; fonts are a `<link>`, not a package); the Sites worker, prepare script and sites-worker test are untouched; the Markdown handling is three small slicers for the exact shapes in the two files, not a renderer.
- Scope: every changed site file maps to a plan.md row; `vite.config.mjs` `fs.allow` is needed for the dev server to serve the build-time imports.

## Not checked
- Browser rendering at 1440 and 375, zoom, clipboard permission behaviour and the live GA request sequence (QA scenarios S2 to S4, S8, S10 own these; their evidence folders were still empty when I read them).
- Whether the three tested install routes behaved as contract.md records: there is no transcript in the task folder, so I took the contract's statement as given.
- Security, correctness of the React code paths beyond the contract, and simplicity (other lenses).
