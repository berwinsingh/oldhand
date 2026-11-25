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

The page is built on Astryx with the `oldhand` theme (themes/oldhand, changed only through
`npx astryx experimental theme editor`). The rules above win over the generated ASTRYX block
below: this page keeps its own editorial layout (semantic HTML and CSS grid, not a page template)
and `styles.css` may alias theme tokens on `:root`, but it never defines colours of its own.

Astryx 0.7.17 behaviour seen on this page (2026-11-23):
- `Table` sets its min-width from the column weights (about 64px per `proportional()` weight), not
  from each column's `minWidth`; keep the weights small on narrow screens.
- `TabList role="tablist"` moves focus on the arrow keys, Home and End but does not select; make
  selection follow focus (`onFocus`), never add a second arrow-key handler.
- `Collapsible`'s trigger has a fixed-height inner wrapper: size the tap target on
  `.astryx-collapsible-trigger`, not on the trigger content.
- `CodeBlock isWrapped` breaks inside words (`--s`/`kill`); leave it off for shell commands.

<!-- ASTRYX:START -->
Astryx v0.7.17 · 174 components
CLI: run every command as `npx astryx <cmd>` (shown below as `astryx ...`).

SETUP (once, in app entry e.g. main.tsx) — without these, components render unstyled:
  import "@astryxdesign/core/reset.css";
  import "@astryxdesign/core/astryx.css";

WORKFLOW — start every page from a template, never from scratch:
1. `astryx build "<idea>"` — names the template to scaffold from and the parts it lacks.
2. `astryx template <name> <path>` — scaffold it; keep its frame, gap and padding; replace the content.
3. `astryx component <Name>` to read props before using one; `astryx template <Block>` prints a block example to read for a part it lacks. Astryx names differ from other libraries: buttons, badges, tokens and tabs take their text in `label` (Text, Heading and Link take children), booleans start with `is` or `has` (`isOpen`, `isDisabled`), and every input takes `value` and `onChange`.
Changing an existing page? Keep it: skip step 2 and add components inside its sections; read a block example when it helps.
Before you deliver a build, run `astryx doctor --built <dir>`; don't deliver it if it fails.

RULES:
- No <div> — components handle all layout and spacing.
- Read `astryx docs layout` before changing a template's frame.
- Dense data = rows (Table, List/Item), not Card-wrapped lists. Badge = counts only.
- Style with component props first, then tokens (var(--color-*|--spacing-*|--radius-*)). No raw hex/px. No StyleX/Tailwind compiler here — don't use xstyle/utility classes directly. Some templates use StyleX and need a compiler plugin; see `astryx docs styling-overview`.
- THEMES: palettes and custom colors go through the theme, never :root overrides; so does a denser or roomier app (`editor set <name> spacing tight`), never gap and padding changes page by page. A change to one kind of part (the sidebar, its selected item, the gaps in a form) is a theme change too, not props on one page: `editor how "<ask>"` names the `set … --on <part>` line. No app yet: `astryx experimental theme preview app <dir>` makes a starter app that shows the theme. To make or change a theme (colors, fonts, corners, spacing, a look from a picture), prefer the experimental theme editor over hand-written theme files: `astryx experimental theme editor new <name> --like neutral`, then `editor set <name> <thing> <value>` or `editor how "<what you want>"`; wire it with `astryx theme add <name>`; after each change look at it with `astryx experimental theme editor show <name> --png` (takes pictures of real components) and open the PNGs it writes; a theme change is not done until you have looked at the pictures. In code, extend an imported theme to customize it; `theme eject <slug>` only forks source. See `astryx docs theme`.
- SELF-CHECK: re-read the file; replace any raw <div>/<span>, imported .css/@apply, or hardcoded #hex/px with the component or a token.

`astryx help` lists every command. Key ones beyond the workflow:
  search "<query>"   find any component / hook / doc / template
  discover <words>   integrations you could add
  docs <topic>       getting-started, principles, tokens, theme … (`astryx docs` lists all)
  docs cli           commands and API reference
  docs authoring     build an integration package, and every field it holds
  upgrade --from <old version> --apply   run after a dependency bump
To remove this block, run `astryx init --remove-agents`, which removes it from the agent files at the project root and in the folder you run it in; from any other file it leaves, delete everything from ASTRYX:START to ASTRYX:END.
<!-- ASTRYX:END -->
