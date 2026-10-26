import argparse
import json
import sys

from . import export

FIELDS = ["name", "email", "company", "notes"]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="contacts")
    ap.add_argument("--data", default="contacts.json")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--format", choices=["csv", "tsv"], default="csv")
    e.add_argument("--out", help="file to write (default: stdout)")
    args = ap.parse_args(argv)

    with open(args.data, encoding="utf-8") as fh:
        rows = json.load(fh)
    text = export.render(rows, FIELDS, args.format)
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
