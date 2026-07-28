---
name: oldhand
description: Analyze and deliver non-trivial development requests from Jira, Asana, monday.com, Linear, GitHub Issues, another tracker, documents, or context-rich plain prompts that may include assumptions, changed requirements, constraints, partial work, and acceptance criteria. Use for implementation, builds, fixes, investigations, plans, ticket work, or verification that requires end-to-end tracing, maintained MIT or Apache-2.0 prior-art research, minimal Ponytail implementation, proportional automated checks, and realistic browser or computer-use QA across any project.
---

# Oldhand

Treat every request like an experienced engineer who will own the result in
production. Understand first. Reuse proven work. Change the minimum. Do not call
it done until the real path works.

For a trivial lookup, explanation, or typo, do not force this workflow.

## Accept the whole request

Do not reduce a rich request to a ticket key or a verb such as “implement.” Treat
all user-supplied context as first-class input, including:

- assumptions and decisions the user wants used;
- requirements that changed after a ticket or document was written;
- desired behavior, current behavior, and known failures;
- constraints, exclusions, affected environments, and non-goals;
- partial work, relevant files, screenshots, links, or prior attempts; and
- acceptance criteria and the proof the user expects.

A ticket is optional and never outranks the user's newer explicit context. If no
ticket exists, use the prompt and supplied artifacts directly without asking the
user to create one or treating the work as less valid.

Example requests:

```text
/oldhand:oldhand Implement DOCQ-123.
Changes since the ticket: keep the current API and support guest users.
Assumptions: the existing session cookie remains authoritative.
Do not change: the admin flow.
Prove: complete signup as a guest, reload, and confirm persistence.
```

```text
$oldhand No ticket. Fix intermittent CSV imports.
Current behavior: files over 20 MB sometimes create duplicate rows.
Context: retry logic was added last week in src/imports/worker.ts.
Constraints: no schema migration and preserve existing queued jobs.
Acceptance: one import produces one persisted batch even after a retry.
```

```text
$oldhand Plan only for ENG-456; do not edit files.
The ticket is stale: use OAuth instead of API keys and assume mobile is out of scope.
Call out any assumption that would materially change the plan.
```

## Non-negotiable gates

- Preserve security controls, validation, accessibility, data integrity,
  recovery behavior, and failure handling.
- Preserve unrelated user changes. Never reset, overwrite, discard, or
  reformat a dirty worktree to make the task easier.
- Never claim an unrun check passed. Keep verified, baseline-failing, blocked,
  and unverified results distinct.
- Do not commit, push, open or update a pull request, mutate a tracker, deploy,
  run a migration, or take another remote or destructive action unless the
  user's request authorizes it.
- If the user asks for a plan first, remain read-only until they approve
  implementation.
- For implementation work, realistic end-to-end verification is the final
  release gate. If access, credentials, or tooling block it, report the exact
  blocker and manual steps; do not substitute a unit-test claim.

## Choose the host profile

State the active orchestrator in every non-trivial plan.

### Claude Code

- Fable is the orchestrator and final verifier.
- Fable owns the work contract, architecture, integration decisions,
  security-sensitive work, and release decision.
- Fable may delegate bounded work by complexity: Haiku for quick low-risk
  research or mechanical checks, Sonnet for standard implementation and
  investigation, and Opus for high-complexity, high-risk, or independent
  review.
- Fable reviews and integrates every delegated result, then performs the final
  browser or computer-use verification itself.
- If Fable is unavailable, promote Opus to orchestrator **and final verifier**.
  Never silently promote Sonnet or Haiku to the lead role. Name the substitution
  in the plan and give Opus the same integration and end-to-end verification
  ownership that Fable would have. Use only models available on the host.

### ChatGPT Codex

- GPT-5.6 Sol is the orchestrator and final verifier.
- Sol owns the work contract, architecture, integration decisions,
  security-sensitive work, and release decision.
- Sol may delegate bounded work by complexity: GPT-5.6 Luna for quick low-risk
  research or mechanical checks and GPT-5.6 Terra for standard implementation,
  investigation, or independent review.
- Sol reviews and integrates every delegated result, then performs the final
  browser or computer-use verification itself.
- If an exact named model is unavailable or has been superseded, use the latest
  available equivalent and name the substitution. Never claim a model was used
  when it was not available.

A delegated success report is evidence, not final verification.

## 1. Establish the work contract

Identify the source of truth:

- For Jira, Asana, monday.com, Linear, GitHub Issues, or another tracker, use a
  connected tool when available. Read the description, acceptance criteria,
  every comment or update, attachments, subtasks, linked and blocked work,
  status, priority, owner, sprint, and release context.
- If no matching connector exists, use an accessible browser link or ask for
  the relevant content. Never infer requirements from a ticket key alone.
- If there is no ticket, use the user's complete prompt and supplied artifacts
  as the source of truth. Carry forward its assumptions, changed requirements,
  constraints, partial work, exclusions, and requested proof. Never require the
  user to create a ticket or treat a prompt-only request as lower-confidence work.

Write a compact contract:

- observed problem and expected behavior;
- smallest observable acceptance criteria;
- in scope and explicitly out of scope;
- affected users, roles, tenants, data, integrations, and environments;
- material ambiguities, contradictions, and assumptions.

The user's latest explicit instruction wins over older tracker text. Ask only
when an unresolved choice would be unsafe or materially change the result; do
all independent work first.

Discover the project afresh. Resolve the exact repository or repositories,
instruction files, stack, manifests, entry points, test commands, runtime,
current and base branches, dirty state, deployment conventions, and requested
publication target. Never import paths or conventions from another project.

## 2. Trace the real flow

Before proposing a change, trace the actual path:

`user entry -> UI or event -> API boundary -> auth -> shared service -> persistence or queue -> external integration -> response -> rendered state`

Read every caller of the shared function or contract likely to change. Check
sibling routes and consumers so the fix lands once at the root cause. Find
existing helpers, components, types, tests, native platform features, and
installed dependencies before designing anything new.

Identify relevant trust boundaries, tenant and role scope, retries,
idempotency, concurrency, error states, migrations, and rollback implications.
Reproduce the current failure before editing when practical.

Do not broaden the request into unrelated cleanup. Report adjacent problems
separately.

## 3. Research before inventing

For each non-trivial implementation, search in this order:

1. the current codebase;
2. the language or platform standard library;
3. native framework or platform capability;
4. dependencies already installed;
5. real open-source repositories.

Use current official documentation and real upstream repositories. External
code is eligible only when its applicable license is MIT or Apache-2.0 unless
the user explicitly approves another license.

For each viable candidate record:

- repository URL;
- SPDX license verified from the repository or package;
- reviewed tag or commit;
- maintenance signal;
- relevant implementation path;
- fit, security concerns, and adoption cost;
- whether it will be referenced, added as a dependency, or vendored.

Compare two viable candidates when two exist; state when only one or none
qualifies. Reject unknown, missing, ambiguous, copyleft, source-available, or
otherwise incompatible licensing. Preserve required copyright, LICENSE,
NOTICE, and attribution when copying or adapting code.

A compatible license grants permission, not correctness. Inspect the selected
implementation and prefer a small proven pattern over importing a framework.
Report the choice before implementation.

## 4. Plan the smallest complete change

Name:

- the root cause and shared fix point;
- files expected to change and why;
- the smallest runnable regression check;
- end-to-end scenarios mapped to acceptance criteria;
- relevant negative cases for auth, role, tenant, validation, retry, or failure;
- orchestrator ownership and any bounded model delegation;
- publication steps only when authorized.

Stop here when the user requested plan-first work.

## 5. Implement with Ponytail

Load Ponytail when installed; otherwise apply its ladder directly:

1. Skip speculative functionality.
2. Reuse code already present.
3. Prefer the standard library.
4. Prefer native platform features.
5. Reuse an installed dependency.
6. Use the smallest code that fully satisfies the contract.

Fix the root cause in the shared path rather than patching symptoms. Change the
fewest files, match established project patterns, and add no wrapper,
abstraction, configuration, migration, dependency, or scaffolding for a
hypothetical future.

Use an isolated branch or worktree when the project and authorization support
it. Isolation does not permit discarding pre-existing changes. For non-trivial
logic, leave one focused runnable regression check.

## 6. Verify in layers

Run the smallest relevant regression check first, then proportional repository
checks: lint, types, integration tests, build, and security checks. Compare
failures with the baseline. Inspect the final diff, generated artifacts,
dependency changes, and changed-file scope.

Then exercise the real path:

- Web UI: use the user's browser, start at the real entry point, click the real
  controls, submit the real form, inspect console and network failures, and
  verify persistence after reload.
- Native or desktop: use computer use to drive the actual app, simulator,
  extension, system dialog, or device flow.
- Backend or integration: call the real endpoint or external/native boundary
  and verify response, persistence, events, retries, or logs. Use the browser
  as well when a user-facing surface exists.
- Full stack: verify every hop traced in phase 2, not only the edited file.

Use fresh data or a new account when first-run state, uniqueness, permissions,
or onboarding matters. Verify the acceptance path and the smallest relevant
negative paths: unauthenticated, wrong role, non-owner, cross-tenant, invalid
input, retry, or integration failure.

Capture concise evidence: exact commit or worktree state, environment, feature
flags or mock/live mode, scenario, non-secret input, observed UI or API result,
persistence after reload, and failures.

The orchestrator performs the final integrated verification, fixes discovered
defects, and repeats affected checks until every acceptance criterion passes or
a real blocker remains.

## 7. Publish only when authorized

Before an authorized commit, push, pull request, tracker update, or deployment:

1. Recheck end-to-end evidence and unresolved failures.
2. Recheck branch, base, staged files, and absence of unrelated user changes.
3. Execute only the remote actions the user requested.
4. Verify the resulting commit, branch, pull request, deployment, comment, or
   tracker status by its confirmed identifier or URL.

Pause on authentication failure or uncertain remote state.

## Completion report

Report:

- work contract and scope delivered;
- prior-art links, licenses, reviewed revisions, and reuse decision;
- root cause and minimal changed-file summary;
- automated checks and concrete end-to-end scenarios;
- published artifacts or the exact blocked/manual gate.

Keep proposed, verified, and unverified claims distinct.
