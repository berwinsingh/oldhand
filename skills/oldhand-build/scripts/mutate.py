#!/usr/bin/env python3
"""Mutation check for Oldhand build. Standard library only, no network, never calls git.

It proves a regression check guards a fix: it breaks the fixed line on purpose, runs
the check, and puts the file back byte for byte.

    python3 mutate.py --file src/x.py --find "return a + b" --replace "return a - b" \\
        --test "python3 -m pytest tests/test_x.py -q" [--timeout 90] [--error-pattern REGEX] \\
        [--ledger .oldhand/<task> --id AC1]

1. Takes a lock on the file (one run per file at a time), copies the file to a new temp
   folder outside the worktree, notes its sha256, and prints the backup path and the
   command that copies it back, before anything changes.
2. Runs --test on the untouched file (the control run). It must pass, or the run stops
   with ERROR: a check that fails or runs no tests anyway proves nothing.
3. Replaces --find with --replace. --find must match exactly once, or nothing changes.
4. Runs --test through the shell from the current folder, with PYTHONDONTWRITEBYTECODE=1
   so no bytecode of the broken file outlives the run. Output goes to a temp file, so a
   helper the test leaves running cannot hold the run open.
5. Always copies the original bytes back (also on Ctrl-C, SIGTERM, SIGHUP, a timeout or a
   crash), ends every process the test started, and checks the sha256 matches. If the file
   changed while the test ran, it is left as it is; the backup and the lock are kept.

The check runs twice, so give the host's command timeout more than twice --timeout.

Results and exit codes:
  0 KILLED    the test command failed with the line broken: the check guards it. You want this.
  1 SURVIVED  the test command passed with the line broken: the check does not guard it.
  2 ERROR     inconclusive: the check fails or does not run on the untouched file, the output
              matched the error pattern (syntax, import, collection or compile error, no tests
              ran), pytest exited 4 or 5, the command could not start, or it timed out.
  3           usage problem (nothing was changed), interrupted, or the restore failed.
The last 40 lines of the test output are printed. With --ledger and --id, the result is
recorded as kind mutation (KILLED pass, SURVIVED fail, ERROR blocked).
"""

import argparse
import contextlib
import hashlib
import importlib.util
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile

DEFAULT_ERROR_PATTERN = (
    r"ERROR collecting|errors? during collection|ImportError while importing|file or directory not found"
    r"|\b(?:SyntaxError|IndentationError|TabError|ModuleNotFoundError)\b|Cannot find module"
    r"|error TS\d+|build failed|setup failed|could not compile"
    r"|no tests ran|NO TESTS RAN|Ran 0 tests|No tests found|(?m:^=*\s*\d+ deselected in\b)"
)
NO_RUN_EXITS = {4: "pytest usage error", 5: "pytest collected no tests", 126: "could not start",
                127: "command not found"}
TAIL = 40
RESULT_EXIT = {"KILLED": 0, "SURVIVED": 1, "ERROR": 2}
LEDGER_STATUS = {"KILLED": "pass", "SURVIVED": "fail", "ERROR": "blocked"}
STOP_SIGNALS = [getattr(signal, n) for n in ("SIGTERM", "SIGHUP", "SIGBREAK") if hasattr(signal, n)]


class UsageError(Exception):
    pass


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _worktree_root(path):
    """The nearest folder above path that holds a .git entry, found without calling git."""
    d = os.path.dirname(os.path.abspath(path))
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def _inside(path, folder):
    path, folder = os.path.realpath(path), os.path.realpath(folder)
    try:
        return os.path.commonpath([path, folder]) == folder
    except ValueError:
        return False


def _ledger():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "oldhand", "scripts", "ledger.py")
    if not os.path.isfile(path):
        raise UsageError("ledger.py not found at %s: install the whole oldhand pack, or drop --ledger"
                         % os.path.normpath(path))
    spec = importlib.util.spec_from_file_location("oldhand_ledger", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def lock_path(path):
    key = hashlib.sha256(os.path.realpath(path).encode("utf-8", "surrogateescape")).hexdigest()[:16]
    return os.path.join(tempfile.gettempdir(), "oldhand-mutate-lock-%s" % key)


def _take_lock(path):
    lock = lock_path(path)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        try:
            with open(lock, encoding="utf-8", errors="replace") as fh:
                held = " ".join(fh.read().split())
        except OSError:
            held = "unreadable"
        raise UsageError("another mutate.py run on %s holds the lock %s (%s). Run mutations one at a time. If no run "
                         "is active, one was killed: compare %s with the backup named in the lock, copy the "
                         "original back if needed, then delete the lock" % (path, lock, held, path))
    with os.fdopen(fd, "w") as fh:
        fh.write("pid %d\n" % os.getpid())
    return lock


def _kill(proc):
    """End the test command and everything it started in its process group (its process tree on Windows)."""
    try:
        if os.name == "posix":
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=30)
    except (OSError, subprocess.SubprocessError):
        pass
    with contextlib.suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=10)


def run_test(cmd, timeout):
    """(exit code or None on timeout, output text)."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    extra = {"start_new_session": True} if os.name == "posix" else {}
    with tempfile.TemporaryFile() as out:  # a file, not a pipe: a left-over helper cannot keep the run waiting
        proc = subprocess.Popen(cmd, shell=True, stdout=out, stderr=subprocess.STDOUT, env=env, **extra)
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            code = None
        except BaseException:  # Ctrl-C, or a host signal turned into KeyboardInterrupt
            _kill(proc)
            raise
        if code is None or os.name == "posix":
            _kill(proc)  # on posix this also ends helpers the test left in its process group
        out.seek(0)
        return code, out.read().decode("utf-8", "replace")


def _restore(path, backup, sha, mutant, lock):
    """Copy the backup bytes back and verify them. True when the file matches the original."""
    try:
        with open(path, "rb") as fh:
            if fh.read() != mutant:
                sys.stderr.write("\nNOT RESTORED: %s changed while the test ran (an edit, or another run), so it was "
                                 "left as it is.\nThe original is kept at %s and the lock %s stays.\nCompare the two, "
                                 "put back what is right by hand, then delete the lock.\n" % (path, backup, lock))
                return False
        with open(backup, "rb") as fh:
            original = fh.read()
        with open(path, "wb") as fh:
            fh.write(original)
        with open(path, "rb") as fh:
            ok = _sha(fh.read()) == sha
    except OSError as e:
        sys.stderr.write("restore error: %s\n" % e)
        ok = False
    if ok:
        shutil.rmtree(os.path.dirname(backup), ignore_errors=True)
        return True
    sys.stderr.write("\nRESTORE FAILED: %s does not match the original.\nThe original is kept at %s\n"
                     "Copy it back by hand before anything else: %s\nThen delete the lock %s\n"
                     % (path, backup, _copy_cmd(backup, path), lock))
    return False


def _copy_cmd(src, dst):
    return ('copy /Y "%s" "%s"' if os.name == "nt" else "cp '%s' '%s'") % (src, dst)


@contextlib.contextmanager
def _signals_held():
    """Hold back Ctrl-C and stop signals while the original bytes are written back; they act right after."""
    mask = getattr(signal, "pthread_sigmask", None)
    sigs = set(STOP_SIGNALS + [signal.SIGINT])
    old = mask(signal.SIG_BLOCK, sigs) if mask else None
    try:
        yield
    finally:
        if mask:
            mask(signal.SIG_SETMASK, old)


def classify(code, output, pattern):
    """(result, reason)"""
    if code is None:
        return "ERROR", "the test command timed out, so the run is inconclusive (raise --timeout if it is just slow)"
    if code in NO_RUN_EXITS:
        return "ERROR", "the test command ran no check (exit %d, %s): fix the command" % (code, NO_RUN_EXITS[code])
    if code == 0:
        return "SURVIVED", "the test command passed with the line broken: the check does not guard this line"
    m = re.search(pattern, output)
    if m:
        return "ERROR", ("the output matched the error pattern (%r): a syntax, import, collection or compile error "
                         "is not a kill; choose a mutation that still runs" % m.group(0))
    return "KILLED", "the test command failed with the line broken (exit %d): the check guards it" % code


def run(path, find, replace, test, timeout=90, error_pattern=None, ledger_dir=None, cid=None, notice=None):
    """Control run, mutation, test, restore. Returns (result, reason, output, restored).
    notice(text) is called with the backup path and the copy-back command before anything changes."""
    if not os.path.isfile(path):
        raise UsageError("no such file: %s" % path)
    if not find:
        raise UsageError("--find is empty: give the exact text of the line to break")
    if find == replace:
        raise UsageError("--replace is the same as --find: that would test nothing")
    if not test.strip():
        raise UsageError("--test is empty: give the command that runs the regression check")
    if timeout <= 0:
        raise UsageError("--timeout must be more than 0 seconds")
    pattern = error_pattern or DEFAULT_ERROR_PATTERN
    try:
        re.compile(pattern)
    except re.error as e:
        raise UsageError("--error-pattern is not a valid regular expression: %s" % e)
    if bool(ledger_dir) != bool(cid):
        raise UsageError("--ledger and --id go together: give both or neither")
    led = None
    if ledger_dir:
        led = _ledger()
        ledger_dir = led.resolve_dir(ledger_dir)
        try:
            led.criterion(led.load(ledger_dir), cid)
        except led.LedgerError as e:
            raise UsageError(str(e))
    lock = _take_lock(path)
    safe, backup_dir = True, None  # safe: the file holds the original bytes, so the lock can go
    try:
        with open(path, "rb") as fh:
            data = fh.read()
        fb, rb = find.encode("utf-8"), replace.encode("utf-8")
        n = data.count(fb)
        if n != 1:
            raise UsageError(("--find was not found in %s: copy the exact text from the file, spaces included" % path)
                             if n == 0 else
                             ("--find matches %d times in %s: make it longer so it matches exactly once" % (n, path)))
        sha = _sha(data)
        backup_dir = tempfile.mkdtemp(prefix="oldhand-mutate-")
        root = _worktree_root(path)
        if root and _inside(backup_dir, root):
            raise UsageError("the temp folder %s is inside the worktree %s: set TMPDIR to a folder outside it"
                             % (backup_dir, root))
        backup = os.path.join(backup_dir, os.path.basename(path))
        with open(backup, "wb") as fh:
            fh.write(data)
        with open(backup, "rb") as fh:
            if _sha(fh.read()) != sha:
                raise UsageError("the backup in %s does not match %s; nothing was changed" % (backup_dir, path))
        with open(lock, "a") as fh:
            fh.write("backup %s\n" % backup)
        if notice:
            notice("backup of %s: %s\nIf this run is killed before it says 'restored', copy it back: %s"
                   % (path, backup, _copy_cmd(backup, path)))
        code, output = run_test(test, timeout)  # control run on the untouched file
        if code != 0:
            what = "control run " + ("timed out" if code is None else "exit %d" % code)
            result, reason = "ERROR", ("the check does not pass, or does not run, on the original code (%s): fix the "
                                       "check before testing a mutation" % what)
        else:
            with open(path, "rb") as fh:
                if fh.read() != data:
                    raise UsageError("%s changed during the control run; nothing was mutated. Run again." % path)
            mutant = data.replace(fb, rb, 1)
            safe = False
            try:
                with open(path, "wb") as fh:
                    fh.write(mutant)
                code, output = run_test(test, timeout)
            finally:
                with _signals_held():
                    safe = _restore(path, backup, sha, mutant, lock)
            what = "timed out" if code is None else "exit %d" % code
            result, reason = classify(code, output, pattern)
        restored = safe
    finally:
        if safe:
            if backup_dir:
                shutil.rmtree(backup_dir, ignore_errors=True)
            with contextlib.suppress(OSError):
                os.remove(lock)
    if led and restored:
        ev = "%s: %s: %r -> %r (%s)" % (result, path, find[:80], replace[:80], what)
        try:
            led.record(ledger_dir, cid, "mutation", LEDGER_STATUS[result], ev, "mutate.py", cmd=test)
        except led.LedgerError as e:
            raise UsageError("the result was %s, but recording it failed: %s" % (result, e))
    return result, reason, output, restored


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write("%s: error: %s (run with -h for help)\n" % (self.prog, message))
        sys.exit(3)


def _stop(signum, frame):
    raise KeyboardInterrupt  # so the restore in run() happens when the host ends this process


def main(argv=None):
    for s in (sys.stdout, sys.stderr):  # a Windows pipe defaults to the ANSI code page; test output can hold any text
        with contextlib.suppress(AttributeError, ValueError):
            s.reconfigure(encoding="utf-8", errors="replace")
    ap = _Parser(prog="mutate.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("--file", required=True)
    ap.add_argument("--find", required=True, help="exact text to break; must match exactly once")
    ap.add_argument("--replace", required=True)
    ap.add_argument("--test", required=True, help="the command that runs the regression check")
    ap.add_argument("--timeout", type=float, default=90, help="seconds per run; the check runs twice (default 90)")
    ap.add_argument("--error-pattern", help="regex for inconclusive output (default covers syntax/import/collection/compile)")
    ap.add_argument("--ledger", help="task folder whose ledger.json gets a mutation record")
    ap.add_argument("--id", help="criterion id for the ledger record, like AC1")
    a = ap.parse_args(argv)
    for sig in STOP_SIGNALS:
        signal.signal(sig, _stop)
    try:
        result, reason, output, restored = run(a.file, a.find, a.replace, a.test, a.timeout, a.error_pattern,
                                               a.ledger, a.id, notice=lambda t: print(t, flush=True))
    except UsageError as e:
        print("error: %s" % e, file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        print("interrupted before a result; %s was restored unless a NOT RESTORED or RESTORE FAILED message says "
              "otherwise" % a.file, file=sys.stderr)
        return 3
    except Exception as e:  # never a traceback with exit 1, which reads as SURVIVED
        print("error: %s: %s; %s was restored unless a NOT RESTORED or RESTORE FAILED message says otherwise"
              % (type(e).__name__, e, a.file), file=sys.stderr)
        return 3
    lines = output.rstrip("\n").splitlines()
    print("--- last %d lines of the test output ---" % min(TAIL, len(lines)))
    print("\n".join(lines[-TAIL:]))
    print("---")
    print("%s: %s" % (result, reason))
    if not restored:
        return 3
    print("restored %s (sha256 matches the original)" % a.file)
    if a.ledger:
        print("recorded as a mutation check on %s in %s" % (a.id, a.ledger))
    return RESULT_EXIT[result]


if __name__ == "__main__":
    sys.exit(main())
