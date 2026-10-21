# Contributing to Oldhand

Questions and ideas belong in [Discussions](https://github.com/berwinsingh/oldhand/discussions). Reproducible bugs belong in [Issues](https://github.com/berwinsingh/oldhand/issues). Report vulnerabilities privately through the [Security tab](https://github.com/berwinsingh/oldhand/security/advisories/new).

## How the pack is laid out

Oldhand is a pack of 11 skills under `skills/`: the `oldhand` conductor plus one skill per stage of the chain.

```
contract -> trace -> rca -> research -> plan -> build -> review -> qa -> ship -> learn
```

Each skill does one job, reads and writes the shared `.oldhand/<task>/` folder, and runs on its own. Verdicts come from the stdlib scripts (`skills/oldhand/scripts/ledger.py`, `skills/oldhand-qa/scripts/qa.py`, `skills/oldhand-build/scripts/mutate.py`), never from the model.

## Pull requests

1. Fork the repository and branch from `main`.
2. Keep the change focused. Reuse existing files and platform features before adding code or dependencies.
3. Keep every platform manifest aligned when changing shared plugin behavior: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`, `plugin.json`, and `gemini-extension.json`. A version bump changes all of them together with `metadata.version` in `skills/oldhand/SKILL.md`.
4. Scripts use the Python standard library only and must run on Python 3.8 and later.
5. Run:

   ```sh
   ./scripts/smoke-test.sh
   ```

   It parses every manifest and runs `python3 -m unittest discover -s tests`. The tests check the skill folders, the frontmatter (`name`, `description`, `license`, and `metadata` in the conductor only), body length, the chain line in every skill, that tool paths and script subcommands named in a skill exist, matching versions, and the writing rules: no model version numbers outside `skills/oldhand/references/orchestration.md`, no machine paths, no em dashes.

6. If `site/` changed, also run:

   ```sh
   cd site
   npm ci --no-audit --no-fund
   npm run build
   npm run test:sites
   ```

7. Open a pull request that explains the problem, the change, and the verification.

`main` is protected. Every change must pass the repository validation check before it can merge.

By contributing, you agree that your contribution is licensed under the repository's MIT License.
