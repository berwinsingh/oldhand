Bug: `python3 -m events report --from 2026-03-01 --to 2026-03-10` leaves out the events from March 10.

Expected behaviour:
- `--from` and `--to` are inclusive calendar days.
- Days are calendar days in the timezone set in `config.json` (`"tz"`), so each event counts on its local date there, not its UTC date.
- Keep the CLI flags and the output format (`<day> <name>` lines, then `total: <n>`).
