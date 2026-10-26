import json
import os
from datetime import datetime, timezone


def parse_time(text):
    """ISO 8601 with an offset or a trailing Z, returned as an aware UTC datetime."""
    try:
        at = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("not an ISO 8601 time: %r" % text)
    if at.tzinfo is None:
        raise ValueError("time needs an offset or Z: %r" % text)
    return at.astimezone(timezone.utc)


def add(db, at, name):
    when = parse_time(at)
    with open(db, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": when.isoformat(), "name": name}) + "\n")


def load(db):
    if not os.path.exists(db):
        return []
    out = []
    with open(db, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                row = json.loads(line)
                out.append((parse_time(row["at"]), row["name"]))
    return out
