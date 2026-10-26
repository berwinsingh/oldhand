from datetime import date


def between(events, start, end, config):
    """Events whose day falls between start and end, oldest first."""
    lo = date.fromisoformat(start)
    hi = date.fromisoformat(end)
    out = []
    for at, name in sorted(events):
        day = at.date()
        if lo <= day <= hi:
            out.append((day.isoformat(), name))
    return out
