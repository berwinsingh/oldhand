import json

PREFIX = "APP_"


def coerce(raw, current):
    """Convert an environment string to the type of the value it replaces."""
    if isinstance(current, bool):
        return raw.lower() in ("1", "true", "yes", "on")
    if isinstance(current, int):
        return int(raw)
    if isinstance(current, float):
        return float(raw)
    return raw


def apply_env(cfg, environ):
    for name, raw in environ.items():
        if name.startswith("APP__"):
            node = cfg
            parts = name[5:].lower().split("__")
            for part in parts[:-1]:
                node = node[part]
            if parts[-1] in node:
                node[parts[-1]] = coerce(raw, node[parts[-1]])
        elif name.startswith(PREFIX):
            key = name[len(PREFIX):].lower()
            if key in cfg:
                cfg[key] = coerce(raw, cfg[key])
    return cfg


def load(path, environ):
    with open(path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    return apply_env(cfg, environ)
