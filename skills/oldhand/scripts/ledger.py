#!/usr/bin/env python3
"""The proof ledger for Oldhand. Standard library only, no network.

One JSON file per task, .oldhand/<task>/ledger.json, holds the criteria read from
contract.md, every check anyone ran against them, the review findings and the
restamps. The verdict is computed from that file, never written by hand.

    python3 ledger.py init --dir .oldhand/<task> --title "<title>" [--mode implement]
    python3 ledger.py sync [--dir D]
    python3 ledger.py run --id AC2 --kind unit --by "lead:fable" [--lead] [--live [--max-age 24h]] \\
        [--timeout 600] [--dir D] -- python3 -m pytest tests -q
    python3 ledger.py rerun --stale | --check C7 [--by "lead:fable"] [--dir D]
    python3 ledger.py record --id AC1 --kind e2e --status pass --evidence qa/results/S1.json \\
        --by "lead:fable" --cmd "qa.py scenario S1" [--lead] [--live [--max-age 24h]] [--dir D]
    python3 ledger.py finding add --sev high --lens security --where src/x.py:42 --text "<defect>" [--dir D]
    python3 ledger.py finding resolve --id F3 --how fixed|refuted|deferred --note "<why>" [--accepted-by user] [--dir D]
    python3 ledger.py restamp --check C7 --reason "<why the change since cannot affect it>" [--dir D]
    python3 ledger.py void --check C7 --reason "<why the check no longer applies>" [--dir D]
    python3 ledger.py verdict [--dir D] [--json]
    python3 ledger.py status [--dir D]
    python3 ledger.py report [--dir D]
    python3 ledger.py where [--dir D | --root FOLDER]

Without --dir, every command except init works on the active task: the folder under
.oldhand/ (in the current folder or any folder above it, up to the repo root) whose
ledger.json changed last. `where` prints it. A relative --dir that starts with .oldhand
is taken from the repo root, so a session in a sub-folder finds the same task.

Criteria are the `- AC<n>: ...` (acceptance) and `- R<n>: ...` (existing behaviour that
must keep working) lines of contract.md, each with an optional
`(proof: e2e|integration|unit|review|manual)`. Without one, the proof is e2e in
implement and verify mode and review in plan-only and investigate mode. `sync` adds
new criteria and marks removed ones dropped. When a criterion's text or proof changes,
or it comes back after a drop, checks recorded before that no longer count for it.

`run` is the way to record a check a command can decide (unit, integration, a scripted
e2e): ledger.py runs the command from the project root, saves its output under
<task>/runs/ as the evidence, and sets pass or fail from the exit code. Exit 0 is pass;
anything else, a timeout, or exit 0 with "no tests ran" output is fail; a command that
cannot start records nothing. Values of the vars in .oldhand-env-names (8 characters or
longer) are replaced by <NAME> in the saved output; anything else the command prints is
saved as it is, in the task folder git ignores; a command line that holds such a value
is refused, because the line is stored. The check is recorded on the tree the command
started on, so a file changed while it ran leaves it stale. `rerun --stale` runs every
stale check that `run` recorded again and records the new results. It executes only
commands signed, for this project folder, with this user's rerun key: a random secret
kept outside every project (the state folder, or a private folder in the temp folder).
A ledger.json that came with a repository or an archive cannot make it run anything. `record` stays for results
a command cannot decide: a review, a manual check, a scenario an agent drove (qa.py
records those).

Every record stamps the working-tree fingerprint, "tree:<id>:<extras>". The id is the git
tree of the files as they are on disk (tracked and untracked, non-ignored; .oldhand/ left
out), made with a copy of the index and a temporary object folder, so nothing is written
into the repository. It names content, not a commit: committing the verified files, an
empty commit, an amend or another branch with the same files keep checks fresh, and the
verdict says whether the tree is exactly the HEAD commit's. Extras cover what that tree
does not: nested repos and submodules by their own state, untracked files over 5 MB by
name and size. A check recorded on another fingerprint is stale until it is re-run or
restamped with a reason; the reason names the files that differ. Checks recorded by 2.1
or earlier keep their old fingerprint (commit, diff hash, untracked hash) and are judged
that way. Outside git the fingerprint is "no-git" and file changes are not tracked; the
verdict says so. If git fails where git was in use, that is an error, never "no-git".

Three more things make a check stale; each is stamped only when it applies, so a repo
with none of them records and decides exactly as before:
  runtime  A pin file at the project root (.nvmrc, .node-version, .python-version,
           .ruby-version, .tool-versions, rust-toolchain, rust-toolchain.toml) is hashed,
           ignored by git or not, and the pinned runtime's version is read from the project
           root (`node --version`, `python --version`, ...). A changed, added or removed pin
           file, or a different version now, makes the check stale.
  env      `.oldhand-env-names` at the project root lists env var NAMES, one per line. Each
           record stores a salted PBKDF2 digest of every listed var (or "unset"), never the
           value. A changed value, a var set or unset, or a name added or removed makes the
           check stale. Values are never written, printed or put in the report.
  live     `record --live [--max-age 24h]` marks a check that hit a real external service.
           Older than its max age (default 24h), it is stale. Only timestamps are compared.
restamp clears file changes only; the other three need a re-run.

Verdict, in this order:
  INCOMPLETE  no contract or criteria, or a live criterion has no counted check of its proof kind
  NOT YET     a counted check fails or is stale, a high/medium finding is open or deferred
              without the user's acceptance, or (implement/verify) no current e2e pass by the lead
  BLOCKED     otherwise, a counted check is blocked
  VERIFIED    everything above is clear
e2e satisfies integration and unit, integration satisfies unit; review and manual only
satisfy themselves. --cmd names the check: records with the same --cmd are runs of one
check and only the latest run counts (a baseline-fail run included, which never counts
as a pass). Every counted check must pass, so one scenario's pass never hides another's
fail (qa.py records each scenario as its own check). A voided check (a wrong scenario
that was removed) is listed, never counted.
Evidence that looks like a file path must exist (under the task folder or the repo),
or the check does not count. A record stores a hash of its evidence file: if the file
changes afterwards, or was empty when recorded, the check does not count either.

Exit codes: verdict exits 0 VERIFIED, 1 NOT YET, 2 BLOCKED, 3 INCOMPLETE. run and rerun
exit 0 when every command passed, and 1 when one failed or rerun left a stale check it
could not run. Every other command exits 0 when it worked. Any error exits 4 with a message that says what to do.
Writers lock the task folder, but run ledger commands one after another anyway.
"""

import argparse
import contextlib
import datetime
import hashlib
import hmac
import json
import os
import re
import secrets
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None
    import msvcrt

MODES = ("implement", "plan-only", "investigate", "verify")
KINDS = ("e2e", "integration", "unit", "mutation", "review", "manual")
STATUSES = ("pass", "fail", "blocked", "baseline-fail")
SEVS = ("high", "medium", "low")
HOWS = ("fixed", "refuted", "deferred")
RANK = {"unit": 1, "integration": 2, "e2e": 3}
VERDICT_EXIT = {"VERIFIED": 0, "NOT YET": 1, "BLOCKED": 2, "INCOMPLETE": 3}
ERROR_EXIT = 4

CRITERION = re.compile(r"^- ((?:AC|R)\d+): (.+?)(?: \(proof: (e2e|integration|unit|review|manual)\))?\s*$")
LOOKS_LIKE_CRITERION = re.compile(r"^\s*[-*+]\s*(?:AC|R)\d+\b")
# The Source line of the template, or a line of its own: never a title like "# Dark Mode: ...".
MODE_LINE = re.compile(r"^(?:Source:.*?\s)?Mode:\s*([A-Za-z-]+)", re.M)
PATHISH = re.compile(r"[/\\]|\.[A-Za-z][A-Za-z0-9]{0,4}$")
BIG = 5 * 1024 * 1024
EXCLUDE = ":(exclude,glob)**/.oldhand/**"
NO_EXTRAS = hashlib.sha256(b"").hexdigest()[:16]
TREE_DELTA_MAX = 400  # paths that differ from HEAD, kept per fingerprint so a stale reason can name what changed
NAMES_SHOWN = 5

# run: the kinds a command can prove, its default timeout, how much output is kept from each end, the shell's
# "could not start" exits (9009 is cmd.exe), and output that means a test runner ran nothing.
RUN_KINDS = ("unit", "integration", "e2e")
RUN_TIMEOUT = 600
RUN_KEEP = 1024 * 1024
NOT_STARTED = {126: "it is not executable", 127: "command not found", 9009: "command not found"}
NO_TESTS = re.compile(rb"no tests ran|NO TESTS RAN|\bRan 0 tests\b|No tests found")
REDACT_MIN = 8  # a listed env var's value this long or longer is replaced by <NAME> in saved output

# Runtime pins: the file, the runtime it pins (.tool-versions names its tools inside), and how to read a version.
PIN_FILES = (".nvmrc", ".node-version", ".python-version", ".ruby-version", ".tool-versions",
             "rust-toolchain", "rust-toolchain.toml")
PIN_RUNTIME = {".nvmrc": "node", ".node-version": "node", ".python-version": "python", ".ruby-version": "ruby",
               "rust-toolchain": "rust", "rust-toolchain.toml": "rust"}
TOOL_VERSIONS_RUNTIME = {"nodejs": "node", "node": "node", "python": "python", "ruby": "ruby", "golang": "go",
                         "go": "go", "rust": "rust", "java": "java"}
# Each runtime: commands tried in order; a later one only when the earlier one is not installed.
PROBES = {"node": [["node", "--version"]], "python": [["python", "--version"], ["python3", "--version"]],
          "ruby": [["ruby", "--version"]], "go": [["go", "version"]], "rust": [["rustc", "--version"]],
          "java": [["java", "-version"]]}
PROBE_TIMEOUT = 10
# A JVM echoes these before its version ("Picked up JAVA_TOOL_OPTIONS: ..."); they can hold secrets.
PROBE_DROP = ("JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS", "JDK_JAVA_OPTIONS")
# The version token only (20.11.0, 3.13.0rc1, 1.8.0_392), never the rest of a probe's output.
VERSION = re.compile(r"\d+(?:\.\d+)+(?:[-+_]?[0-9A-Za-z][0-9A-Za-z.]*)?")
QUOTED_VERSION = re.compile(r'version "(\d[0-9A-Za-z.+_-]*)"')  # java: version "21", "17-ea"
# Env var names a project's checks depend on. At the project root, not in .oldhand/, which git ignores.
ENV_NAMES_FILE = ".oldhand-env-names"
ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
ENV_ROUNDS = 100000
LIVE_MAX_AGE = 24 * 3600
DURATION = re.compile(r"^(\d+)([smhd]?)$")
UNIT = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}


class LedgerError(Exception):
    pass


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


# --- git and the fingerprint ---
def _git(args, cwd, env=None, data=None):
    """stdout bytes of a git command, or None when git is missing or the command fails."""
    try:
        p = subprocess.run(["git"] + args, cwd=cwd, env=env, input=data, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL)
    except OSError:
        return None
    return p.stdout if p.returncode == 0 else None


def repo_root(path):
    out = _git(["rev-parse", "--show-toplevel"], path)
    return out.decode("utf-8", "replace").strip() if out else None


def project_root(d):
    """The repo root, else the folder that holds .oldhand/, else None."""
    root = repo_root(d)
    if root:
        return root
    parent = os.path.dirname(d)
    return os.path.dirname(parent) if os.path.basename(parent) == ".oldhand" else None


def _has_dotgit(d):
    d = os.path.abspath(d)
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return True
        parent = os.path.dirname(d)
        if parent == d:
            return False
        d = parent


def tree_info(d, led=None):
    """(fingerprint, what changed_files needs to compare it later), or ("no-git", None) outside git. When git fails
    where git is or was in use, that is an error: a silent "no-git" would switch staleness off."""
    root = repo_root(d)
    if root:
        return _tree(root)
    dotgit = _has_dotgit(d)
    if dotgit or (led and any(ch["fingerprint"] != "no-git" for ch in led["checks"])):
        raise LedgerError("git did not answer in %s although %s: check that git is on PATH and that `git status` "
                          "works there (a 'dubious ownership' error needs `git config --global --add safe.directory`)"
                          % (d, "a .git folder is above it" if dotgit else "earlier checks were recorded in git"))
    return "no-git", None


def fingerprint(d, led=None):
    return tree_info(d, led)[0]


def legacy(fp):
    """True for a fingerprint written before 2.2 ("HEAD:diff:untracked"). It is compared the way it was made."""
    return fp != "no-git" and not fp.startswith("tree:")


def _text(name):
    return name.decode("utf-8", "replace")


def _tree(root, depth=0):
    """(fingerprint, info) of the working tree. The fingerprint is "tree:<id>:<extras>". The id is the git tree of
    the content on disk, what `git add -A && git write-tree` would give with .oldhand/ left out, so a commit does
    not change it and it equals a commit's tree id when nothing else differs. It is made with a copy of the index
    and a temporary object folder: nothing is written into the repository. Extras are what git add does not see the
    way a check does: untracked nested repos, a submodule's own state, untracked files over 5 MB (name and size) and
    untracked files that cannot be read. info = {head, delta: {path: "mode blob" or None} against head, extras}."""
    head = _git(["rev-parse", "--verify", "-q", "HEAD"], root)
    head = head.decode().strip() if head else "no-head"
    places = _git(["rev-parse", "--git-path", "index", "--git-path", "objects"], root)
    others = _git(["ls-files", "--others", "--exclude-standard", "-z", "--", ".", EXCLUDE], root)
    tags = _git(["ls-files", "-v", "-z"], root)
    stage = _git(["ls-files", "--stage", "-z"], root) if os.path.exists(os.path.join(root, ".gitmodules")) else b""
    if places is None or others is None or tags is None or stage is None:
        raise LedgerError("git could not describe the working tree in %s: run `git status` there to see why" % root)
    index, objects = (os.path.join(root, x) for x in os.fsdecode(places).splitlines()[:2])
    extras, skip = {}, []
    for name in sorted(n for n in others.split(b"\0") if n):
        path = os.path.join(root, os.fsdecode(name))
        if os.path.islink(path):
            continue  # git stores where the link points
        if os.path.isdir(path):
            # A nested repo: git add would store only its HEAD commit, and fails when it has none.
            token = _tree(path, depth + 1)[0] if depth < 5 and os.path.exists(os.path.join(path, ".git")) else "folder"
        else:
            try:
                size = os.path.getsize(path)
                token = "size:%d" % size if size > BIG else None if os.access(path, os.R_OK) else "unreadable"
            except OSError:
                token = "unreadable"
        if token:
            extras[_text(name)] = token
            skip.append(os.fsdecode(name).rstrip("/"))
    for sub in sorted(e.split(b"\t", 1)[1] for e in stage.split(b"\0") if e.startswith(b"160000 ") and b"\t" in e):
        path = os.path.join(root, os.fsdecode(sub))
        if depth < 5 and os.path.exists(os.path.join(path, ".git")):  # git shows only its commit or "-dirty"
            extras["submodule " + _text(sub)] = _tree(path, depth + 1)[0]
    tmp = tempfile.mkdtemp(prefix="oldhand-tree-")
    try:
        env = dict(os.environ, GIT_INDEX_FILE=os.path.join(tmp, "index"), GIT_OBJECT_DIRECTORY=os.path.join(tmp, "objects"))
        # New objects go to the temp folder and old ones are read through its alternates file (an env var would
        # split a repo path at ":"). The repo's hooks and its split-index setting are switched off for these
        # calls: a post-index-change hook must not fire, and a split index would write into .git.
        os.makedirs(os.path.join(tmp, "objects", "info"))
        real = os.fsencode(os.path.abspath(objects))
        if b"\n" in real or real[:1] in (b'"', b"#"):  # the file is one path per line; git reads a quoted one C-style
            real = b'"' + real.replace(b"\\", b"\\\\").replace(b'"', b'\\"').replace(b"\n", b"\\n") + b'"'
        with open(os.path.join(tmp, "objects", "info", "alternates"), "wb") as fh:
            fh.write(real + b"\n")
        own = ["-c", "core.splitIndex=false", "-c", "core.hooksPath=" + os.path.join(tmp, "no-hooks")]
        if os.path.exists(index):
            # The copy keeps the stat cache, so unchanged files are not re-read, and it must keep the index's own
            # time: git re-reads a file that is not older than its index, and a newer time would hide an edit made
            # in the same second as the last `git add`. The time is read first, so a race only makes it older.
            st = os.stat(index)
            shutil.copyfile(index, env["GIT_INDEX_FILE"])
            os.utime(env["GIT_INDEX_FILE"], ns=(st.st_atime_ns, st.st_mtime_ns))
        # git add trusts assume-unchanged and skip-worktree, so an edit to such a file would not count. Clear the
        # marks in the copy: one flag per call (update-index applies only one), and skip-worktree only where the
        # file exists, because a sparse checkout leaves such files out on purpose.
        marked = [(e[:1], e[2:]) for e in tags.split(b"\0") if len(e) > 2]
        for flag, names in (("--no-assume-unchanged", [n for t, n in marked if t.islower()]),
                            ("--no-skip-worktree", [n for t, n in marked if t in (b"S", b"s")
                                                    and os.path.lexists(os.path.join(root, os.fsdecode(n)))])):
            if names and _git(own + ["update-index", "-z", flag, "--stdin"], root, env, b"\0".join(names) + b"\0") is None:
                raise LedgerError("git could not read the index in %s: run `git status` there to see why" % root)
        try:  # safecrlf=true would make git add refuse a file whose line endings it would convert
            add = subprocess.run(["git", "-c", "core.safecrlf=false"] + own + ["add", "-A", "--ignore-errors", "--", ".", EXCLUDE]
                                 + [":(exclude,literal)" + n for n in skip], cwd=root, env=env,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        except OSError:
            add = None
        tree = _git(own + ["write-tree", "--missing-ok"], root, env)
        raw = _git(own + (["ls-files", "--stage", "-z"] if head == "no-head" else
                          ["diff-index", "--cached", "--raw", "--no-renames", "--no-abbrev", "-z", head]), root, env)
        if add is None or add.returncode not in (0, 1) or tree is None or raw is None:
            raise LedgerError("git could not read the working tree in %s: run `git status` there to see why" % root)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if add.returncode:  # a tracked file git could not read: it stays as committed, and that this happened still counts
        errors = b"\n".join(ln for ln in add.stderr.splitlines() if ln.startswith(b"error:"))
        extras["unreadable files"] = hashlib.sha256(errors).hexdigest()[:16]
    delta = {}
    parts = raw.split(b"\0")
    if head == "no-head":
        for meta, name in (e.split(b"\t", 1) for e in parts if b"\t" in e):
            delta[_text(name)] = "%s %s" % tuple(_text(x) for x in meta.split()[:2])
    else:
        for meta, name in zip(parts[0::2], parts[1::2]):
            f = [_text(x) for x in meta.split()]
            delta[_text(name)] = None if f[4] == "D" else "%s %s" % (f[1], f[3])
    info = {"head": head, "delta": delta if len(delta) <= TREE_DELTA_MAX else None, "extras": extras}
    mix = hashlib.sha256("".join("%s\0%s\0" % kv for kv in sorted(extras.items())).encode("utf-8", "replace"))
    return "tree:%s:%s" % (tree.decode().strip(), mix.hexdigest()[:16]), info


def changed_files(root, then, now, listings=None):
    """The paths whose content differs between two recorded trees, or None when that cannot be told: one of them
    has no stored info (recorded before 2.2), differs from its commit in too many paths, or its commit is gone."""
    if not then or not now or then.get("delta") is None or now.get("delta") is None:
        return None
    listings = {} if listings is None else listings
    same, sides = then["head"] == now["head"], [{}, {}]
    if not same:
        for i, head in enumerate((then["head"], now["head"])):
            if head not in listings:
                out = b"" if head == "no-head" else _git(["ls-tree", "-r", "-z", "--full-tree", head], root)
                listings[head] = None if out is None else {
                    _text(name): "%s %s" % tuple(_text(x) for x in meta.split()[::2])
                    for meta, name in (e.split(b"\t", 1) for e in out.split(b"\0") if b"\t" in e)}
            if listings[head] is None:
                return None
            sides[i] = listings[head]
    paths = set(then["delta"]) | set(now["delta"]) | {p for p in set(sides[0]) | set(sides[1])
                                                     if sides[0].get(p) != sides[1].get(p)}

    def at(info, side, path):
        return info["delta"][path] if path in info["delta"] else side.get(path, "as committed" if same else None)

    a, b = then.get("extras") or {}, now.get("extras") or {}
    return (sorted(p for p in paths if at(then, sides[0], p) != at(now, sides[1], p))
            + sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k)))


def _names(paths):
    more = len(paths) - NAMES_SHOWN
    return ", ".join(paths[:NAMES_SHOWN]) + (" and %d more" % more if more > 0 else "")


# Plain patch text: the user's external diff and textconv drivers would hide real changes.
DIFF = ["diff", "--binary", "--submodule=diff", "--no-ext-diff", "--no-textconv"]


def _legacy_tree_state(root, depth=0):
    """The fingerprint as 2.1 and earlier made it: the commit, a hash of the diff text and a hash of the untracked
    files. Kept only to judge checks recorded with it."""
    head = _git(["rev-parse", "--verify", "-q", "HEAD"], root)
    if head:
        head = head.decode().strip()
        diff = _git(DIFF + ["HEAD", "--", ".", EXCLUDE], root)
    else:  # a repo with no commit yet
        head = "no-head"
        staged = _git(DIFF + ["--cached", "--", ".", EXCLUDE], root)
        unstaged = _git(DIFF + ["--", ".", EXCLUDE], root)
        diff = None if staged is None or unstaged is None else staged + unstaged
    names = _git(["ls-files", "--others", "--exclude-standard", "-z", "--", ".", EXCLUDE], root)
    stage = _git(["ls-files", "--stage", "-z"], root) if os.path.exists(os.path.join(root, ".gitmodules")) else b""
    if diff is None or names is None or stage is None:
        raise LedgerError("git could not describe the working tree in %s: run `git status` there to see why" % root)
    h = hashlib.sha256()
    for name in sorted(n for n in names.split(b"\0") if n):
        h.update(name + b"\0")
        _hash_path(h, os.path.join(root, os.fsdecode(name)), depth)
    for sub in sorted(e.split(b"\t", 1)[1] for e in stage.split(b"\0") if e.startswith(b"160000 ") and b"\t" in e):
        h.update(b"submodule\0" + sub + b"\0")
        _hash_path(h, os.path.join(root, os.fsdecode(sub)), depth)
    return "%s:%s:%s" % (head, hashlib.sha256(diff).hexdigest()[:16], h.hexdigest()[:16])


def _hash_path(h, path, depth):
    if os.path.isdir(path):
        # A nested repo or a submodule: git shows only its name or "-dirty", so hash its own state.
        if depth < 5 and os.path.exists(os.path.join(path, ".git")):
            h.update(_legacy_tree_state(path, depth + 1).encode())
        return
    try:
        size = os.path.getsize(path)
        if size > BIG:
            h.update(b"size:%d" % size)
        else:
            with open(path, "rb") as fh:
                h.update(hashlib.sha256(fh.read()).digest())
    except OSError:
        h.update(b"unreadable")


def short_fp(fp):
    if ":" not in fp:
        return fp
    first, second, third = fp.split(":")  # "tree", tree id, extras; before 2.2: commit, diff hash, untracked hash
    if first == "tree":
        return second[:10] + ("" if third == NO_EXTRAS else "+" + third[:8])
    return "%s:%s:%s" % (first[:10], second[:8], third[:8])


def exclude_oldhand(d):
    """Keep .oldhand/ out of git: a `*` .gitignore inside it (needs no write to .git, which some sandboxes
    protect), plus a line in .git/info/exclude when that file is writable. Returns (exclude file written or None,
    warning or None)."""
    parent = os.path.dirname(os.path.abspath(d))
    ignore = os.path.join(parent, ".gitignore")
    if os.path.basename(parent) == ".oldhand" and not os.path.exists(ignore):
        with open(ignore, "w", encoding="utf-8") as fh:
            fh.write("# Oldhand task folders: local only\n*\n")
    out = _git(["rev-parse", "--git-path", "info/exclude"], d)
    if not out:
        return None, None
    path = os.path.normpath(os.path.join(d, out.decode("utf-8", "replace").strip()))
    try:
        text = ""
        if os.path.exists(path):
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        if any(line.strip() in (".oldhand", ".oldhand/", "/.oldhand", "/.oldhand/") for line in text.splitlines()):
            return None, None
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(("\n" if text and not text.endswith("\n") else "") + ".oldhand/\n")
    except OSError as e:
        return None, "could not add .oldhand/ to %s (%s); .oldhand/.gitignore keeps it out of git" % (path, e)
    return path, None


# --- what a check depends on outside the tree: runtime pins, listed env vars, live services ---
def pin_files(root):
    """{pin file name: content hash} for the runtime pin files at the project root, ignored by git or not."""
    out = {}
    for name in PIN_FILES:
        path = os.path.join(root, name) if root else None
        if path and os.path.isfile(path):
            try:
                with open(path, "rb") as fh:
                    out[name] = hashlib.sha256(fh.read()).hexdigest()[:16]
            except OSError:
                out[name] = "unreadable"
    return out


def pinned_runtimes(root, pins):
    """The runtimes the pin files name. .tool-versions lists `tool version` lines; tools not in
    TOOL_VERSIONS_RUNTIME are covered by the file's hash only."""
    names = {PIN_RUNTIME[p] for p in pins if p in PIN_RUNTIME}
    if ".tool-versions" in pins:
        with contextlib.suppress(OSError):
            with open(os.path.join(root, ".tool-versions"), encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    tool = line.split("#", 1)[0].split()
                    if tool and tool[0] in TOOL_VERSIONS_RUNTIME:
                        names.add(TOOL_VERSIONS_RUNTIME[tool[0]])
    return names


def probe(runtime, root):
    """The version the runtime reports from the project root, so version-manager shims honour the pin. Only the
    version token is kept: a JVM prints JAVA_TOOL_OPTIONS and friends before its version, and they can hold
    secrets, so those vars are also kept from the probe. GOTOOLCHAIN=local and RUSTUP_AUTO_INSTALL=0 stop go and
    rustup downloading a toolchain; shims that ignore them (rustup 1.27 and older, Volta, mise) may still."""
    env = {k: v for k, v in os.environ.items() if k not in PROBE_DROP}
    env.update(RUSTUP_AUTO_INSTALL="0", GOTOOLCHAIN="local")
    for cmd in PROBES.get(runtime, []):
        try:
            p = subprocess.run(cmd, cwd=root, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=env, timeout=PROBE_TIMEOUT)
        except FileNotFoundError:
            continue
        except subprocess.TimeoutExpired:
            return "unavailable (%s timed out)" % cmd[0]
        except OSError as e:
            return "unavailable (%s: %s)" % (cmd[0], e.strerror or e)
        if p.returncode != 0:
            return "unavailable (%s exited %d)" % (cmd[0], p.returncode)
        for line in (p.stdout + b"\n" + p.stderr).decode("utf-8", "replace").split("\n"):
            if "Picked up " in line:
                continue
            m = QUOTED_VERSION.search(line)
            v = m.group(1) if m else (VERSION.search(line) or [None])[0]
            if v:
                return v[:40]
        return "unavailable (no version in its output)"
    return "unavailable (%s not found)" % " or ".join(c[0] for c in PROBES.get(runtime, [])) if runtime in PROBES \
        else "unavailable (no probe for %s)" % runtime


def env_names(root):
    """The names listed in .oldhand-env-names, or None when the project has no such file. A line that is not a
    plain name is an error that cites its number only: it may hold a value."""
    path = os.path.join(root, ENV_NAMES_FILE) if root else None
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
        # Windows editors and PowerShell 5 redirection write a byte order mark (UTF-8 or UTF-16).
        lines = raw.decode("utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig",
                           "replace").splitlines()
    except OSError as e:
        raise LedgerError("could not read %s (%s): fix its permissions or remove it" % (path, e.strerror or e))
    names = []
    for n, line in enumerate(lines, 1):
        name = line.split("#", 1)[0].strip()
        if not name:
            continue
        if not ENV_NAME.match(name):
            raise LedgerError("line %d of %s is not an env var name: list names only, one per line, never values "
                              "(the line is not shown in case it holds a value)" % (n, path))
        if name not in names:
            names.append(name)
    return names


def env_digests(names, salt):
    """{name: salted digest, or "unset"}. The value goes into the hash and nowhere else."""
    out = {}
    for name in names:
        value = os.environ.get(name)
        out[name] = "unset" if value is None else hashlib.pbkdf2_hmac(
            "sha256", value.encode("utf-8", "surrogateescape"), bytes.fromhex(salt), ENV_ROUNDS).hex()[:16]
    return out


def parse_duration(s):
    """Seconds from 90m, 24h, 7d or a plain number of seconds."""
    m = DURATION.match(str(s).strip().lower())
    if not m or int(m.group(1)) == 0:
        raise LedgerError("--max-age %r is not a duration: use a whole number with s, m, h or d, for example "
                          "90m, 24h or 7d" % s)
    return int(m.group(1)) * UNIT[m.group(2)]


def human(secs):
    """A short duration: whole days (from 2d), hours or minutes when exact, else hours or minutes rounded down."""
    secs = int(secs)
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if secs >= max(size, 2 * 86400 if unit == "d" else 0) and secs % size == 0:
            return "%d%s" % (secs // size, unit)
    for unit, size in (("h", 3600), ("m", 60)):
        if secs >= size:
            return "%d%s" % (secs // size, unit)
    return "%ds" % secs


# --- the ledger file ---
def _ledger_path(d):
    return os.path.join(d, "ledger.json")


def load(d):
    p = _ledger_path(d)
    try:
        with open(p, encoding="utf-8") as fh:
            led = json.load(fh)
    except FileNotFoundError:
        raise LedgerError('no ledger.json in %s: start the task with `ledger.py init --dir %s --title "..."`' % (d, d))
    except ValueError as e:
        raise LedgerError("%s is not valid JSON (%s): fix it by hand; do not delete it, it holds the task's proof" % (p, e))
    if not isinstance(led, dict) or any(not isinstance(led.get(k), list) for k in ("criteria", "checks", "findings", "restamps")):
        raise LedgerError("%s is missing its criteria/checks/findings/restamps lists: fix it by hand" % p)
    if led.get("mode") not in MODES:
        raise LedgerError("%s has mode %r: set it to one of %s" % (p, led.get("mode"), ", ".join(MODES)))
    for n, ch in enumerate(led["checks"], 1):
        bad = _bad_field(ch)
        if bad:
            name = ch["id"] if isinstance(ch, dict) and isinstance(ch.get("id"), str) else "number %d" % n
            raise LedgerError("check %s in %s %s: fix that by hand, or record the check again and void this one" % (name, p, bad))
    if not isinstance(led.get("trees", {}), dict):
        raise LedgerError("%s has a `trees` entry that is not an object: remove it by hand" % p)
    return led


CHECK_FIELDS = {"id": str, "criterion": str, "kind": str, "status": str, "evidence": str, "by": str,
                "fingerprint": str, "time": str}
CHECK_OPTIONAL = {"cmd": str, "lead": bool, "pins": dict, "runtime": dict, "env": dict, "live": dict, "run": dict,
                  "void": dict, "evidence_hash": str}


def _bad_field(ch):
    """What is wrong with a check's shape, or None. The value itself is never quoted: only its type."""
    if not isinstance(ch, dict):
        return "is a %s, not an object" % type(ch).__name__
    for key, kind in CHECK_FIELDS.items():
        if not isinstance(ch.get(key), kind):
            return "has no `%s`" % key if key not in ch else "has a `%s` that is a %s, not a %s" % (
                key, type(ch[key]).__name__, kind.__name__)
    for key, kind in CHECK_OPTIONAL.items():
        if ch.get(key) is not None and not isinstance(ch[key], kind):
            return "has a `%s` that is a %s, not a %s" % (key, type(ch[key]).__name__, kind.__name__)
    age = (ch.get("live") or {}).get("max_age", LIVE_MAX_AGE)
    if isinstance(age, bool) or not isinstance(age, (int, float)) or age <= 0:
        return "has a live `max_age` that is not a number of seconds above 0"
    return None


def save(d, led):
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".ledger-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(led, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, _ledger_path(d))
    except BaseException:
        with contextlib.suppress(OSError):
            os.remove(tmp)
        raise


@contextlib.contextmanager
def _locked(d):
    """Hold the task folder's lock while a writer loads, changes and saves ledger.json. Not re-entrant."""
    if not os.path.isdir(d):
        raise LedgerError('no ledger.json in %s: start the task with `ledger.py init --dir %s --title "..."`' % (d, d))
    with open(os.path.join(d, "ledger.lock"), "a+") as fh:
        if fcntl:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        else:
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            if fcntl:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            else:
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)


def resolve_dir(d):
    """A relative --dir that starts with .oldhand is taken from the repo root, so a session opened in a
    sub-folder (a monorepo package) uses the same task folder as every other stage."""
    if not os.path.isabs(d) and os.path.normpath(d).split(os.sep)[0] == ".oldhand":
        cwd = os.getcwd()
        return os.path.join(repo_root(cwd) or cwd, os.path.normpath(d))
    return os.path.abspath(d)


def where(cwd=None):
    """The active task folder: the one under .oldhand/ in cwd or a folder above it (up to the repo root) whose
    ledger.json changed last."""
    d = os.path.realpath(cwd or os.getcwd())
    top = repo_root(d)
    top = os.path.realpath(top) if top else d
    found, bases = [], []
    while True:
        bases.append(os.path.join(d, ".oldhand"))
        parent = os.path.dirname(d)
        if d == top or parent == d:
            break
        d = parent
    for base in bases:
        if os.path.isdir(base):
            for name in os.listdir(base):
                p = _ledger_path(os.path.join(base, name))
                if os.path.isfile(p):
                    found.append((os.path.getmtime(p), os.path.join(base, name)))
    if not found:
        raise LedgerError('no task folder with a ledger.json under %s: start one with '
                          '`ledger.py init --dir .oldhand/<task> --title "..."` (oldhand-contract), or pass --dir'
                          % os.path.join(top, ".oldhand"))
    return max(found)[1]


def init(d, title, mode="implement"):
    """Create the task folder and its ledger. Returns (exclude file written or None, warning or None)."""
    d = os.path.abspath(d)
    if mode not in MODES:
        raise LedgerError("mode %r is not one of %s" % (mode, ", ".join(MODES)))
    if not title.strip():
        raise LedgerError("--title is empty: give the task a short title")
    os.makedirs(d, exist_ok=True)
    with _locked(d):
        if os.path.exists(_ledger_path(d)):
            raise LedgerError("%s already has a ledger: run `ledger.py sync --dir %s` to re-read contract.md, "
                              "or pick a new task folder" % (d, d))
        save(d, {"title": title.strip(), "mode": mode, "created": now(),
                 "criteria": [], "checks": [], "findings": [], "restamps": []})
    result = exclude_oldhand(d)
    if os.path.exists(os.path.join(d, "contract.md")):
        sync(d)
    return result


# --- criteria ---
def parse_contract(text):
    """(mode or None, [{id, text, proof or None}], [problems])"""
    problems, found, seen = [], [], set()
    mode = None
    m = MODE_LINE.search(text)
    if m:
        mode = m.group(1).lower()
        if mode not in MODES:
            problems.append("Mode %r is not one of %s" % (m.group(1), ", ".join(MODES)))
            mode = None
    for n, line in enumerate(text.splitlines(), 1):
        m = CRITERION.match(line)
        if not m:
            if LOOKS_LIKE_CRITERION.match(line):
                problems.append("line %d is not a criterion line: %r. Write it as `- AC1: <observable outcome> (proof: e2e)`"
                                % (n, line.strip()))
            continue
        cid, body, proof = m.groups()
        if "(proof:" in body:
            problems.append("line %d: %s has an unknown proof kind; use one of e2e, integration, unit, review, manual" % (n, cid))
        if cid in seen:
            problems.append("line %d: %s appears twice; give each criterion its own number" % (n, cid))
        seen.add(cid)
        found.append({"id": cid, "text": body.strip(), "proof": proof})
    return mode, found, problems


def default_proof(mode):
    return "e2e" if mode in ("implement", "verify") else "review"


def sync(d):
    """Re-read the criteria from contract.md. Returns the list of changes."""
    d = os.path.abspath(d)
    with _locked(d):
        led = load(d)
        cp = os.path.join(d, "contract.md")
        if not os.path.exists(cp):
            raise LedgerError("no contract.md in %s: write it first (oldhand-contract), then run sync" % d)
        with open(cp, encoding="utf-8") as fh:
            mode, found, problems = parse_contract(fh.read())
        if problems:
            raise LedgerError("contract.md has problems, nothing was changed:\n  - " + "\n  - ".join(problems))
        changes = []
        if mode and mode != led["mode"]:
            changes.append("mode %s -> %s" % (led["mode"], mode))
            led["mode"] = mode
        by_id = {c["id"]: c for c in led["criteria"]}
        for f in found:
            proof = f["proof"] or default_proof(led["mode"])
            c = by_id.get(f["id"])
            if c is None:
                led["criteria"].append({"id": f["id"], "text": f["text"], "proof": proof, "status": "live",
                                        "added": now()})
                changes.append("added " + f["id"])
                continue
            if c["status"] != "live" or c["text"] != f["text"] or c["proof"] != proof:
                changes.append(("restored " if c["status"] != "live" else "updated ") + f["id"])
                # A changed wording is a new requirement: only checks recorded from here on prove it.
                c.update(since=now(), since_check=len(led["checks"]))
            c.update(text=f["text"], proof=proof, status="live")
        ids = {f["id"] for f in found}
        for c in led["criteria"]:
            if c["status"] == "live" and c["id"] not in ids:
                c["status"] = "dropped"
                c["dropped"] = now()
                changes.append("dropped " + c["id"])
        led["criteria"].sort(key=lambda c: _order(c["id"]))
        save(d, led)
    return changes


def _order(cid):
    m = re.match(r"(AC|R)(\d+)$", cid)
    return (0 if m.group(1) == "AC" else 1, int(m.group(2))) if m else (2, 0)


def criterion(led, cid):
    """The live criterion cid, or a LedgerError that says what to do."""
    for c in led["criteria"]:
        if c["id"] == cid:
            if c["status"] != "live":
                raise LedgerError("%s was dropped from contract.md: record against a live criterion, or put it back "
                                  "in contract.md and run `ledger.py sync`" % cid)
            return c
    live = ", ".join(c["id"] for c in led["criteria"] if c["status"] == "live") or "none yet"
    raise LedgerError("no criterion %s (live: %s): add it to contract.md and run `ledger.py sync`" % (cid, live))


# --- records ---
def evidence_path(d, root, ev):
    """The path a path-like evidence string names (file or folder), False when it names one that is not there,
    None when it is not path-like: a sentence, a URL."""
    ev = (ev or "").strip()
    if not ev or re.search(r"\s", ev) or "://" in ev or not PATHISH.search(ev):
        return None
    p = re.sub(r":\d+(?::\d+)?$", "", ev)
    return next((x for x in ([p] if os.path.isabs(p) else [os.path.join(base, p) for base in (d, root) if base])
                 if os.path.exists(x)), False)


def evidence_missing(d, root, ev):
    """True when the evidence looks like a single file path and that path does not exist."""
    return evidence_path(d, root, ev) is False


def evidence_hash(path):
    """A hash of an evidence file's content: "empty", the size alone over 5 MB, None for a folder or no file."""
    try:
        if not path or not os.path.isfile(path):
            return None
        size = os.path.getsize(path)
        if size == 0:
            return "empty"
        if size > BIG:
            return "size:%d" % size
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()[:16]
    except OSError:
        return "unreadable"


def evidence_problem(d, root, ch):
    """Why a check's evidence does not hold: "missing", "empty" (it was empty when recorded), "changed" (the file
    is not what it was when recorded), or None. A check without a stored hash (recorded before 2.2, or evidence
    that is not a file) is only asked to exist."""
    path = evidence_path(d, root, ch["evidence"])
    if path is False:
        return "missing"
    was = ch.get("evidence_hash")
    if not was:
        return None
    return "empty" if was == "empty" else "changed" if evidence_hash(path) != was else None


def record(d, cid, kind, status, evidence, by, cmd=None, lead=False, live=False, max_age=None, run=None, tree=None):
    """Append a check. Returns (check, warning or None). `run` and `tree` are set by run(): what the command
    ledger.py ran itself did, and the (fingerprint, info) of the tree it started on."""
    d = os.path.abspath(d)
    if max_age is not None and not live:
        raise LedgerError("--max-age only applies to a live check: add --live, or drop --max-age")
    max_age = parse_duration(max_age) if max_age is not None else LIVE_MAX_AGE
    if kind not in KINDS:
        raise LedgerError("--kind %r is not one of %s" % (kind, ", ".join(KINDS)))
    if status not in STATUSES:
        raise LedgerError("--status %r is not one of %s" % (status, ", ".join(STATUSES)))
    if not (evidence or "").strip():
        raise LedgerError("--evidence is empty: give the file you saved (screenshot, log, result) or what you observed")
    if not (by or "").strip():
        raise LedgerError('--by is empty: say who ran it as role:model, for example "lead:fable" or "qa:worker"')
    if not (cmd or "").strip():
        raise LedgerError('--cmd is empty: name the check (the test command, "qa.py scenario S1", "rca.md"). A re-run '
                          'with the same --cmd replaces its earlier run; different checks never hide each other')
    root = project_root(d)
    pins = pin_files(root)
    runtime = {r: probe(r, root) for r in sorted(pinned_runtimes(root, pins))}
    names = env_names(root)
    with _locked(d):
        led = load(d)
        criterion(led, cid)
        fp, info = tree or tree_info(d, led)
        check = {"id": "C%d" % (len(led["checks"]) + 1), "criterion": cid, "kind": kind, "status": status,
                 "evidence": evidence.strip(), "by": by.strip(), "cmd": cmd.strip(), "lead": bool(lead),
                 "fingerprint": fp, "time": now()}
        proof = evidence_hash(evidence_path(d, root, evidence))
        if proof:
            check["evidence_hash"] = proof
        if run:
            check["run"] = run
        if info:  # what differs from the commit, so a later stale reason can name the files; unused ones dropped
            used = {ch["fingerprint"] for ch in led["checks"]}
            led["trees"] = dict({k: v for k, v in led.get("trees", {}).items() if k in used}, **{fp: info})
        # Stamped only when they apply, so a project without pins, env names or live checks records as before.
        if pins:
            check.update(pins=pins, runtime=runtime)
        if names is not None:
            led.setdefault("env_salt", secrets.token_hex(16))
            check["env"] = env_digests(names, led["env_salt"])
        if live:
            check["live"] = {"max_age": max_age}
        led["checks"].append(check)
        save(d, led)
    warnings = []
    if evidence_missing(d, root, evidence):
        warnings.append("evidence %s was not found under the task folder or the repo: this check will not count "
                        "until the file exists" % evidence.strip())
    if proof == "empty":
        warnings.append("evidence %s is an empty file: this check will not count. Save what the check showed in it "
                        "and record again" % evidence.strip())
    warnings += ["could not read the %s version (%s): recorded as unavailable, so a working %s later makes this "
                 "check stale" % (r, v[len("unavailable ("):-1], r) for r, v in runtime.items() if v.startswith("unavailable")]
    return check, "\n".join(warnings) or None


# --- run: ledger.py runs the command itself, so the status is the exit code, not what the caller typed ---
def _kill(proc):
    """End the command and everything it started in its process group (its process tree on Windows)."""
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


def _execute(line, cwd, timeout, out):
    """Run a shell line with its output going to the open file `out`. Returns (exit code, or None after the
    timeout; seconds). A file, not a pipe: a helper the command leaves running cannot keep the run waiting."""
    extra = {"start_new_session": True} if os.name == "posix" else {}
    start = time.time()
    try:
        proc = subprocess.Popen(line, shell=True, cwd=cwd, stdin=subprocess.DEVNULL, stdout=out,
                                stderr=subprocess.STDOUT, **extra)
    except OSError as e:
        raise LedgerError("the command could not start (%s), so nothing was recorded: %s" % (e.strerror or e, line))
    try:
        code = proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        code = None
    except BaseException:  # Ctrl-C, or a stop signal (see _stoppable)
        _kill(proc)
        raise
    if code is None or os.name == "posix":
        _kill(proc)  # on posix this also ends helpers the command left in its process group
    return code, time.time() - start


@contextlib.contextmanager
def _stoppable():
    """While a command runs, a stop signal (a host ending a long tool call) becomes an exception, so the command
    is ended with ledger.py instead of running on alone."""
    def stop(signum, frame):
        raise KeyboardInterrupt
    old = {}
    for name in ("SIGTERM", "SIGHUP", "SIGBREAK"):
        with contextlib.suppress(AttributeError, ValueError, OSError):  # not on this OS, or not the main thread
            old[getattr(signal, name)] = signal.signal(getattr(signal, name), stop)
    try:
        yield
    finally:
        for sig, handler in old.items():
            signal.signal(sig, handler)


def _output(out, hidden):
    """What is kept of a command's output: every value in hidden [(env var name, value bytes), longest first]
    replaced by <NAME>, and of long output only the first and last RUN_KEEP bytes. Each kept piece is read longer
    by the longest value, so a value that begins in the kept part is seen whole, and one that began before the
    last piece has its remainder dropped: no part of a value is left at a cut."""
    names = {value: b"<" + name.encode() + b">" for name, value in hidden}
    # A lookahead finds a value at every position, so values that overlap each other are all seen.
    values = re.compile(b"(?=(" + b"|".join(re.escape(v) for _, v in hidden) + b"))") if hidden else None

    def clean(data, start, end):
        spans = []  # [start, end, placeholder] of each stretch that values cover, overlapping ones merged
        for m in values.finditer(data) if values else ():
            if spans and m.start(1) < spans[-1][1]:
                spans[-1][1] = max(spans[-1][1], m.end(1))
            else:
                spans.append([m.start(1), m.end(1), names[m.group(1)]])
        parts, at = [], start
        for first, last, name in spans:
            if first >= end:
                break
            if last <= start:
                continue
            if first < start:
                at = max(at, min(last, end))  # began before the kept part: what is left of it goes too
            else:
                parts += [data[at:first], name]
                at = last
        return b"".join(parts + [data[at:end]] if at < end else parts)

    edge = max([len(v) for _, v in hidden] + [0])
    size = out.seek(0, os.SEEK_END)
    out.seek(0)
    if size <= 2 * RUN_KEEP + edge:
        data = out.read()
        return clean(data, 0, len(data))
    head = out.read(RUN_KEEP + edge)
    out.seek(size - RUN_KEEP - edge)
    tail = out.read()
    return (clean(head, 0, RUN_KEEP) + b"\n[... %d bytes left out ...]\n" % (size - 2 * RUN_KEEP)
            + clean(tail, edge, len(tail)))


def _key_folders():
    """Where the rerun key may live, outside every project: the user's state folder, then a private folder in the
    temp folder for hosts where the first cannot be written (a sandbox)."""
    home = os.path.expanduser("~")
    state = os.environ.get("XDG_STATE_HOME") or os.environ.get("LOCALAPPDATA") or os.path.join(home, ".local", "state")
    user = os.getuid() if hasattr(os, "getuid") else os.environ.get("USERNAME", "user")
    # A relative path would put the key inside whatever project the command runs in.
    return [os.path.join(x, "oldhand") for x in (state,) if os.path.isabs(x)] + [
        os.path.join(tempfile.gettempdir(), "oldhand-%s" % user)]


def _rerun_key(create=False):
    """The secret that signs every command `run` records, or None when there is none. `rerun` executes a stored
    command only when its signature fits this key, so a ledger.json that came with a repository or an archive, or
    was edited by hand, cannot make rerun execute anything: its commands were not recorded by this user here."""
    for folder in _key_folders():  # the state folder when a key is or can be put there, else the temp folder
        path = os.path.join(folder, "rerun-key")
        try:
            if create and not os.path.lexists(path):
                os.makedirs(folder, mode=0o700, exist_ok=True)
                fd, new = tempfile.mkstemp(dir=folder, prefix=".key-")  # mode 0600
                try:
                    with os.fdopen(fd, "wb") as fh:
                        fh.write(secrets.token_bytes(32))
                    with contextlib.suppress(FileExistsError):
                        os.link(new, path)  # whole or not at all, and never over a key another run just made
                finally:
                    os.remove(new)
            # Ours, the folder not writable and the key not readable by anyone else, and no link to elsewhere.
            for target, others in ((folder, 0o022), (path, 0o077)):
                st = os.lstat(target)
                if os.name == "posix" and (st.st_uid != os.getuid() or st.st_mode & others or stat.S_ISLNK(st.st_mode)):
                    raise OSError("not a private file of this user")
            with open(path, "rb") as fh:
                key = fh.read()
            if len(key) >= 32:
                return key
        except OSError:
            continue
    return None


NO_COMMAND = "no command: it was not recorded by `ledger.py run`"
NOT_OURS = "its command was not recorded by this user in this project on this machine"


def _signature(key, check, root):
    """The signature of what rerun would execute and record: the command, its criterion, its kind and the project
    folder, so a signed check copied into another project's ledger does not run there."""
    text = "\0".join((check.get("cmd") or "", check["criterion"], check["kind"], os.path.realpath(root)))
    return hmac.new(key, text.encode("utf-8", "surrogateescape"), "sha256").hexdigest()


def _runnable(key, check, root):
    """Why rerun will not execute a check's command, or None when it will."""
    if not check.get("run"):
        return NO_COMMAND
    signed = str(check["run"].get("signed")).encode("utf-8", "replace")  # bytes: any text a ledger holds can be compared
    if not key or not hmac.compare_digest(signed, _signature(key, check, root).encode()):
        return NOT_OURS
    return None


def _run(d, cid, kind, by, line, lead, live, max_age, timeout):
    """Run a shell line from the project root, save its output under <task>/runs/ and record the result on the
    tree the command started on. Returns (check, warning or None, the output's last lines)."""
    root, line = project_root(d) or os.getcwd(), line.strip()
    # Values of the vars in .oldhand-env-names are kept out of what is saved; the longest first, so a value that
    # contains another is replaced whole. A broken names file stops the run before the command starts.
    hidden = sorted(((n, os.environ[n].encode("utf-8", "surrogateescape")) for n in env_names(root) or []
                     if len(os.environ.get(n, "")) >= REDACT_MIN), key=lambda nv: -len(nv[1]))
    for name, value in hidden:
        if value in line.encode("utf-8", "surrogateescape"):
            raise LedgerError("the command line holds the value of %s, and the command line is stored in "
                              "ledger.json: nothing was run or recorded. Give the variable's name instead and let "
                              "the command's own shell fill it in, for example '... $%s ...' inside single quotes"
                              % (name, name))
    before = tree_info(d, load(d))
    with tempfile.TemporaryFile() as raw, _stoppable():  # no name on disk: a kill leaves no raw output behind
        code, secs = _execute(line, root, timeout, raw)
        if code in NOT_STARTED:
            raise LedgerError("the command could not start (exit %d: %s), so nothing was recorded: %s"
                              % (code, NOT_STARTED[code], line))
        body = _output(raw, hidden)
    how = ("timed out after %gs" % timeout if code is None else "exit %d" % code if code
           else "exit 0, but the output says no tests ran" if NO_TESTS.search(body) else "exit 0")
    status = "pass" if how == "exit 0" else "fail"
    runs = os.path.join(d, "runs")
    os.makedirs(runs, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
    for n in range(1, 1000):  # a name no other run has: two runs of one criterion can finish in the same second
        name = "%s-%s-%s%s.txt" % (stamp, cid, kind, "" if n == 1 else "-%d" % n)
        try:
            with open(os.path.join(runs, name), "xb") as fh:
                fh.write(("$ %s\n%s: %s, %.1fs\n\n" % (line, how, status, secs)).encode("utf-8", "replace") + body)
            break
        except FileExistsError:
            continue
    else:
        raise LedgerError("could not name the output file in %s: remove old files there" % runs)
    done = {"exit": code, "result": how, "seconds": round(secs, 1), "timeout": timeout}
    key = _rerun_key(create=True)
    if key:
        done["signed"] = _signature(key, {"cmd": line, "criterion": cid, "kind": kind}, root)
    check, warning = record(d, cid, kind, status, "runs/" + name, by, cmd=line, lead=lead, live=live,
                            max_age=max_age, run=done, tree=before)
    if not key:
        warning = "\n".join(x for x in (warning, "no folder for the rerun key could be written, so `rerun` will not "
                                                 "run this check again") if x)
    after = tree_info(d)
    if after[0] != before[0]:  # the check proves the tree it started on, which is no longer the tree
        changed = changed_files(root, before[1], after[1])
        warning = "\n".join(x for x in (warning, (
            "files changed while the command ran%s, so this check is already stale. If the command writes them "
            "itself, add them to .gitignore or .git/info/exclude; otherwise run it again"
            % (": " + _names(changed) if changed else ""))) if x)
    return check, warning, body.decode("utf-8", "replace").splitlines()[-15:]


def _shell_join(argv):
    return subprocess.list2cmdline(argv) if os.name == "nt" else " ".join(shlex.quote(a) for a in argv)


def run(d, cid, kind, by, argv, lead=False, live=False, max_age=None, timeout=RUN_TIMEOUT):
    """Run a command and record the result as a check: pass when it exits 0, fail otherwise. One argument is taken
    as a whole shell line; several are quoted and joined. A run started in a sub-folder is stored as
    `cd <sub-folder> && <command>` from the project root, so `rerun` can repeat it from anywhere."""
    d = os.path.abspath(d)
    argv = list(argv)[1:] if list(argv)[:1] == ["--"] else list(argv)
    if kind not in RUN_KINDS:
        raise LedgerError("--kind %r is not a kind `run` records (%s): record a review or manual check with "
                          "`ledger.py record`, a mutation check with mutate.py" % (kind, ", ".join(RUN_KINDS)))
    if not "".join(argv).strip():
        raise LedgerError("no command to run: put it after `--`, for example "
                          "`ledger.py run --id AC1 --kind unit --by lead:fable -- python3 -m pytest tests -q`")
    if not (by or "").strip():
        raise LedgerError('--by is empty: say who ran it as role:model, for example "lead:fable" or "qa:worker"')
    if max_age is not None and not live:
        raise LedgerError("--max-age only applies to a live check: add --live, or drop --max-age")
    if max_age is not None:
        parse_duration(max_age)  # a bad value stops here, before the command runs
    if not timeout or timeout <= 0:
        raise LedgerError("--timeout must be a number of seconds above 0")
    criterion(load(d), cid)
    line = argv[0] if len(argv) == 1 else _shell_join(argv)
    root, cwd = project_root(d), os.path.realpath(os.getcwd())
    if root and cwd != os.path.realpath(root):
        rel = os.path.relpath(cwd, os.path.realpath(root))
        # "./" keeps a folder named like an option from being read as one; cmd.exe needs the double quotes.
        there = cwd if rel.startswith("..") else os.path.join(".", rel)
        line = "cd %s && %s" % ('"%s"' % there if os.name == "nt" else shlex.quote(there), line)
    return _run(d, cid, kind, by, line, lead, live, max_age, timeout)


def rerun(d, stale=False, check=None, by=None):
    """Run again what `run` recorded: every counted stale check (stale=True) or the one named. Only a command
    signed with this user's rerun key is executed. Returns ([(old check, new check, warning, last output lines)],
    [(stale check that was not run, why)])."""
    d = os.path.abspath(d)
    led, key, root = load(d), _rerun_key(), project_root(d) or os.getcwd()
    if check:
        todo = [_check(led, check)]
        why = _runnable(key, todo[0], root)
        if why:
            raise LedgerError("%s cannot be run again (%s). Repeat the check the way it was made and record it; "
                              "run a command from a ledger you did not write only when the user asks for it"
                              % (check, why))
    elif stale:
        ids = set(evaluate(d)["stale"])
        todo = [ch for ch in led["checks"] if ch["id"] in ids]
    else:
        raise LedgerError("say what to run again: --stale for every stale check, or --check C<n> for one")
    done = []
    for ch in (c for c in todo if not _runnable(key, c, root)):
        age = ch["live"].get("max_age", LIVE_MAX_AGE) if ch.get("live") else None
        new, warning, tail = _run(d, ch["criterion"], ch["kind"], by or ch["by"], ch["cmd"], ch.get("lead", False),
                                  bool(ch.get("live")), None if age is None else "%d" % age,
                                  ch["run"].get("timeout") or RUN_TIMEOUT)
        done.append((ch, new, warning, tail))
    return done, [(c, _runnable(key, c, root)) for c in todo if _runnable(key, c, root)]


def finding_add(d, sev, lens, where_, text):
    d = os.path.abspath(d)
    if sev not in SEVS:
        raise LedgerError("--sev %r is not one of %s" % (sev, ", ".join(SEVS)))
    for name, v in (("--lens", lens), ("--where", where_), ("--text", text)):
        if not (v or "").strip():
            raise LedgerError("%s is empty: a finding needs its lens, its file:line and the concrete defect" % name)
    with _locked(d):
        led = load(d)
        f = {"id": "F%d" % (len(led["findings"]) + 1), "sev": sev, "lens": lens.strip(), "where": where_.strip(),
             "text": text.strip(), "status": "open", "note": "", "accepted_by": "", "time": now()}
        led["findings"].append(f)
        save(d, led)
    return f


def finding_resolve(d, fid, how, note, accepted_by=None):
    d = os.path.abspath(d)
    if how not in HOWS:
        raise LedgerError("--how %r is not one of %s" % (how, ", ".join(HOWS)))
    if not (note or "").strip():
        raise LedgerError("--note is empty: say what fixed it, what refutes it, or why it can wait")
    if accepted_by not in (None, "", "user"):
        raise LedgerError("--accepted-by only takes 'user': only the user can accept a deferred high or medium finding")
    if accepted_by and how != "deferred":
        raise LedgerError("--accepted-by only applies to --how deferred")
    with _locked(d):
        led = load(d)
        for f in led["findings"]:
            if f["id"] == fid:
                f.update(status=how, note=note.strip(), accepted_by=accepted_by or "", resolved=now())
                save(d, led)
                return f
    known = ", ".join(f["id"] for f in led["findings"]) or "none yet"
    raise LedgerError("no finding %s (known: %s): see `ledger.py status`" % (fid, known))


def _check(led, cid):
    check = next((c for c in led["checks"] if c["id"] == cid), None)
    if check is None:
        raise LedgerError("no check %s: see `ledger.py status` for the check ids" % cid)
    return check


def restamp(d, cid, reason):
    """Mark check cid as still valid on the current tree. Returns the restamp, or None if it was current."""
    d = os.path.abspath(d)
    if not (reason or "").strip():
        raise LedgerError("--reason is empty: say why the change since the check cannot affect it")
    with _locked(d):
        led = load(d)
        check = _check(led, cid)
        fp = fingerprint(d, led)
        if fp == "no-git":
            raise LedgerError("no git here, so checks never go stale and there is nothing to restamp")
        was = check["fingerprint"]
        if was == fp or (legacy(was) and was == _legacy_tree_state(repo_root(d))) \
                or any(r["check"] == cid and r["fingerprint"] == fp for r in led["restamps"]):
            return None
        r = {"check": cid, "reason": reason.strip(), "from": check["fingerprint"], "fingerprint": fp, "time": now()}
        led["restamps"].append(r)
        save(d, led)
    return r


def void(d, cid, reason):
    """Retire a check that no longer applies (a wrong scenario that was removed). It is listed, never counted."""
    d = os.path.abspath(d)
    if not (reason or "").strip():
        raise LedgerError("--reason is empty: say why the check no longer applies, for example "
                          "\"scenario S4 was wrong and is removed from scenarios.json\"")
    with _locked(d):
        led = load(d)
        check = _check(led, cid)
        check["void"] = {"reason": reason.strip(), "time": now()}
        save(d, led)
    return check


# --- the verdict ---
def satisfying(proof):
    if proof in RANK:
        return {k for k, r in RANK.items() if r >= RANK[proof]}
    return {proof}


def evaluate(d):
    d = os.path.abspath(d)
    led = load(d)
    root = project_root(d)
    fp, info = tree_info(d, led)
    git = fp != "no-git"
    restamped = {(r["check"], r["fingerprint"]) for r in led["restamps"]}
    trees = led.get("trees", {})
    old, listings, problems = [], {}, {}
    order = {ch["id"]: i for i, ch in enumerate(led["checks"])}
    live = [c for c in led["criteria"] if c["status"] == "live"]
    since = {c["id"]: c.get("since_check", 0) for c in live}
    pins = pin_files(root)
    names = env_names(root)
    salt = led.get("env_salt")
    # Without a salt no check stored env digests, so only the names are compared.
    env_now = {} if names is None else env_digests(names, salt) if salt else dict.fromkeys(names)
    versions = {}  # runtime -> version now, probed once per verdict and only for runtimes a check recorded
    clock = datetime.datetime.now(datetime.timezone.utc)
    beyond = {}

    def version_now(rt):
        if rt not in versions:
            versions[rt] = probe(rt, root)
        return versions[rt]

    def fp_like(ch):
        """The tree now, in the form the check's fingerprint has: a check from 2.1 or earlier is judged its way."""
        if not legacy(ch["fingerprint"]):
            return fp
        if not old:
            old.append(_legacy_tree_state(repo_root(d)))
        return old[0]

    def files_fresh(ch):
        return not git or ch["fingerprint"] in (fp, fp_like(ch)) or bool({(ch["id"], fp), (ch["id"], fp_like(ch))} & restamped)

    def other_stale(ch):
        """Why the check is stale beyond the files: runtime, env vars, live expiry. Restamp clears none of these."""
        if ch["id"] in beyond:
            return beyond[ch["id"]]
        why = []
        was = ch.get("pins") or {}
        for p in sorted(set(was) | set(pins)):
            if was.get(p) != pins.get(p):
                why.append("runtime pin file %s %s" % (p, "added" if p not in was else "removed" if p not in pins
                                                       else "changed"))
        for rt, then in sorted((ch.get("runtime") or {}).items()):
            if version_now(rt) != then:
                why.append("runtime %s changed: %s -> %s" % (rt, then, version_now(rt)))
        was = ch.get("env") or {}
        for n in sorted(set(was) | set(env_now)):
            if n not in env_now:
                why.append("env var %s removed from %s" % (n, ENV_NAMES_FILE))
            elif n not in was:
                why.append("env var %s added to %s" % (n, ENV_NAMES_FILE))
            elif was[n] != env_now[n]:
                why.append("env var %s %s" % (n, "was set" if was[n] == "unset" else "was unset"
                                              if env_now[n] == "unset" else "changed"))
        if ch.get("live"):
            max_age = ch["live"].get("max_age", LIVE_MAX_AGE)
            try:
                age = (clock - datetime.datetime.fromisoformat(ch["time"])).total_seconds()
            except (TypeError, ValueError):
                age = None
            if age is None:
                why.append("live check has an unreadable time (%s)" % ch["time"])
            elif age < -60:
                why.append("live check is dated in the future (%s)" % ch["time"])
            elif age > max_age:
                why.append("live check expired (recorded %s ago, max %s)" % (human(age), human(max_age)))
        beyond[ch["id"]] = why
        return why

    def fresh(ch):
        return files_fresh(ch) and not other_stale(ch)

    def problem(ch):
        if ch["id"] not in problems:
            problems[ch["id"]] = evidence_problem(d, root, ch)
        return problems[ch["id"]]

    def current(ch):
        """Not voided, and recorded against the criterion's present wording."""
        return not ch.get("void") and order[ch["id"]] >= since.get(ch["criterion"], 0)

    incomplete, notyet, blocked, notes, stale = [], [], [], [], []
    if not os.path.exists(os.path.join(d, "contract.md")):
        incomplete.append("no contract.md in the task folder: write it (oldhand-contract), then run `ledger.py sync`")
    elif not live:
        incomplete.append("contract.md has no live criteria: add `- AC1: ...` lines, then run `ledger.py sync`")
    rows = []
    for c in live:
        kinds = satisfying(c["proof"])
        mine = [ch for ch in led["checks"] if ch["criterion"] == c["id"] and ch["kind"] in kinds]
        older = [ch["id"] for ch in mine if not ch.get("void") and not current(ch)]
        if older:
            notes.append("%s: %s were recorded against an older wording of %s and do not count"
                         % (c["id"], ", ".join(older), c["id"]))
        # Checks with the same --cmd are runs of one check: only the latest run counts, a baseline-fail run
        # included. Every check counts, so a later pass of one scenario never hides an earlier fail of another.
        latest = {}
        for ch in mine:
            if current(ch):
                latest.pop(ch.get("cmd") or "", None)
                latest[ch.get("cmd") or ""] = ch
        counted = [ch for ch in latest.values() if ch["status"] != "baseline-fail"]
        row = {"id": c["id"], "text": c["text"], "proof": c["proof"], "check": None, "counted": [],
               "status": "none", "by": "", "evidence": "", "flags": []}
        rows.append(row)
        if not counted:
            what = " or ".join(k for k in ("e2e", "integration", "unit", "review", "manual") if k in kinds)
            incomplete.append("%s has no %s check yet: run it and `ledger.py record` it" % (c["id"], what))
            continue
        row["counted"] = [ch["id"] for ch in counted]
        for ch in counted:
            if not fresh(ch):
                stale.append(ch["id"])
                if "stale" not in row["flags"]:
                    row["flags"].append("stale")
            if problem(ch):
                if "evidence " + problem(ch) not in row["flags"]:
                    row["flags"].append("evidence " + problem(ch))
                incomplete.append("%s: the evidence of %s (%s) %s, so it does not count: %s" % (
                    c["id"], ch["id"], ch["evidence"],
                    {"missing": "is not there", "empty": "was an empty file when the check was recorded",
                     "changed": "changed after the check was recorded"}[problem(ch)],
                    "save the evidence at that path or record the check again" if problem(ch) == "missing"
                    else "run the check again and record it"))
                continue
            if ch["status"] == "fail":
                notyet.append("%s fails (%s %s by %s): fix it and record a new run" % (c["id"], ch["id"], ch["kind"], ch["by"]))
            if not files_fresh(ch):
                changed = changed_files(root, trees.get(ch["fingerprint"]), info, listings)
                notyet.append("%s: %s was recorded on an older tree (%s, now %s%s): re-run it and record again, or "
                              "`ledger.py restamp --check %s --reason ...` if the change cannot affect it"
                              % (c["id"], ch["id"], short_fp(ch["fingerprint"]), short_fp(fp_like(ch)),
                                 "; changed: " + _names(changed) if changed else "", ch["id"]))
            if other_stale(ch):
                notyet.append("%s: %s is stale: %s: re-run it and record again (restamp clears file changes only)"
                              % (c["id"], ch["id"], "; ".join(other_stale(ch))))
            if fresh(ch) and ch["status"] == "blocked":
                blocked.append("%s is blocked (%s): %s" % (c["id"], ch["id"], ch["evidence"]))
        statuses = [ch["status"] for ch in counted]
        row["status"] = next(s for s in ("fail", "blocked", "pass") if s in statuses)
        rep = [ch for ch in counted if ch["status"] == row["status"]][-1]
        row.update(check=rep["id"], by=rep["by"], evidence=rep["evidence"])

    open_findings = []
    for f in led["findings"]:
        serious = f["sev"] in ("high", "medium")
        if f["status"] == "open":
            open_findings.append(f)
            if serious:
                notyet.append("%s (%s, %s) is open at %s: fix it, refute it, or defer it with the user's acceptance"
                              % (f["id"], f["sev"], f["lens"], f["where"]))
            else:
                notes.append("%s (low) is a known follow-up: %s" % (f["id"], f["text"]))
        elif f["status"] == "deferred" and serious and f.get("accepted_by") != "user":
            notyet.append("%s (%s) is deferred without the user's acceptance: ask the user, then "
                          "`ledger.py finding resolve --id %s --how deferred --note ... --accepted-by user`"
                          % (f["id"], f["sev"], f["id"]))

    if led["mode"] in ("implement", "verify") and not any(
            ch["kind"] == "e2e" and ch["status"] == "pass" and ch.get("lead") and ch["criterion"] in since
            and current(ch) and fresh(ch) and not problem(ch) for ch in led["checks"]):
        notyet.append("no e2e pass recorded with --lead on the current tree: the lead re-runs the most important "
                      "acceptance scenario itself and records it with --lead")

    for ch in led["checks"]:
        if ch.get("void"):
            notes.append("%s (%s %s) was voided and does not count: %s"
                         % (ch["id"], ch["criterion"], ch["kind"], ch["void"]["reason"]))
        elif ch["status"] == "baseline-fail":
            notes.append("%s (%s %s) failed on the untouched tree before the change: pre-existing, never counts as a pass"
                         % (ch["id"], ch["criterion"], ch["kind"]))
        elif ch["kind"] == "mutation":
            word = {"pass": "KILLED", "fail": "SURVIVED", "blocked": "ERROR"}.get(ch["status"], ch["status"])
            notes.append("%s mutation check on %s: %s" % (ch["id"], ch["criterion"], word))
    if not git:
        notes.append("no git here: %s is not tracked, so a check may describe an older version of the files"
                     % ("staleness" if not (pins or names is not None or any(ch.get("live") for ch in led["checks"]))
                        else "file staleness"))

    if incomplete:
        verdict, reasons = "INCOMPLETE", incomplete + notyet + blocked
    elif notyet:
        verdict, reasons = "NOT YET", notyet + blocked
    elif blocked:
        verdict, reasons = "BLOCKED", blocked
    else:
        verdict = "VERIFIED"
        reasons = ["every live criterion has a passing check of its proof kind on the current tree"
                   + (" and the lead recorded an e2e pass" if led["mode"] in ("implement", "verify") else "")
                   + "; no open high or medium findings"]
    head = info["head"] if info and info["head"] != "no-head" else None
    return {"verdict": verdict, "exit": VERDICT_EXIT[verdict], "title": led["title"], "mode": led["mode"],
            "dir": d, "fingerprint": fp, "head": head,
            # True when the fingerprinted files are exactly the tree of the HEAD commit.
            "committed": bool(head and info["delta"] == {} and not info["extras"]),
            "criteria": rows, "open_findings": open_findings, "reasons": reasons, "notes": notes,
            "stale": sorted(stale, key=order.get)}


# --- output ---
def _table(headers, rows):
    rows = [[str(x) for x in r] for r in rows]
    w = [max([len(h)] + [len(r[i]) for r in rows]) for i, h in enumerate(headers)]
    return "\n".join("  ".join(c.ljust(w[i]) for i, c in enumerate(r)).rstrip() for r in [headers] + rows)


def _cut(s, n=60):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[:n - 3] + "..."


def verdict_text(res):
    out = ["VERDICT: %s" % res["verdict"], "Task: %s (mode %s)  %s" % (res["title"], res["mode"], res["dir"]),
           "Tree: %s" % ("no git, staleness not tracked" if res["fingerprint"] == "no-git" else tree_text(res)), ""]
    if res["criteria"]:
        out.append(_table(["criterion", "proof", "counted", "status", "by", "flags"],
                          [[r["id"], r["proof"], ",".join(r["counted"]) or "-", r["status"], r["by"] or "-",
                            ", ".join(r["flags"])]
                           for r in res["criteria"]]))
    else:
        out.append("No live criteria.")
    if res["open_findings"]:
        out += ["", "Open findings:"]
        out += ["  %s  %s  %s  %s  %s" % (f["id"], f["sev"], f["lens"], f["where"], _cut(f["text"], 80))
                for f in res["open_findings"]]
    out += ["", "Reasons:"] + ["  - " + r for r in res["reasons"]]
    if res["notes"]:
        out += ["", "Notes:"] + ["  - " + n for n in res["notes"]]
    return "\n".join(out)


def tree_text(res):
    """The tree id and how it relates to the commit, so a commit can be shown to hold the verified files."""
    return short_fp(res["fingerprint"]) + (
        ", no commit yet" if not res["head"] else ", the files of commit %s" % res["head"][:10] if res["committed"]
        else ", commit %s plus uncommitted changes" % res["head"][:10])


def status_text(d):
    d = os.path.abspath(d)
    led = load(d)
    out = ["Task: %s (mode %s)  %s" % (led["title"], led["mode"], d), "", "Criteria:"]
    out.append(_table(["id", "status", "proof", "text"], [[c["id"], c["status"], c["proof"], _cut(c["text"])]
                                                         for c in led["criteria"]]) if led["criteria"] else "  none yet")
    out += ["", "Checks:"]
    out.append(_table(["id", "criterion", "kind", "status", "lead", "by", "tree", "evidence"],
                      [[c["id"], c["criterion"], c["kind"], c["status"] + (" (void)" if c.get("void") else "")
                        + (" (live %s)" % human(c["live"].get("max_age", LIVE_MAX_AGE)) if c.get("live") else ""),
                        "yes" if c["lead"] else "", c["by"],
                        short_fp(c["fingerprint"]), _cut(c["evidence"], 50)] for c in led["checks"]])
               if led["checks"] else "  none yet")
    out += ["", "Findings:"]
    out.append(_table(["id", "sev", "lens", "status", "where", "text"],
                      [[f["id"], f["sev"], f["lens"], f["status"] + (" (accepted by user)" if f.get("accepted_by") else ""),
                        f["where"], _cut(f["text"], 50)] for f in led["findings"]]) if led["findings"] else "  none")
    if led["restamps"]:
        out += ["", "Restamps:"] + ["  %s at %s: %s" % (r["check"], r["time"], r["reason"]) for r in led["restamps"]]
    return "\n".join(out)


def _cell(s):
    return str(s).replace("|", "/").replace("\n", " ")


def report_md(d):
    res = evaluate(d)
    led = load(os.path.abspath(d))
    out = ["### Verdict: %s" % res["verdict"], "",
           "| criterion | outcome | proof | counted checks | status | by | evidence | flags |",
           "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in res["criteria"]:
        out.append("| %s |" % " | ".join(_cell(x) for x in (r["id"], r["text"], r["proof"], ", ".join(r["counted"]) or "-", r["status"],
                                                           r["by"] or "-", r["evidence"] or "-", ", ".join(r["flags"]))))
    out += ["", "**Why:**"] + ["- " + _cell(r) for r in res["reasons"]]
    if led["findings"]:
        out += ["", "**Review findings**", "", "| id | sev | lens | where | status | finding | note |",
                "| --- | --- | --- | --- | --- | --- | --- |"]
        for f in led["findings"]:
            st = f["status"] + (" (accepted by user)" if f.get("accepted_by") else "")
            out.append("| %s |" % " | ".join(_cell(x) for x in (f["id"], f["sev"], f["lens"], f["where"], st, f["text"], f["note"])))
    if res["notes"]:
        out += ["", "**Notes**"] + ["- " + _cell(n) for n in res["notes"]]
    tree = "no git" if res["fingerprint"] == "no-git" else tree_text(res)
    out += ["", "Computed by ledger.py from ledger.json at %s on tree %s. Not written by hand." % (now(), tree)]
    return "\n".join(out) + "\n"


def _warn(warning):
    for line in (warning or "").splitlines():
        print("warning: " + line, file=sys.stderr)


def _ran(check, tail):
    """One line for a check `run` made, with the end of the output when it failed."""
    out = "%s recorded: %s %s %s (%s, %.1fs), evidence %s (tree %s)" % (
        check["id"], check["criterion"], check["kind"], check["status"], check["run"]["result"],
        check["run"]["seconds"], check["evidence"], short_fp(check["fingerprint"]))
    return out if check["status"] == "pass" else "\n".join([out] + ["  | " + line for line in tail])


# --- command line ---
class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write("%s: error: %s (run with -h for help)\n" % (self.prog, message))
        sys.exit(ERROR_EXIT)


def main(argv=None):
    ap = _Parser(prog="ledger.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    dir_opt = _Parser(add_help=False)
    dir_opt.add_argument("--dir", help="task folder (default: the active task, see `where`)")

    p = sub.add_parser("init", help="create the task folder and its ledger")
    p.add_argument("--dir", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--mode", default="implement", choices=MODES)
    sub.add_parser("sync", parents=[dir_opt], help="re-read the criteria from contract.md")
    p = sub.add_parser("record", parents=[dir_opt], help="record a check against a criterion")
    p.add_argument("--id", required=True)
    p.add_argument("--kind", required=True, choices=KINDS)
    p.add_argument("--status", required=True, choices=STATUSES)
    p.add_argument("--evidence", required=True)
    p.add_argument("--by", required=True)
    p.add_argument("--cmd", required=True, help="names the check; a re-run with the same --cmd replaces its last run")
    p.add_argument("--lead", action="store_true")
    p.add_argument("--live", action="store_true",
                   help="the check hit a real external service; it goes stale after --max-age")
    p.add_argument("--max-age", help="with --live: how long it stays fresh, for example 90m, 24h, 7d (default 24h)")
    p = sub.add_parser("run", parents=[dir_opt], help="run a command and record its result: exit 0 is pass")
    p.add_argument("--id", required=True)
    p.add_argument("--kind", required=True, choices=RUN_KINDS)
    p.add_argument("--by", required=True)
    p.add_argument("--lead", action="store_true")
    p.add_argument("--live", action="store_true", help="the command hits a real external service")
    p.add_argument("--max-age", help="with --live: how long the check stays fresh (default 24h)")
    p.add_argument("--timeout", type=float, default=RUN_TIMEOUT, help="seconds before the command is stopped and "
                   "recorded as a fail (default %d)" % RUN_TIMEOUT)
    p.add_argument("argv", nargs=argparse.REMAINDER, metavar="-- command",
                   help="after every option: `--`, then the command (one quoted shell line, or the words)")
    p = sub.add_parser("rerun", parents=[dir_opt], help="run again the checks `run` recorded, and record the results")
    which = p.add_mutually_exclusive_group(required=True)
    which.add_argument("--stale", action="store_true", help="every stale check that has a command")
    which.add_argument("--check", help="one check, like C7")
    p.add_argument("--by", help="who runs it now (default: who ran it before)")
    fp_ = sub.add_parser("finding", help="add or resolve a review finding")
    fsub = fp_.add_subparsers(dest="fcmd", required=True)
    p = fsub.add_parser("add", parents=[dir_opt])
    p.add_argument("--sev", required=True, choices=SEVS)
    p.add_argument("--lens", required=True)
    p.add_argument("--where", required=True)
    p.add_argument("--text", required=True)
    p = fsub.add_parser("resolve", parents=[dir_opt])
    p.add_argument("--id", required=True)
    p.add_argument("--how", required=True, choices=HOWS)
    p.add_argument("--note", required=True)
    p.add_argument("--accepted-by", choices=["user"])
    p = sub.add_parser("restamp", parents=[dir_opt], help="keep a check valid across a change that cannot affect it")
    p.add_argument("--check", required=True)
    p.add_argument("--reason", required=True)
    p = sub.add_parser("void", parents=[dir_opt], help="retire a check that no longer applies; listed, never counted")
    p.add_argument("--check", required=True)
    p.add_argument("--reason", required=True)
    p = sub.add_parser("verdict", parents=[dir_opt], help="compute the verdict")
    p.add_argument("--json", action="store_true")
    sub.add_parser("status", parents=[dir_opt], help="print everything in the ledger")
    sub.add_parser("report", parents=[dir_opt], help="markdown block for report.md")
    p = sub.add_parser("where", parents=[dir_opt], help="print the active task folder, or check the one --dir names")
    p.add_argument("--root", help="search from this folder instead of the current one")
    a = ap.parse_args(argv)
    for s in (sys.stdout, sys.stderr):  # a Windows pipe defaults to the ANSI code page; criteria can hold any text
        with contextlib.suppress(AttributeError, ValueError):
            s.reconfigure(encoding="utf-8", errors="replace")
    try:
        if a.dir:
            d = resolve_dir(a.dir)
        elif a.command not in ("init", "where"):
            d = where()
        if a.command == "init":
            excluded, warning = init(d, a.title, a.mode)
            print("ledger created in %s (mode %s)." % (d, a.mode))
            if excluded:
                print("added .oldhand/ to %s (local only)." % excluded)
            if warning:
                print("warning: " + warning, file=sys.stderr)
            print("Next: write contract.md there, then `ledger.py sync --dir %s`." % d)
        elif a.command == "sync":
            changes = sync(d)
            led = load(d)
            live = [c["id"] for c in led["criteria"] if c["status"] == "live"]
            print("%s. %d live criteria: %s (mode %s)." % ("; ".join(changes) if changes else "no changes",
                                                           len(live), ", ".join(live) or "none", led["mode"]))
            if any(x.startswith(("updated", "restored")) for x in changes):
                print("Checks recorded before an update or restore no longer count for that criterion: re-run them.")
        elif a.command == "record":
            check, warning = record(d, a.id, a.kind, a.status, a.evidence, a.by, a.cmd, a.lead, a.live, a.max_age)
            print("%s recorded: %s %s %s%s%s (tree %s)" % (
                check["id"], a.id, a.kind, a.status, " by the lead" if a.lead else "",
                ", live for %s" % human(check["live"]["max_age"]) if a.live else "", short_fp(check["fingerprint"])))
            _warn(warning)
        elif a.command == "run":
            check, warning, tail = run(d, a.id, a.kind, a.by, a.argv, a.lead, a.live, a.max_age, a.timeout)
            print(_ran(check, tail))
            _warn(warning)
            return 0 if check["status"] == "pass" else 1
        elif a.command == "rerun":
            done, left = rerun(d, a.stale, a.check, a.by)
            for old, check, warning, tail in done:
                print("%s -> %s" % (old["id"], _ran(check, tail)))
                _warn(warning)
            if left:
                print("Still stale and not run again. Repeat each the way it was made and record it:")
                for ch, why in left:  # a command that was not recorded here is not shown: nobody should copy it
                    print("  %s  %s %s by %s (%s): %s" % (
                        ch["id"], ch["criterion"], ch["kind"], ch["by"], why, _cut(ch.get("cmd") or "", 70)
                        if why == NO_COMMAND else "not shown; run it only if the user asks for it"))
            if not done and not left:
                print("no stale checks: nothing to run again.")
            return 1 if left or any(check["status"] != "pass" for _, check, _, _ in done) else 0
        elif a.command == "finding" and a.fcmd == "add":
            f = finding_add(d, a.sev, a.lens, a.where, a.text)
            print("%s added (%s, %s)." % (f["id"], f["sev"], f["lens"]))
        elif a.command == "finding":
            f = finding_resolve(d, a.id, a.how, a.note, a.accepted_by)
            print("%s %s%s." % (f["id"], f["status"], " (accepted by user)" if f["accepted_by"] else ""))
        elif a.command == "restamp":
            r = restamp(d, a.check, a.reason)
            print("%s restamped to tree %s." % (a.check, short_fp(r["fingerprint"])) if r
                  else "%s already matches the current tree; nothing to restamp." % a.check)
        elif a.command == "void":
            ch = void(d, a.check, a.reason)
            print("%s (%s %s %s) voided: listed, never counted." % (ch["id"], ch["criterion"], ch["kind"], ch["status"]))
        elif a.command == "verdict":
            res = evaluate(d)
            print(json.dumps(res, indent=1) if a.json else verdict_text(res))
            return res["exit"]
        elif a.command == "status":
            print(status_text(d))
        elif a.command == "report":
            sys.stdout.write(report_md(d))
        elif a.command == "where":
            if a.dir:
                load(d)  # says what to do when there is no ledger there
            print(d if a.dir else where(a.root))
    except LedgerError as e:
        print("error: %s" % e, file=sys.stderr)
        return ERROR_EXIT
    except KeyboardInterrupt:  # Ctrl-C or a stop signal while a command ran: it was ended with us
        print("error: interrupted: the command was stopped and nothing was recorded", file=sys.stderr)
        return ERROR_EXIT
    except Exception as e:  # never a traceback with exit 1, which reads as NOT YET
        print("error: %s: %s (ledger.py hit an unexpected problem; run one ledger command at a time)"
              % (type(e).__name__, e), file=sys.stderr)
        return ERROR_EXIT
    return 0


if __name__ == "__main__":
    sys.exit(main())
