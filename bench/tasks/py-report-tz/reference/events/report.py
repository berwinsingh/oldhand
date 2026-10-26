from datetime import date
from zoneinfo import ZoneInfo


def between(events, start, end, config):
    """Events whose local day (in config["tz"]) falls between start and end inclusive, oldest first."""
    lo = date.fromisoformat(start)
    hi = date.fromisoformat(end)
    tz = ZoneInfo(config.get("tz", "UTC"))
    out = []
    for at, name in sorted(events):
        day = at.astimezone(tz).date()
        if lo <= day <= hi:
            out.append((day.isoformat(), name))
    return out
