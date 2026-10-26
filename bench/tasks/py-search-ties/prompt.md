Bug: `python3 -m search "garden" --page 2` sometimes repeats results already shown on page 1, and some articles never show up on any page.

Expected behaviour:
- Results are ordered by score, highest first. Ties are broken by article id in natural order: `doc-2` comes before `doc-10`.
- For any `--per-page`, every result appears on exactly one page, and the same query always gives the same pages.
- `--all` lists exactly the pages one after another.
- The header line `<n> results` counts each article once.
- Scoring stays as it is: +2 for each query word in the title, +1 in the body. Keep the output format.
