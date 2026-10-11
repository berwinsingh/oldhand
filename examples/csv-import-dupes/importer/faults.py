"""Fault injection for chaos testing.

IMPORTER_FAULTS="progress:1,insert:2" makes the named step raise a transient
"database is locked" error the first N times it runs in this process.
Unset in production.
"""
import os
import sqlite3

_seen = {}


def _plan():
    plan = {}
    for part in os.environ.get("IMPORTER_FAULTS", "").split(","):
        if ":" in part:
            step, n = part.split(":", 1)
            plan[step.strip()] = int(n)
    return plan


def maybe_fail(step):
    budget = _plan().get(step, 0)
    if _seen.get(step, 0) < budget:
        _seen[step] = _seen.get(step, 0) + 1
        raise sqlite3.OperationalError("database is locked")


def reset():
    _seen.clear()
