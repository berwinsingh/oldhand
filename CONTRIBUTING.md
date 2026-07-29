# Contributing to Oldhand

Questions and ideas belong in [Discussions](https://github.com/berwinsingh/oldhand/discussions). Reproducible bugs belong in [Issues](https://github.com/berwinsingh/oldhand/issues). Report vulnerabilities privately through the [Security tab](https://github.com/berwinsingh/oldhand/security/advisories/new).

## Pull requests

1. Fork the repository and branch from `main`.
2. Keep the change focused. Reuse existing files and platform features before adding code or dependencies.
3. Keep the Claude and Codex manifests aligned when changing shared plugin behavior.
4. Run:

   ```sh
   ./scripts/smoke-test.sh
   ```

5. If `site/` changed, also run:

   ```sh
   cd site
   npm ci --no-audit --no-fund
   npm run build
   npm run test:sites
   ```

6. Open a pull request that explains the problem, the change, and the verification.

`main` is protected. Every change must pass the repository validation check before it can merge.

By contributing, you agree that your contribution is licensed under the repository's MIT License.
