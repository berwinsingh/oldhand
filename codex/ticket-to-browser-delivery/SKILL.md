---
name: ticket-to-browser-delivery
description: Analyze and deliver non-trivial development requests from Jira, Asana, Monday, Linear, GitHub Issues, other trackers, documents, or plain user prompts through source research, minimal Ponytail implementation, automated checks, and realistic browser or computer-use QA. Use for cross-project feature work, bug fixes, investigations, implementation plans, validation, or authorized publication whenever a change must be understood and proven end to end.
---

# Adaptive Development Workflow

Deliver the smallest correct change only after understanding the request, the current project, and existing implementations. Treat realistic browser QA as a release gate, not an optional demonstration.

## Non-negotiable gates

- Preserve security controls, validation, accessibility, data integrity, and failure handling.
- Never overwrite, reset, discard, or reformat unrelated user changes.
- Never claim an unrun check passed. Separate verified results, baseline failures, and unverified work.
- Never commit, push, open or update a PR, comment on a tracker, or change work-item status unless the user authorized that remote action.
- Do not publish or transition implementation work before realistic browser/computer-use QA passes. If QA is blocked, provide exact manual steps and stop.
- If the user asks for a plan first, remain read-only through the plan and wait for approval before branching, editing, or running live workflows.

## Model orchestration

Include the following ownership in every non-trivial plan:

- Use GPT-5.6 Sol as orchestrator and final verifier. If that exact model is unavailable or superseded, use the latest available Sol-equivalent flagship Codex model and name it in the plan.
- Let Sol retain the work contract, architecture, integration decisions, security-sensitive work, and release decision.
- Delegate only bounded work based on complexity: use GPT-5.6 Luna for quick, low-risk research or mechanical checks and GPT-5.6 Terra for standard implementation, investigation, and independent checks. Use only models actually available on the host and state any substitution.
- Require Sol to review and integrate every delegated result. A subagent's success report is evidence, not final verification.
- Require Sol to run the completed change end to end through the browser or computer-use tools, fix discovered defects, and repeat the relevant automated and UI checks until the acceptance criteria pass or a real blocker remains.

## 1. Establish the work contract

1. Identify the source of truth:
   - For Jira, Asana, Monday, Linear, GitHub Issues, or another tracker, use its connected tool when available. Read the description, acceptance criteria, all comments or updates, attachments, subtasks, linked or blocked work, status, priority, assignee, and release or sprint context.
   - If no matching connector exists, use an accessible browser link or ask for the relevant content. Never infer requirements from an issue key alone.
   - If there is no ticketing system, treat the user's prompt and supplied files as the source of truth. Do not require the user to create a ticket.
2. Convert the source into a short contract:
   - observed problem and expected behavior;
   - in-scope and explicitly out-of-scope behavior;
   - affected users, roles, tenants, data, integrations, and environments;
   - acceptance criteria mapped to observable checks;
   - ambiguities and assumptions that could materially change the implementation.
3. When the prompt has no formal acceptance criteria, derive the smallest observable criteria that prove the requested outcome and state material assumptions. Ask only when an unresolved choice would be unsafe or materially change the result.
4. Treat the user's latest explicit instruction as authoritative. Surface conflicts with older tracker content rather than silently choosing.
5. Discover the project afresh: resolve the exact repository or repositories, instruction files, stack, manifests, entry points, test commands, runtime, current/base branches, dirty state, deployment conventions, and publication target.
6. Never import repository paths, branch names, commands, architecture, or release conventions from another project. Do not assume the workspace root is a Git repository or that the default branch is the requested PR base.
7. Preserve a dirty tree and call out overlap with existing changes before editing.

## 2. Trace the real flow

Trace the request end to end before proposing a fix:

- Find the UI/entry point, API or event boundary, authentication and authorization checks, shared service/helper, persistence or queue layer, external integration, and response/rendering path.
- Read every caller of the shared function or contract likely to change. Check sibling routes and consumers so the fix lands once at the root cause.
- Search for existing helpers, components, types, tests, native platform features, and installed dependencies before designing new code.
- Identify trust boundaries, tenant/role scope, retries, idempotency, error states, concurrency, and migration/rollback implications relevant to the request.
- Record the current behavior and, when practical, reproduce the defect before editing.

Do not broaden the request into unrelated cleanup. Report adjacent problems separately.

## 3. Pass the reuse and license gate

For every non-trivial implementation, research before writing:

1. Search in this order: current codebase, language/platform standard library, native framework/platform capability, installed dependencies, then external open-source repositories.
2. Browse official documentation and real upstream repositories. Prefer maintained, production-used projects that solve the same narrow problem.
3. Treat only MIT and Apache-2.0 as eligible unless the user explicitly approves another license. Verify the applicable repository/package/subdirectory license from source; do not rely only on a search snippet or package badge.
4. Record each viable candidate's repository URL, applicable license, tag or commit reviewed, maintenance signal, relevant implementation location, fit, and adoption cost. Compare at least two viable candidates when two exist; state when only one or none qualifies.
5. Reject unknown, ambiguous, copyleft, source-available, non-commercial, or incompatible licensing. Preserve required copyright, LICENSE, NOTICE, and attribution obligations for copied or adapted code.
6. Reuse behavior and small proven patterns without importing a framework wholesale. Prefer the higher rung on the Ponytail ladder and add no dependency when existing or native code is enough.
7. Inspect the selected implementation for security, edge cases, and architectural fit. A compatible license is permission, not proof of correctness.

Summarize the choice before implementation. If no candidate improves on the existing codebase, say so and implement the minimum local fix.

## 4. Plan the smallest complete change

Create a compact plan that names:

- the root cause and shared fix point;
- files expected to change and why;
- the smallest runnable regression check;
- browser/computer-use scenarios mapped to acceptance criteria;
- negative cases required by auth, tenant, role, validation, or failure behavior;
- the Sol/Terra/Luna ownership and bounded delegation for this request;
- publication steps only if requested.

Stop here when the user requested plan-first work.

## 5. Implement with Ponytail

Apply Ponytail's ladder after understanding the flow:

1. Skip speculative functionality.
2. Reuse code already present.
3. Prefer the standard library.
4. Prefer native platform features.
5. Reuse an installed dependency.
6. Use the smallest code that fully satisfies the contract.

Fix the root cause in the shared path rather than patching each symptom. Change the fewest files, preserve established project patterns, and avoid scaffolding, wrappers, configuration, migrations, or dependencies "for later."

For non-trivial logic, add one focused runnable regression check. Do not simplify away trust-boundary validation, authorization, safe errors, data-loss prevention, accessibility, or required recovery behavior.

## 6. Verify in layers

### Automated checks

- Run the smallest relevant regression check first, then the repository's proportional lint, type, integration, build, and security checks.
- Compare failures with the pre-change baseline or unchanged files. Report unrelated failures without calling the suite green.
- Inspect the final diff, changed-file scope, generated artifacts, and dependency/lockfile changes.

### Real end-to-end QA

Use the Browser/Chrome tool for web UI. Use computer use for native apps, system dialogs, simulators, extensions, or flows the browser cannot prove.

- Start from the real user entry point and exercise the actual UI, API, persistence, and integration path rather than mocks or direct database edits.
- Use a genuinely new account or fresh data when creation, onboarding, uniqueness, permissions, or first-run state matters.
- Verify the acceptance path, reload/persistence, and the smallest relevant negative paths such as unauthenticated, wrong role, same-tenant non-owner, cross-tenant, invalid input, retry, or integration failure.
- Verify actual external/native behavior when the request changes it. A unit test of an adapter is not external integration proof.
- Capture concise evidence: environment, scenario, inputs without secrets, observed UI/API state, persistence after reload, and failures.
- Keep Sol as the final release verifier; delegated models cannot self-certify the integrated change.

If tools, credentials, environment, or permissions block realistic QA, do not substitute a claim based on unit tests. Give exact manual steps and expected results, mark the release gate blocked, and wait for confirmation.

## 7. Publish only when authorized

Before any authorized commit, push, PR, work-item comment, or status transition:

1. Recheck browser evidence and unresolved failures.
2. Recheck branch, base, staged files, commit scope, and absence of unrelated user changes.
3. Execute only the remote actions the user requested.
4. Verify the resulting commit, remote branch, PR base/head, assignee/reviewer, work-item comment, and tracker status.

Pause on authentication failure or uncertain remote state. Never claim an artifact exists until its ID or URL is confirmed.

## Completion report

Report:

- **Work contract:** source, acceptance criteria, and scope actually delivered.
- **Reuse evidence:** repository links, license, reviewed tag/commit, and what was reused or rejected.
- **Implementation:** root cause and minimal changed-file summary.
- **Verification:** automated results and concrete browser/computer-use scenarios.
- **Release state:** published artifacts, or the exact blocked/manual gate.

Keep proposed, verified, and unverified claims distinct.
