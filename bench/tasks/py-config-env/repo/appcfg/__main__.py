import argparse
import json
import os
import sys

from . import config


def flatten(obj, prefix=""):
    for key in sorted(obj):
        path = prefix + key
        if isinstance(obj[key], dict):
            yield from flatten(obj[key], path + ".")
        else:
            yield path, obj[key]


def main(argv=None, environ=None):
    ap = argparse.ArgumentParser(prog="appcfg")
    ap.add_argument("--config", default="config.json")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show")
    s.add_argument("--json", action="store_true")
    s.add_argument("--key", help="dotted path, e.g. db.port")
    args = ap.parse_args(argv)

    cfg = config.load(args.config, os.environ if environ is None else environ)
    if args.key:
        node = cfg
        for part in args.key.split("."):
            node = node[part]
        print(json.dumps(node))
    elif args.json:
        print(json.dumps(cfg, indent=2, sort_keys=True))
    else:
        for path, value in flatten(cfg):
            print("%s = %s" % (path, json.dumps(value)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
