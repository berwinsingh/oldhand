# events

A tiny event log. Events are stored in UTC in `events.jsonl`; `config.json` holds the team's timezone.

    python3 -m events add --at 2026-03-10T15:00:00Z --name standup
    python3 -m events report --from 2026-03-01 --to 2026-03-31

Run the tests with `python3 -m unittest discover -s tests`.
