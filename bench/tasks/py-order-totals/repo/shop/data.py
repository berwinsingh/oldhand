import json


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def find(all_orders, order_id):
    return next((o for o in all_orders if o["id"] == order_id), None)
