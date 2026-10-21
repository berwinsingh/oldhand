# Trace: the Oldhand website

Static site. No server, auth, persistence or queue. Every hop below was read, not inferred.

## Hop table

| hop | where | what happens | timeout x retries | failure mode |
| --- | --- | --- | --- | --- |
| 1 visitor | https://berwinsingh.github.io/oldhand/ | GitHub Pages serves `dist/client/index.html` built from `site/` | n/a | stale deploy until the next push to main that touches `site/**` |
| 2 deploy | `.github/workflows/pages.yml:1-81` | on push to main (paths `site/**`): node 22, `npm ci`, `npm run build`, `vite preview` on 127.0.0.1:4173, headless Chrome screenshots `?social-preview=1` at 1200x627 into `dist/client/og-image.png` (`test -s`), uploads `dist/client` | preview wait 30 x 1s | `og-image.png` empty or missing fails the build; the social-preview hook in `index.html` must survive |
| 3 build | `site/package.json:6-11`, `site/vite.config.mjs` | `vite build` (base `./`, outDir `dist/client`) then `scripts/prepare-sites-build.mjs` copies `worker/index.js` and `.openai/hosting.json` into `dist/` | n/a | the Sites test `tests/sites-worker.test.mjs:58-62` needs all three dist files |
| 4 html | `site/index.html` | meta, OG and Twitter tags, favicon, canonical; inline script adds `html.social-preview` on `?social-preview`; inline CSS pins 1200x627 and hides `.analytics-consent`; loads `/src/main.jsx` | n/a | title and description still say 1.x and "Claude Code and ChatGPT Codex" |
| 5 app | `site/src/main.jsx` -> `site/src/App.jsx` | renders the page; `InstallPanel` tabs with `CopyButton` (clipboard with `execCommand` fallback); `AnalyticsConsent` overlay | n/a | 626 lines, 21 Phosphor icons, 2.9 MB of PNGs |
| 6 analytics | `App.jsx:111-160, 299-306` | `readAnalyticsChoice` (localStorage, try/catch) -> `loadAnalytics` only when `granted`: pushes consent default denied, then update granted, injects gtag script `G-75YW6HE9FT` | n/a | correct and opt-in today; only the overlay is the problem |
| 7 fonts | `styles.css:1` | `@import` Google Fonts (Archivo Black, Archivo Narrow, Space Mono) | browser default | render-blocking import in CSS; fallback fonts |
| 8 external links | `App.jsx` | GitHub repo, README anchors, LICENSE | n/a | README anchors change with the rewrite |

## Readers and callers of what changes

- `scripts/smoke-test.sh`: the 1.x version grepped `App.jsx` for the GA id and "Analytics preferences". The 2.0 version (rewritten by the pack build) no longer greps the site. Verify before build.
- `site/tests/sites-worker.test.mjs`: reads `dist/` outputs only; unchanged.
- `site/AGENTS.md`: tells future agents the generated mock is the source of truth; this is the root cause of the look and must change.
- `README.md`: links to the site; its install section must match the tabs.
- `.codex-plugin/plugin.json` `brandColor`: now `#b4441c`, the site accent must match.

## Config the runtime reads

`import.meta.env.BASE_URL` = `./` (vite base). The dev server blocks imports outside `site/` unless `server.fs.allow` includes `..`; `vite build` has no such restriction. New build-time imports: `../../skills/oldhand/SKILL.md?raw`, `../../examples/csv-import-dupes/oldhand/report.md?raw`, `../../.claude-plugin/plugin.json`.

## Trust boundaries

None server-side. Third parties: Google Fonts (always), googletagmanager (opt-in only), GitHub (links). Page content is static; no user input is stored except the analytics choice and the chosen install tab in localStorage.

## Existing helpers to reuse

`CopyButton`, `readAnalyticsChoice`, `saveAnalyticsChoice`, `loadAnalytics` (move to `src/analytics.js` so a node test can import them), the social-preview hook, `prepare-sites-build.mjs`.

Sanity: 6 files change for 8 hops; hops 1 to 3 and 6 to 8 are kept as they are.
