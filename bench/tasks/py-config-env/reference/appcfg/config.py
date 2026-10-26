import json

PREFIX = "APP_"
NESTED = "APP__"
TRUE = ("1", "true")
FALSE = ("0", "false")


class ConfigError(ValueError):
    pass


def coerce(name, raw, current):
    """Convert an environment string to the type of the value it replaces."""
    try:
        if isinstance(current, bool):
            low = raw.lower()
            if low in TRUE:
                return True
            if low in FALSE:
                return False
            raise ValueError(raw)
        if isinstance(current, int):
            return int(raw)
        if isinstance(current, float):
            return float(raw)
    except ValueError:
        raise ConfigError("%s=%r is not a valid %s" % (name, raw, type(current).__name__))
    return raw


def set_path(cfg, name, parts, raw):
    node = cfg
    for part in parts[:-1]:
        if not isinstance(node.get(part), dict):
            node[part] = {}
        node = node[part]
    last = parts[-1]
    node[last] = coerce(name, raw, node[last]) if last in node else raw


def apply_env(cfg, environ):
    for name, raw in sorted(environ.items()):
        if name.startswith(NESTED):
            parts = [p.lower() for p in name[len(NESTED):].split("__") if p]
            if parts:
                set_path(cfg, name, parts, raw)
        elif name.startswith(PREFIX):
            key = name[len(PREFIX):].lower()
            if key in cfg:
                cfg[key] = coerce(name, raw, cfg[key])
    return cfg


def load(path, environ):
    with open(path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    return apply_env(cfg, environ)
