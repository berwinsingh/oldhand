# Review: site rebuild

Panel: contract, correctness, security, simplicity (read-only worker sub-agents, Sonnet class), one round. Chair: the lead. The security lens was relaunched once after the host machine slept mid-run.

| lens | high | medium | low | survived (recorded) |
| --- | --- | --- | --- | --- |
| contract | 1 | 5 | 6 | F1, F2, F3, F4 (+F5, F6 shared with correctness) |
| correctness | 0 | 3 | 7 | F5, F6, F7 |
| security | 0 | 0 | 4 | none at medium or above |
| simplicity | 0 | 1 | 3 | F8 |

Chair's refutations and merges:
- contract 12 (README hunks beyond the install section): refuted. This pull request carries the pack and the site together; the README intro and model sections belong to the pack commit.
- contract 5 and correctness 1 (Pages trigger paths) merged into F5. The contract listed the workflow as out of scope; the chair added the trigger list to the scope because the page imports files outside site/ and the build and screenshot steps stay untouched (R2 still holds).
- contract 6 and correctness 2 (silent empty slice) merged into F6.
- security 2 and correctness 3 (copy fallback) merged into F7.
- correctness low (social card crops mid-row) and contract 11: same item, folded in.

All eight survivors are fixed (see `ledger.py status`). Lows folded into the same fix because each was one or two lines in a file already being changed: "Copy raw" label; "for example" on the invocation lines; footer says "Google Analytics" with the disclosure link and "nothing is sent" when off; social card hides the panel detail below the first command; modifier keys no longer hijack the arrow handler; the SKILL.md box and the tables are keyboard-scrollable (tabIndex) and tables keep their table role; the dead `data-theme` CSS block is gone; `columns` is required; install-tab persistence dropped (the `?agent=` deep link stays); the criteria table slice no longer drops its last row when the table ends the file; the dev server's file allow-list is narrowed to the three imported folders.

Lows deferred as follow-ups (not in this change): the copy status should live in a sibling `role="status"` outside the button for screen readers; turning analytics off leaves the `_ga` cookies in place; Google Fonts load before any choice (self-host the two families); the `npx skills` command is unpinned while the tested line names 1.7.2; a CSP or SRI cannot be set on GitHub Pages (noted, not a defect).

Review-proof criteria, judged by the chair after the fixes:
- AC3 (no invented artifact; claims link to their source): pass. The stamp, fake screenshot, fake ids, checkmarks and badges are gone; the remaining example ticket id is labelled "for example"; every factual block links to the file it comes from or is sliced from it at build time.
- R2 (Pages workflow steps unchanged; the social-preview hook renders at 1200x627): pass. Only the `paths` trigger list changed; the build, preview and screenshot steps are as before, and the hook survives in index.html.
