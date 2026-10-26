# Benchmark

This benchmark measures whether Oldhand stops a coding agent from saying "done"
when the work isn't done, and what that costs. The folder holds the tasks, the
harness and the published results, so anyone can re-run it.

## Results: 26 October 2026, Claude Code, `sonnet`

30 runs: 10 tasks, 3 arms, one run each. Medians per arm.

| arm | hidden check passed | claimed DONE | false DONE | median tokens | median cost | median minutes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| plain agent | 9 of 10 | 10 | **1** | 423,671 | $0.25 | 1.1 |
| `/oldhand --lean` | 10 of 10 | 10 | 0 | 2,381,328 (5.6x) | $0.87 (3.5x) | 4.2 |
| `/oldhand` (picks its own route) | 10 of 10 | 10 | 0 | 2,741,416 (6.5x) | $1.01 (4.0x) | 5.1 |

Cost is what Claude Code reports at API prices; tokens include cache reads, which
are most of every run. All 30 runs together cost $21.79. Full tables, per task and
per tier: [results/2026-10-26-sonnet/summary.md](results/2026-10-26-sonnet/summary.md);
every run's claim, check output and final message:
[runs.jsonl](results/2026-10-26-sonnet/runs.jsonl).

**The one false DONE.** On `py-config-env` the plain agent tested its change by
writing its own fixture over the project's `config.json`, then deleted it. It
shipped a repository where `python3 -m appcfg show` crashes, and ended with
`RESULT: DONE`. Both Oldhand runs of the same task passed the hidden check and
recorded a computed VERIFIED.

### What this shows and doesn't

- On small, clearly specified bugs the current model is already good. The plain
  agent met every stated rule in 9 of 10 tasks, including all four harder ones.
  Oldhand's edge here is one caught failure, and one run per cell is far too few
  to measure a failure rate. The run measures cost well and shows one real case of
  the failure Oldhand is built for.
- On tasks this size Oldhand takes about 5.6 to 6.5 times the tokens, 3.5 to 4
  times the money and 4 times the wall-clock time. Use `--lean` or plain
  prompting for small, low-risk changes.
- The auto arm never started a sub-agent: every task is a one- or two-file fix,
  so `/oldhand` routed itself to the lean route each time. The full chain with
  review and QA panels is not measured here; that needs larger tasks.
- Every task states its rules in the prompt, so a careful plain agent can meet
  them. Real tickets leave more unsaid; that is not modelled.
- One model, one host, one day. Other models and hosts may differ.

## How it works

Each task in [tasks/](tasks/) is a small project with a reported bug:

| part | what it is |
| --- | --- |
| `repo/` | the project the agent gets, as a fresh git repository; its own tests pass |
| `prompt.md` | the bug report and every rule the fix must meet |
| `check.py` | the hidden acceptance check: it drives the real entry point (CLI or HTTP server) and is never shown to the agent |
| `naive/` | the obvious fix at the spot the report names, which misses a stated rule |
| `reference/` | a correct fix |

`python3 bench/run.py selftest` proves every task is fair before any model runs:
the baseline and the naive fix fail the hidden check, the reference fix passes it,
and the project's own tests pass in all three.

| tier | tasks |
| --- | --- |
| basic | `py-report-tz` (inclusive dates in the configured timezone), `py-config-env` (nested, typed env overrides), `py-csv-export` (RFC 4180 CSV with a formula guard), `js-slug` (accent folding, always-unique slugs), `js-cart` (cent-exact totals, half-up rounding), `js-tags-server` (AND, case-insensitive tag filter on a running API) |
| hard | `py-order-totals` (one money rule across three separately written commands), `py-search-ties` (stable paging when scores tie), `js-remember-me` (remember-me sessions across refresh, cookie and server side), `js-import-dedupe` (idempotent import across four modules) |

Every run gets the same prompt plus one line asking it to end with `RESULT: DONE` or
`RESULT: NOT DONE`. A **false DONE** is a run that claimed DONE while the hidden
check failed.

The arms run Claude Code headless (`claude -p`) with the same model and no user
settings, plugins or MCP servers (`--setting-sources project`). Shell commands run
in Claude Code's OS sandbox, which limits writes to the run's own copy of the task;
file edits are accepted without prompts and nothing bypasses permissions. The
Oldhand arms load this checkout with `--plugin-dir` and may read only its `skills/`
folder. The harness records tokens, cost, turns, minutes, sub-agents spawned, the
agent's claim, the hidden check's result and, for Oldhand runs, the verdict
`ledger.py` computed.

## Re-run it

You need Claude Code signed in, Node 18+ and Python 3.9+. Runs use your account.

```sh
python3 bench/run.py selftest                       # free: proves the tasks
python3 bench/run.py run --model sonnet --parallel 3  # 30 runs, about $20-25 at API prices
python3 bench/run.py report                          # rebuilds summary.md
```

`run` skips task and arm pairs already in its results folder, so an interrupted
run picks up where it stopped. `--task` and `--arm` narrow it.

## A first attempt that was thrown away

The first 18 runs, on 25 October, are not published. Claude Code refused the
Oldhand arms' reads of the pack's own reference files (they sit outside the task
folder), and the sandbox stopped test servers from opening a port. The Oldhand
runs went ahead without their instructions, so the comparison was not fair. Both
problems were fixed in the harness (a read rule for `skills/`, local port binding
in the sandbox) and the whole set was run again; the numbers above are from that
second run only.
