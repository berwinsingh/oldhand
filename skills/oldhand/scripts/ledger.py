#!/usr/bin/env python3
"""The proof ledger for Oldhand. Standard library only, no network.

One JSON file per task, .oldhand/<task>/ledger.json, holds the criteria read from
contract.md, every check anyone ran against them, the review findings and the
restamps. The verdict is computed from that file, never written by hand.

    python3 ledger.py init --dir .oldhand/<task> --title "<title>" [--mode implement]
    python3 ledger.py sync [--dir D]
    python3 ledger.py record --id AC1 --kind e2e --status pass --evidence qa/results/S1.json \\
        --by "lead:fable" --cmd "qa.py scenario S1" [--lead] [--dir D]
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

Every record stamps the working-tree fingerprint: git HEAD, a hash of
`git diff HEAD --binary` and a hash of the untracked, non-ignored files (files over
5 MB by name and size; nested repos and submodules by their own state). .oldhand/
itself is left out. A check recorded on another fingerprint is stale until it is
re-run or restamped with a reason. Outside git the fingerprint is "no-git" and
staleness is not tracked; the verdict says so. If git fails where git was in use,
that is an error, never "no-git".

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
or the check does not count.

Exit codes: verdict exits 0 VERIFIED, 1 NOT YET, 2 BLOCKED, 3 INCOMPLETE. Every other
command exits 0 when it worked. Any error exits 4 with a message that says what to do.
Writers lock the task folder, but run ledger commands one after another anyway.
"""

import argparse
import contextlib
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

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


class LedgerError(Exception):
    pass


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


# --- git and the fingerprint ---
def _git(args, cwd):
    """stdout bytes of a git command, or None when git is missing or the command fails."""
    try:
        p = subprocess.run(["git"] + args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
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


def fingerprint(d, led=None):
    """The working-tree fingerprint, or "no-git" outside git. When git fails where git is or was in use, that is an
    error: a silent "no-git" would switch staleness off."""
    root = repo_root(d)
    if root:
        return _tree_state(root)
    dotgit = _has_dotgit(d)
    if dotgit or (led and any(ch["fingerprint"] != "no-git" for ch in led["checks"])):
        raise LedgerError("git did not answer in %s although %s: check that git is on PATH and that `git status` "
                          "works there (a 'dubious ownership' error needs `git config --global --add safe.directory`)"
                          % (d, "a .git folder is above it" if dotgit else "earlier checks were recorded in git"))
    return "no-git"


# Plain patch text: the user's external diff and textconv drivers would hide real changes.
DIFF = ["diff", "--binary", "--submodule=diff", "--no-ext-diff", "--no-textconv"]


def _tree_state(root, depth=0):
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
            h.update(_tree_state(path, depth + 1).encode())
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
    head, diff, untracked = fp.split(":")
    return "%s:%s:%s" % (head[:10], diff[:8], untracked[:8])


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
    return led


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
def evidence_missing(d, root, ev):
    """True when the evidence looks like a single file path and that path does not exist."""
    ev = (ev or "").strip()
    if not ev or re.search(r"\s", ev) or "://" in ev or not PATHISH.search(ev):
        return False
    p = re.sub(r":\d+(?::\d+)?$", "", ev)
    if os.path.isabs(p):
        return not os.path.exists(p)
    return not any(os.path.exists(os.path.join(base, p)) for base in (d, root) if base)


def record(d, cid, kind, status, evidence, by, cmd=None, lead=False):
    """Append a check. Returns (check, warning or None)."""
    d = os.path.abspath(d)
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
    with _locked(d):
        led = load(d)
        criterion(led, cid)
        check = {"id": "C%d" % (len(led["checks"]) + 1), "criterion": cid, "kind": kind, "status": status,
                 "evidence": evidence.strip(), "by": by.strip(), "cmd": cmd.strip(), "lead": bool(lead),
                 "fingerprint": fingerprint(d, led), "time": now()}
        led["checks"].append(check)
        save(d, led)
    warning = None
    if evidence_missing(d, project_root(d), evidence):
        warning = ("evidence %s was not found under the task folder or the repo: this check will not count "
                   "until the file exists" % evidence.strip())
    return check, warning


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
        if check["fingerprint"] == fp or any(r["check"] == cid and r["fingerprint"] == fp for r in led["restamps"]):
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
    fp = fingerprint(d, led)
    git = fp != "no-git"
    restamped = {(r["check"], r["fingerprint"]) for r in led["restamps"]}
    order = {ch["id"]: i for i, ch in enumerate(led["checks"])}
    live = [c for c in led["criteria"] if c["status"] == "live"]
    since = {c["id"]: c.get("since_check", 0) for c in live}

    def fresh(ch):
        return not git or ch["fingerprint"] == fp or (ch["id"], fp) in restamped

    def missing(ch):
        return evidence_missing(d, root, ch["evidence"])

    def current(ch):
        """Not voided, and recorded against the criterion's present wording."""
        return not ch.get("void") and order[ch["id"]] >= since.get(ch["criterion"], 0)

    incomplete, notyet, blocked, notes = [], [], [], []
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
            if not fresh(ch) and "stale" not in row["flags"]:
                row["flags"].append("stale")
            if missing(ch):
                if "evidence missing" not in row["flags"]:
                    row["flags"].append("evidence missing")
                incomplete.append("%s: the evidence of %s (%s) is not there, so it does not count: save the evidence "
                                  "at that path or record the check again" % (c["id"], ch["id"], ch["evidence"]))
                continue
            if ch["status"] == "fail":
                notyet.append("%s fails (%s %s by %s): fix it and record a new run" % (c["id"], ch["id"], ch["kind"], ch["by"]))
            if not fresh(ch):
                notyet.append("%s: %s was recorded on an older tree (%s, now %s): re-run it and record again, or "
                              "`ledger.py restamp --check %s --reason ...` if the change cannot affect it"
                              % (c["id"], ch["id"], short_fp(ch["fingerprint"]), short_fp(fp), ch["id"]))
            elif ch["status"] == "blocked":
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
            and current(ch) and fresh(ch) and not missing(ch) for ch in led["checks"]):
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
        notes.append("no git here: staleness is not tracked, so a check may describe an older version of the files")

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
    return {"verdict": verdict, "exit": VERDICT_EXIT[verdict], "title": led["title"], "mode": led["mode"],
            "dir": d, "fingerprint": fp, "criteria": rows, "open_findings": open_findings,
            "reasons": reasons, "notes": notes}


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
           "Tree: %s" % ("no git, staleness not tracked" if res["fingerprint"] == "no-git" else short_fp(res["fingerprint"])), ""]
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


def status_text(d):
    d = os.path.abspath(d)
    led = load(d)
    out = ["Task: %s (mode %s)  %s" % (led["title"], led["mode"], d), "", "Criteria:"]
    out.append(_table(["id", "status", "proof", "text"], [[c["id"], c["status"], c["proof"], _cut(c["text"])]
                                                         for c in led["criteria"]]) if led["criteria"] else "  none yet")
    out += ["", "Checks:"]
    out.append(_table(["id", "criterion", "kind", "status", "lead", "by", "tree", "evidence"],
                      [[c["id"], c["criterion"], c["kind"], c["status"] + (" (void)" if c.get("void") else ""),
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
    tree = "no git" if res["fingerprint"] == "no-git" else short_fp(res["fingerprint"])
    out += ["", "Computed by ledger.py from ledger.json at %s on tree %s. Not written by hand." % (now(), tree)]
    return "\n".join(out) + "\n"


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
            check, warning = record(d, a.id, a.kind, a.status, a.evidence, a.by, a.cmd, a.lead)
            print("%s recorded: %s %s %s%s (tree %s)" % (check["id"], a.id, a.kind, a.status,
                                                        " by the lead" if a.lead else "", short_fp(check["fingerprint"])))
            if warning:
                print("warning: " + warning, file=sys.stderr)
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
    except Exception as e:  # never a traceback with exit 1, which reads as NOT YET
        print("error: %s: %s (ledger.py hit an unexpected problem; run one ledger command at a time)"
              % (type(e).__name__, e), file=sys.stderr)
        return ERROR_EXIT
    return 0


if __name__ == "__main__":
    sys.exit(main())
