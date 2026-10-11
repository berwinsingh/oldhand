"""Retry wrapper for transient storage errors."""
import sqlite3
import time

TRANSIENT = ("database is locked", "database is busy")


def is_transient(exc):
    return isinstance(exc, sqlite3.OperationalError) and any(t in str(exc) for t in TRANSIENT)


def with_retries(fn, retries=3, delay=0.05, log=None):
    """Call fn() and retry it up to `retries` more times on a transient error."""
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            if not is_transient(exc) or attempt >= retries:
                raise
            attempt += 1
            if log:
                log("transient error (%s), retry %d/%d" % (exc, attempt, retries))
            time.sleep(delay * attempt)
