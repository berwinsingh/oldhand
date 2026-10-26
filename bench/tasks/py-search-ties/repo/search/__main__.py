import argparse
import json
import sys

from . import index, paging, rank


def main(argv=None):
    ap = argparse.ArgumentParser(prog="search")
    ap.add_argument("query")
    ap.add_argument("--data", default="articles.json")
    ap.add_argument("--page", type=int, default=1)
    ap.add_argument("--per-page", type=int, default=5)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args(argv)

    with open(args.data, encoding="utf-8") as fh:
        articles = {a["id"]: a for a in json.load(fh)}
    idx = index.build(articles.values())
    hits = rank.ranked(idx, articles, args.query)
    shown = hits if args.all else paging.page(hits, args.page, args.per_page)
    print("%d results" % len(hits))
    for doc_id, score in shown:
        print("%s  %d  %s" % (doc_id, score, articles[doc_id]["title"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
