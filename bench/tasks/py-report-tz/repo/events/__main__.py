import argparse
import json
import sys

from . import report, store


def main(argv=None):
    ap = argparse.ArgumentParser(prog="events")
    ap.add_argument("--db", default="events.jsonl")
    ap.add_argument("--config", default="config.json")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="record an event")
    a.add_argument("--at", required=True, help="ISO 8601 time, e.g. 2026-03-10T15:00:00Z")
    a.add_argument("--name", required=True)
    r = sub.add_parser("report", help="list events between two days")
    r.add_argument("--from", dest="start", required=True, help="first day, YYYY-MM-DD")
    r.add_argument("--to", dest="end", required=True, help="last day, YYYY-MM-DD")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "add":
            store.add(args.db, args.at, args.name)
            print("added %s" % args.name)
            return 0
        with open(args.config, encoding="utf-8") as fh:
            config = json.load(fh)
        rows = report.between(store.load(args.db), args.start, args.end, config)
    except ValueError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    for day, name in rows:
        print("%s %s" % (day, name))
    print("total: %d" % len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
