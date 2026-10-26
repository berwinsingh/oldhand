# search

Full-text search over the help-centre articles in `articles.json`.

    python3 -m search "garden hose"                  # page 1, 5 per page
    python3 -m search "garden" --page 2 --per-page 3
    python3 -m search "garden" --all

Output: a header line `<n> results`, then one `<id>  <score>  <title>` line per result.
Run the tests with `python3 -m unittest discover -s tests`.
