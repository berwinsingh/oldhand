#!/usr/bin/env python3
"""The Oldhand benchmark. Standard library only.

Each task in tasks/<id>/ is a small project with a reported bug (prompt.md), a hidden
acceptance check the agent never sees (check.py), the obvious-but-incomplete fix (naive/)
and a correct fix (reference/). The agent gets a fresh git copy of repo/ and the prompt;
afterwards check.py decides whether the request was really met, and the agent's own last
line (RESULT: DONE or RESULT: NOT DONE) says whether it claimed it was.

    python3 bench/run.py selftest                     # no model calls: proves every task is fair
    python3 bench/run.py run --model sonnet [--arm plain --arm lean --arm full] [--task ID] [--parallel 3]
    python3 bench/run.py report [--results bench/results/<run>]

Arms: plain (the agent alone), lean (/oldhand --lean) and auto (/oldhand, which picks its own
route: lean for small fixes, the full chain with sub-agents otherwise). Every arm runs
Claude Code headless in its OS sandbox (writes only inside the run's copy of the task) with the
same prompt, the same model and no user or plugin settings;
the two Oldhand arms load this checkout as a plugin (--plugin-dir), so they test the
working tree. A "false done" is a run that claimed DONE while the hidden check failed.
"""

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

BENCH = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BENCH)
TASKS = os.path.join(BENCH, "tasks")
ARMS = ("plain", "lean", "auto")
TIMEOUT = 60 * 60  # per run
WORK = os.path.join(tempfile.gettempdir(), "oldhand-bench")
SUFFIX = (
    "\n\nWork only in this repository (the current directory). You can't ask questions: make reasonable "
    "assumptions and say what you assumed. When you have finished, end your final message with exactly one "
    "line: `RESULT: DONE` if the request is fully done and verified, or `RESULT: NOT DONE` if it is not."
)
CLAIM = re.compile(r"RESULT:\s*(NOT DONE|DONE)\b")


def tasks(only=None):
    out = []
    for name in sorted(os.listdir(TASKS)):
        path = os.path.join(TASKS, name)
        if os.path.isfile(os.path.join(path, "task.json")) and (not only or name in only):
            with open(os.path.join(path, "task.json")) as fh:
                out.append(dict(json.load(fh), path=path))
    return out


def shim_env():
    """PATH with a python3 that is this interpreter, so tasks run the same everywhere."""
    d = tempfile.mkdtemp(prefix="oldhand-bench-bin-")
    for name in ("python3", "python"):
        os.symlink(sys.executable, os.path.join(d, name))
    env = dict(os.environ, PATH=d + os.pathsep + os.environ.get("PATH", ""))
    for k in [k for k in env if k.upper().startswith("APP_")]:
        del env[k]
    return env


def overlay(src, dst):
    for base, _, files in os.walk(src):
        for f in files:
            rel = os.path.relpath(os.path.join(base, f), src)
            os.makedirs(os.path.dirname(os.path.join(dst, rel)), exist_ok=True)
            shutil.copy2(os.path.join(base, f), os.path.join(dst, rel))


def workdir(task, parent, *overlays):
    d = os.path.join(parent, task["id"])
    shutil.copytree(os.path.join(task["path"], "repo"), d)
    for o in overlays:
        overlay(os.path.join(task["path"], o), d)
    return d


def git_init(d, env):
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                ["git", "-c", "user.name=bench", "-c", "user.email=bench@example.invalid", "commit", "-qm", "baseline"]):
        subprocess.run(cmd, cwd=d, env=env, check=True, capture_output=True)


def sh(cmd, cwd, env, timeout=300):
    p = subprocess.run(cmd, cwd=cwd, env=env, shell=True, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr)[-2000:]


def check(task, d, env):
    p = subprocess.run([sys.executable, "-I", os.path.join(task["path"], "check.py"), d], env=env,
                       capture_output=True, text=True, timeout=600)
    return p.returncode == 0, p.stdout[-3000:] + p.stderr[-1000:]


# ---------- selftest ----------
def selftest(args):
    env = shim_env()
    bad = 0
    for task in tasks(args.task):
        parent = tempfile.mkdtemp(prefix="oldhand-bench-self-")
        rows = []
        for label, overlays, want_check in (("baseline", (), False), ("naive fix", ("naive",), False),
                                            ("reference fix", ("reference",), True)):
            d = workdir(task, os.path.join(parent, label.replace(" ", "-")), *overlays)
            tcode, tout = sh(task["test"], d, env)
            ok, out = check(task, d, env)
            fine = tcode == 0 and ok == want_check
            bad += not fine
            rows.append("  %-14s visible tests %-4s hidden check %-4s %s" % (
                label, "pass" if tcode == 0 else "FAIL", "pass" if ok else "fail", "ok" if fine else "UNEXPECTED"))
            if not fine:
                rows.append("    " + (tout if tcode else out).strip().replace("\n", "\n    ")[-1500:])
        print("%s: %s\n%s" % (task["id"], task["summary"], "\n".join(rows)))
        shutil.rmtree(parent, ignore_errors=True)
    print("\nselftest: %s" % ("every task is fair: the baseline and the obvious fix fail the hidden check, "
                              "the reference fix passes it" if not bad else "%d unexpected results" % bad))
    return 1 if bad else 0


# ---------- run ----------
def prompt_for(task, arm):
    with open(os.path.join(task["path"], "prompt.md")) as fh:
        text = fh.read().strip() + SUFFIX
    return {"plain": text, "lean": "/oldhand:oldhand --lean " + text, "auto": "/oldhand:oldhand " + text}[arm]


def parse_stream(path):
    init, result, spawned = {}, {}, 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("type") == "system" and ev.get("subtype") == "init" and not init:
                init = ev
            elif ev.get("type") == "result":
                result = ev
            elif ev.get("type") == "assistant" and not ev.get("parent_tool_use_id"):
                for part in (ev.get("message") or {}).get("content") or []:
                    if part.get("type") == "tool_use" and part.get("name") in ("Agent", "Task"):
                        spawned += 1
    return init, result, spawned


def token_total(result):
    total = 0
    for usage in (result.get("modelUsage") or {}).values():
        total += sum(int(usage.get(k) or 0) for k in
                     ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens"))
    if not total:
        u = result.get("usage") or {}
        total = sum(int(u.get(k) or 0) for k in
                    ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    return total


def ledger_verdicts(d, env):
    out = []
    root = os.path.join(d, ".oldhand")
    if not os.path.isdir(root):
        return out
    ledger = os.path.join(ROOT, "skills", "oldhand", "scripts", "ledger.py")
    for name in sorted(os.listdir(root)):
        if os.path.isfile(os.path.join(root, name, "ledger.json")):
            p = subprocess.run([sys.executable, ledger, "verdict", "--json", "--dir", os.path.join(root, name)],
                               cwd=d, env=env, capture_output=True, text=True, timeout=60)
            try:
                out.append(json.loads(p.stdout)["verdict"])
            except (ValueError, KeyError):
                out.append("unreadable")
    return out


def one_run(task, arm, model, out_dir, env):
    # Outside this checkout: Claude Code treats files under a loaded plugin's folder as sensitive.
    run_dir = os.path.join(WORK, os.path.basename(out_dir), "%s-%s" % (task["id"], arm))
    os.makedirs(run_dir)
    d = workdir(task, run_dir)
    git_init(d, env)
    stream = os.path.join(out_dir, "streams", "%s-%s.jsonl" % (task["id"], arm))
    os.makedirs(os.path.dirname(stream), exist_ok=True)
    # Sandboxed: shell commands run in the OS sandbox, which limits writes to the run's own copy of the
    # task; inside it they run without prompts, and file edits are accepted. Nothing bypasses permissions.
    sandbox = {"sandbox": {"enabled": True, "autoAllowBashIfSandboxed": True, "allowUnsandboxedCommands": False,
                           "network": {"allowLocalBinding": True}}}
    cmd = ["claude", "-p", prompt_for(task, arm), "--model", model, "--output-format", "stream-json", "--verbose",
           "--setting-sources", "project", "--settings", json.dumps(sandbox), "--permission-mode", "acceptEdits",
           "--allowedTools", "Bash", "Edit", "Write", "MultiEdit",
           # the Oldhand arms read the pack's references and scripts; nothing else outside the task copy
           "Read(/%s/skills/**)" % ROOT]
    if arm != "plain":
        cmd += ["--plugin-dir", ROOT]
    started = time.time()
    timed_out = False
    with open(stream, "w") as fh:
        try:
            subprocess.run(cmd, cwd=d, env=env, stdout=fh, stderr=subprocess.STDOUT, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            timed_out = True
    wall = time.time() - started
    init, result, spawned = parse_stream(stream)
    text = result.get("result") or ""
    claims = CLAIM.findall(text)
    passed, check_out = check(task, d, env)
    tcode, _ = sh(task["test"], d, env)
    row = {
        "task": task["id"], "arm": arm, "model": model, "requested_model": model,
        "session_model": init.get("model"), "oldhand_loaded": any("oldhand" in str(s) for s in
                                                                  (init.get("skills") or []) + (init.get("slash_commands") or [])),
        "claim": claims[-1] if claims else "none", "hidden_check": "pass" if passed else "fail",
        "visible_tests": "pass" if tcode == 0 else "fail", "ledger_verdicts": ledger_verdicts(d, env),
        "tokens": token_total(result), "cost_usd": result.get("total_cost_usd"), "turns": result.get("num_turns"),
        "minutes": round(wall / 60, 1), "subagents": spawned, "timed_out": timed_out,
        "is_error": bool(result.get("is_error")) or not result, "final_message": text[-1500:],
        "check_output": check_out, "finished": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    row["false_done"] = row["claim"] == "DONE" and not passed
    with open(os.path.join(out_dir, "runs.jsonl"), "a") as fh:
        fh.write(json.dumps(row) + "\n")
    return row


def run(args):
    env = shim_env()
    out_dir = args.results or os.path.join(BENCH, "results", dt.date.today().isoformat() + "-" + args.model)
    os.makedirs(out_dir, exist_ok=True)
    done = set()
    if os.path.exists(os.path.join(out_dir, "runs.jsonl")):
        with open(os.path.join(out_dir, "runs.jsonl")) as fh:
            done = {(r["task"], r["arm"]) for r in map(json.loads, fh)}
    jobs = [(t, a) for t in tasks(args.task) for a in (args.arm or ARMS) if (t["id"], a) not in done]
    print("%d runs to do in %s (%d already done)" % (len(jobs), out_dir, len(done)), flush=True)
    with cf.ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futs = {pool.submit(one_run, t, a, args.model, out_dir, env): (t["id"], a) for t, a in jobs}
        for f in cf.as_completed(futs):
            try:
                r = f.result()
                print("%-16s %-5s claim %-8s hidden %-4s %8d tokens  %s min  %d sub-agents%s" % (
                    r["task"], r["arm"], r["claim"], r["hidden_check"], r["tokens"], r["minutes"], r["subagents"],
                    "  FALSE DONE" if r["false_done"] else ""), flush=True)
            except Exception as e:  # keep the other runs going; the row is simply missing
                print("%s %s crashed: %r" % (futs[f] + (e,)), flush=True)
    return report(argparse.Namespace(results=out_dir))


# ---------- report ----------
def report(args):
    path = args.results or sorted(
        os.path.join(BENCH, "results", d) for d in os.listdir(os.path.join(BENCH, "results")))[-1]
    with open(os.path.join(path, "runs.jsonl")) as fh:
        rows = [json.loads(l) for l in fh if l.strip()]
    tier = {t["id"]: t.get("tier", "basic") for t in tasks()}
    med = lambda xs: statistics.median(xs) if xs else 0
    lines = ["| tasks | arm | runs | hidden check passed | claimed DONE | false DONE | median tokens | median cost (USD) | "
             "median minutes | sub-agents (total) |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for group in ("basic", "hard", "all"):
        for arm in ARMS:
            rs = [r for r in rows if r["arm"] == arm and group in ("all", tier.get(r["task"]))]
            if not rs:
                continue
            lines.append("| %s | %s | %d | %d | %d | %d | %s | %.2f | %s | %d |" % (
                group, arm, len(rs), sum(r["hidden_check"] == "pass" for r in rs), sum(r["claim"] == "DONE" for r in rs),
                sum(r["false_done"] for r in rs), "{:,}".format(int(med([r["tokens"] for r in rs]))),
                med([r["cost_usd"] or 0 for r in rs]), round(med([r["minutes"] for r in rs]), 1), sum(r["subagents"] for r in rs)))
    per = ["| task | " + " | ".join(a for a in ARMS) + " |", "| --- |" + " --- |" * len(ARMS)]
    for t in sorted({r["task"] for r in rows}, key=lambda t: (tier.get(t) != "basic", t)):
        cells = []
        for a in ARMS:
            r = next((r for r in rows if r["task"] == t and r["arm"] == a), None)
            cells.append("" if r is None else "%s, claimed %s, %s tokens%s" % (
                "pass" if r["hidden_check"] == "pass" else "**fail**", r["claim"], "{:,}".format(r["tokens"]),
                ", %s" % "/".join(r["ledger_verdicts"]) if r["ledger_verdicts"] else ""))
        per.append("| %s | %s |" % (t, " | ".join(cells)))
    text = "\n".join(["Summary", "", *lines, "", "Per task (hidden check, the agent's claim, tokens, Oldhand verdict)",
                      "", *per, ""])
    with open(os.path.join(path, "summary.md"), "w") as fh:
        fh.write(text)
    print(text)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("selftest")
    s.add_argument("--task", action="append")
    r = sub.add_parser("run")
    r.add_argument("--model", default="sonnet")
    r.add_argument("--arm", action="append", choices=ARMS)
    r.add_argument("--task", action="append")
    r.add_argument("--parallel", type=int, default=3)
    r.add_argument("--results", help="results folder; re-running skips the task/arm pairs already in it")
    p = sub.add_parser("report")
    p.add_argument("--results")
    a = ap.parse_args(argv)
    return {"selftest": selftest, "run": run, "report": report}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
