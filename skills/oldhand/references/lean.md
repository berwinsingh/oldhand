# Lean mode

One agent, no sub-agents, no stage files beyond the contract and the report. It keeps
what makes the verdict mean something: numbered criteria, a regression check proven by
mutation, the lead's own end-to-end run, and the verdict `ledger.py` computes. It drops
the trace, rca, research and plan files, the review panel, the QA fan-out and learn.

## When

- The user asks for it: `/oldhand --lean ...`, "lean", "quick run", "no sub-agents".
- The request is small: one or two files, and the cause is shown by a failing test or
  a short read of one code path.

Switch to the full route, and say so in one line (`Switching to the full route: <why>`),
when any of these shows up: the change needs more than three files; the cause is
still unclear after reading the code path the request names and its callers; a
criterion can only be proved in a browser or on a desktop; or the change touches
authentication, money, data deletion, migrations or another user-facing contract the
request did not mention.

## Steps

LEDGER is `python3 "${CLAUDE_SKILL_DIR}/scripts/ledger.py"` and MUTATE is
`python3 "${CLAUDE_SKILL_DIR}/../oldhand-build/scripts/mutate.py"`. Run them one at a time.

1. **Contract, short form.** Write `.oldhand/<task>/contract.md`: the request in two
   lines, `Mode: implement`, and one `- AC<n>:` line per behaviour the request asks for
   and one `- R<n>:` line per behaviour that must keep working, each observable and
   tagged `(proof: e2e)`; a pure helper may be `(proof: unit)`. Every rule the request
   states is its own criterion: a stated edge case is not optional. Run `LEDGER init
   --dir .oldhand/<task> --title "<title>"` and `LEDGER sync`.
2. **Build.** Read the code path the request names and every caller of what you
   change. Make the smallest change at the shared point. Write one focused regression
   check that fails without the fix, run the project's tests, and run MUTATE on the
   fixed line with that check (`--ledger .oldhand/<task> --id <criterion>`). Record the
   test runs with `LEDGER record --kind unit` (or `integration`) and the real command.
3. **Review, by you.** Read the whole diff once against every criterion and ask: which
   input would still break it, did any caller's behaviour change, is every stated rule
   covered. Record a high or medium problem with `LEDGER finding add`, fix it, and
   resolve it; list lows in the report.
4. **QA, by you.** Run every criterion through the real entry point (the CLI, the HTTP
   endpoint, the page) with the input the request names plus one edge case the request
   states, and record each one: `LEDGER record --id <AC> --kind e2e --status pass|fail
   --evidence <file or output> --by lead:<model> --cmd "<the exact command>" --lead`.
   Save the output you relied on under `.oldhand/<task>/qa/`.
5. **Verdict.** Run `LEDGER verdict`. NOT YET goes back to step 2 for the named
   criterion, inside the round caps. Write a short `report.md` from `LEDGER report`
   (verdict, criteria, what was not verified) and end with the verdict line it printed.

Never write VERIFIED, done or fixed by hand: the verdict is the script's.
