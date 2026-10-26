Bug: a contact whose company is `Acme, Inc.` shifts every column after it to the right when the CSV export is opened in a spreadsheet.

Expected behaviour of `python3 -m contacts export --format csv`:
- Valid RFC 4180 CSV that Python's `csv` module and Excel read back to the same values: a field that contains a comma, a double quote or a line break is quoted, with inner double quotes doubled.
- These files get opened in Excel, so any cell that starts with `=`, `+`, `-` or `@` gets a leading single quote `'` so it can't run as a formula.
- The header row stays `name,email,company,notes`, and non-ASCII text is kept as is.
- TSV export keeps working as before for ordinary values.
