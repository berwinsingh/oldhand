# Review lenses

One reviewer applies ONE lens. Read your section, the severity scale and the memo shape at the end.
Stay inside your lens: another reviewer covers the rest, and a finding outside your lens is noise the
chair has to throw away. Every finding is checked against the code before anyone acts on it, so report
what you can show, not what you suspect would sound thorough.

## Severity

- high: an AC or R criterion fails on a realistic input; data is lost or corrupted; a security hole;
  a failure that reports success.
- medium: a wrong result on a plausible edge, messy or error-path input; a sibling left with the same
  defect; a required proof missing; a regression check that would still pass without the fix.
- low: idiom, naming, a small simplification, an unlikely edge that fails visibly (not silently).

Confidence: high = reproduced in a temp copy, or traced line by line to the failing input; medium =
traced, not run; low = suspected. A low-confidence finding is still worth a line if you say what would
confirm it.

## 1. contract

Read: the criteria and out-of-scope list in the brief, the file table in `plan.md`, the whole diff.

Ask:
- Which hunk delivers each AC? Does it handle the messy and negative inputs the AC implies, or only the
  example in the ticket?
- For each R: which existing behaviour could this diff change? Show that it still holds.
- Is every changed line needed by some criterion? Name the scope creep: refactors, renames, reformatting,
  extra features.
- Does the change keep the stated constraints (no new dependency or infrastructure, keep the API,
  separate PRs for separate concerns)?
- Is a value hard-coded to the ticket's example (one customer, id, phrase, date), so the next real input
  fails?
- Does every criterion have its required proof, or a stage that will produce it (e2e from QA is fine
  to come later; a criterion nothing will ever check is not)?

Typical defects: an AC done for the happy path only; a neighbouring case that worked before now
behaves differently; unrelated user changes swept into the diff; a fix keyed to the sample data.

Not a finding: another way to meet a criterion that is already met; an improvement nobody asked for;
missing e2e evidence before QA has run.

## 2. correctness

Read: the diff, then every caller, reader and sibling of the changed code (grep the names; the diff's
context lines are not enough), and the hop table in `trace.md`.

Ask:
- Does every caller still get what it expects: type, None against empty, exceptions, order, units?
- Messy input: empty, None, whitespace, unicode, very large, duplicated, out of order, wrong case,
  partial records.
- Error paths: dependency down, timeout, 4xx or 5xx, malformed response. Is "could not determine" kept
  apart from "none" and from success?
- Retries: is the operation idempotent? Is a non-idempotent request retried after a timeout?
- Concurrency: two requests at once, a double submit, a job processed twice.
- Timeouts: does inner timeout x (retries + 1) at each hop stay under the caller's budget? Does every
  client set one?
- Async: is a 202 or "queued" treated as done?
- The class: does the same defect live in a sibling handler, variant or copy, and is it fixed there?
- Does the regression check fail without the fix (the mutation result in `build.md`), and does it test
  behaviour rather than the implementation?

Typical defects: a second caller not updated; an exception swallowed into an empty result; a retry that
doubles a write; a failure stored in a cache; an off-by-one at a page or batch edge; a test that only
asserts its own mock.

Not a finding: a race with no concurrent caller on this path; input that cannot arrive because an
upstream check rejects it (name the check); performance with no measured or obvious hot path.

## 3. security

Read: the diff, the trust boundaries in `trace.md`, the auth and permission code on the changed paths,
and config defaults.

Ask:
- Is every input that crosses a trust boundary validated for type, size and format?
- Does every new or changed path check the caller's identity, role, tenant and ownership, including
  list, bulk, export and background paths?
- Injection: SQL built from strings, shell commands with interpolated input, template rendering, path
  traversal, prompt injection (untrusted text reaching a model that has tools, or model output used as
  a command, query, URL or path).
- SSRF: does the server fetch a URL that a user or a model controls? Are redirects checked against the
  allowlist too? Are internal addresses blocked?
- Secrets: in code, fixtures, logs, error messages, URLs or query strings, client bundles?
- Unsafe defaults: fail-open on error, debug on, auth off behind a flag, permissive CORS, broad
  permissions.

Typical defects: a new query without the tenant filter; an id from the request used without an
ownership check; a token logged on failure; an allowlist checked before redirects are followed.

Not a finding: an attack that needs the access it would gain; escaping the framework already does (say
where); hardening of code this change does not touch (that is a follow-up).

## 4. data

Read: migrations, models and serializers, every reader of a record shape the diff writes, cache code,
and writes to shared stores and shared config.

Ask:
- Migrations: idempotent, with existence guards? Proven twice on a fresh copy of the deployed schema?
  Applied before the code that needs them, with a lock timeout on big tables? Does the model match the
  table column for column?
- Do readers of stored records and shared config tolerate unknown fields? Will the old code still read
  what the new code writes, so a rollback works?
- Caches: are only successful, checked results stored? Does the key include everything that changes the
  result?
- Shared writes: read, merge, then write; abort if the read fails; sibling keys intact afterwards?
- Single-use or rotating credentials: is the new value held in memory before a persist that can fail?
- An error midway: partial writes, transaction boundaries, data lost or duplicated?
- Are three states kept apart: null (unknown), empty (none), and a list of what was dropped?

Typical defects: a strict model that rejects records carrying one new field, so every read fails; a
whole-object overwrite that drops a sibling key; a cached failure that no retry can fix; a migration
that fails when run twice.

Not a finding: schema taste; scale worries with no evidence of the volume.

## 5. simplicity

Read: the diff, `research.md`, and the module around each change.

Ask:
- Could it be smaller and still meet every criterion?
- Does a helper, type or pattern for this already exist in the codebase (grep for similar names)?
  Would the standard library, a platform feature or an installed dependency do?
- Speculative structure: an interface with one implementation, a factory for one product, config for a
  value that never changes, a flag nobody asked for?
- A new dependency, service, secret store or piece of infrastructure the contract did not ask for?
- One guard in the shared function, or the same guard pasted into every caller?
- Does it match the codebase idiom for errors, logging, naming and tests?
- Dead code, commented-out code, debug prints or unused parameters left behind?

Typical defects: a new util duplicating one two folders away; a wrapper class around a single call;
the same fix copied into each caller.

Not a finding: a deliberate shortcut marked with a `ponytail:` comment that names its ceiling; "could be
more general". Never suggest removing validation, error handling, security checks or accessibility to
save lines: smaller must keep the behaviour.

## 6. ai-behaviour

Only when prompts, models, tool schemas or agent logic change.

Read: prompts and system text, tool and output schemas, the code that parses model output and acts on
it, model configuration, and any eval or gold set with its last results.

Ask:
- Is natural language classified with a regex, keywords or a hard-coded word list where the model
  should judge?
- Is model output validated and coerced at the boundary, so one malformed field does not lose the
  whole result?
- Are ids, URLs, links and names the model copied checked against the source before use?
- Does a timeout, refusal, token-cap stop or parse error look like success or a valid empty answer?
- Is must-hold behaviour enforced in code, or only asked for in the prompt?
- Does the model, or an LLM judge, see the full evidence, with explicit markers where text was cut?
- Can a flag the model sets switch off a rule without quoting evidence that code checks in the input?
- Does an unstable upstream label veto a later step that could look at the evidence itself?
- Is a behaviour claim backed by a gold set or the original failing case, run more than once? Do the
  tests avoid paid model calls?
- Does an unknown model id fall back with a warning, and is a restart noted where a service reads
  model config?

Typical defects: `if "urgent" in text`; a model-picked id used without a lookup; an empty list returned
on a model error; "never do X" in the prompt with no check in code; a verifier fed a clipped page.

Not a finding: prompt wording preferences with no failing case; asking for an eval larger than the
risk; opinions on model choice with no data.

## Memo shape

```markdown
# <lens> lens
Reviewer: <role:model> · Read: <files, or a count> · Ran: <commands in the temp copy, or "nothing">
## Findings
### 1. <the defect in one line>
- Severity: high | medium | low · Confidence: high | medium | low
- Where: path/to/file.ext:123
- Failure: <input or state> -> <what happens>; expected: <what should happen>
- Evidence: <the quoted line or lines, or the command and its output>
- Smallest fix: <one line, optional>
## Checked and found fine
- <what you checked and where, one line each>
## Not checked
- <what this lens could not check, and why>
```

Write "None." under Findings when there are none. Do not pad: the chair checks every finding against
the code and drops what does not hold.
