import argparse
import sys

from . import data, invoices, orders, reports


def main(argv=None):
    ap = argparse.ArgumentParser(prog="shop")
    ap.add_argument("--data", default="orders.json")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("order").add_argument("id", type=int)
    sub.add_parser("invoice").add_argument("id", type=int)
    sub.add_parser("report").add_argument("month", help="YYYY-MM")
    args = ap.parse_args(argv)

    all_orders = data.load(args.data)
    if args.cmd == "report":
        print(reports.monthly(all_orders, args.month))
        return 0
    order = data.find(all_orders, args.id)
    if order is None:
        print("error: no order %d" % args.id, file=sys.stderr)
        return 2
    print(orders.confirmation(order) if args.cmd == "order" else invoices.render(order))
    return 0


if __name__ == "__main__":
    sys.exit(main())
