# Learned: site rebuild (2026-10-11)

Written where: this file, and the lead's project memory note `oldhand-skill-pack.md` (the host's memory directory; the repository keeps no agent instruction file beyond site/AGENTS.md, which now carries the content rule).

- Run review before QA, not alongside it. The review's fix round changed the page, which made every QA result taken in parallel stale; five scenarios had to be re-run. The pack's order (review, then qa) exists for this reason.
- In zsh, a variable holding `python3 path/to/ledger.py` is one word; `$L init` fails with "no such file". Define a shell function (`L() { python3 ... "$@"; }`) instead. The trial agent hit the same thing.
- A macOS sleep kills running sub-agents mid-response; the host's keep-awake request (session_idle) prevents it for the rest of the session.
- Sub-agents can drive the host's built-in browser pane, but they share one pane: a reviewer that started its own preview server navigated a QA agent's tab. Web scenarios stay one at a time, and reviewers should be told not to open the pane.
- `mutate.py` reports ERROR, not KILLED, when the mutation does not parse (a dangling `else`); pick a mutation that keeps the file valid, and void the inconclusive check so it is listed but never counted.
- Vite's `server.fs.allow` entries resolve against the Vite root; `[".."]` exposes the whole repository (including `.oldhand/`) on a dev server bound to all interfaces. List the imported folders instead.
- A build-time import does not stop a page from drifting: the heading slice returns empty and the build still passes. A source check in the build script (`scripts/check-sources.mjs`) is what fails it.
- "Tested" on a page means the exact command was run; a route sketched from documentation (the git-clone loop) reads as tested until someone runs it. The contract lens caught it.
