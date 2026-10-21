# Site instructions

The page shows the real thing. Its content comes from the repository at build
time: `skills/oldhand/SKILL.md`, `examples/*/oldhand/report.md` and
`.claude-plugin/plugin.json` are imported, never copied. Never invent ids,
screenshots, results, badges or checkmarks. An install command appears on the
page only after someone has run it, with the tool version and date it was run.

Run the local server yourself (`npm run dev`) and open the preview in the
browser available to this environment; do not hand the user server-start
instructions when you can run it.

Keep `.openai/hosting.json`, `worker/index.js`, `scripts/prepare-sites-build.mjs`
and `tests/sites-worker.test.mjs` intact so the same build can be handed to
Sites. Before a handoff run `npm run build`, `npm test` and `npm run test:sites`;
the build must leave `dist/client/index.html`, `dist/server/index.js` and
`dist/.openai/hosting.json`. The Pages workflow screenshots `?social-preview=1`
at 1200 x 627, so the hero must fit that box.
