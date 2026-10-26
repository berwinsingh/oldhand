Bug: `node bin/slug.js add "Café Menü"` gives `caf-men`.

Expected behaviour:
- Accented Latin letters lose their accent instead of being dropped: é becomes e, ü becomes u, ñ becomes n, Å becomes a.
- A slug is lowercase a-z, 0-9 and single hyphens, with no leading or trailing hyphen.
- Every slug in the store stays unique: a repeat gets the lowest free suffix, `-2`, `-3`, and so on, also when a title's own slug already looks numbered (for example `hello-world-2`).
- A title with no letters or digits at all gets `untitled`, made unique the same way.
- `add` and `list` keep their output.
