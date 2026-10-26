Bug: importing the same CSV twice doubles every contact whose email has capitals or stray spaces (`" Bob@Example.com"`).

Expected behaviour of `node bin/import.js <file.csv> --db <crm.json>`:
- A contact's identity is its email trimmed and lowercased. A contact already in the store, or earlier in the same file, is skipped.
- The stored email is the first-seen spelling with spaces trimmed (`Bob@Example.com`), not lowercased.
- A row whose email has no `@` is not imported: it prints `row <n>: invalid email` on stderr (n counts data rows from 1, the header is not a row) and the import goes on.
- The last line on stdout is `added <a>, skipped <s>, invalid <i>` (skipped = duplicates). Importing the same file again prints `added 0, ...` and changes nothing.
- Quoted fields keep working as now.
