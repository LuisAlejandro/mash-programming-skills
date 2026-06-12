---
name: rosey-lfg-quality
description: Run the autonomous Rosey quality and shipping pipeline from a rosey-lfg-code handoff: QA autofix, post-review lint when needed, residual durability, and PR creation or update. Use only when explicitly continuing from rosey-lfg-code.
argument-hint: "[PLAN_PATH plus rosey-work handoff context]"
disable-model-invocation: true
---

# Rosey LFG Quality

Run the quality and shipping half of the Rosey autonomous pipeline. This skill starts from a completed `rosey-lfg-code` handoff and finishes with a pull request plus durable QA outcomes.

## Communication while using this skill

**Caveman full** for assistant status prose while this skill runs: drop articles, use fragments when clear, prefer short synonyms, and keep technical terms exact. Technical accuracy unchanged; quoted errors, code, commands, and tool output unchanged. Drop full for security warnings, irreversible confirmations, ambiguous multi-step instructions, user confusion, blockers requiring careful explanation, or when the user asks for normal or long-form wording.

**Artifact boundary:** Caveman full applies to chat/status prose, not QA findings, PR bodies, residual summaries, handoff fields, or the final `<promise>DONE</promise>` signal.

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default for direct chat invocation. Child skills may ask blocking questions and wait for user answers.
- `mode:non-interactive` — scripted or skill-to-skill execution. Child skills must not ask blocking questions or wait for confirmations.

Strip the interaction mode token before parsing the handoff context. If no interaction mode token is present, set `INTERACTION_MODE=interactive`.

If multiple interaction mode tokens appear, stop and report the conflict.

### Non-Interactive Mode Rules

When `INTERACTION_MODE=non-interactive`:

- Do not use blocking question tools or wait for user confirmation.
- Carry residual findings into durable PR or plan-linked artifacts instead of asking the user.
- Invoke child skills with their no-prompt submodes where available.
- Stop with a concise blocker if safe progress requires human judgment.

## Stage Boundary

`rosey-lfg-quality` owns:

- Code review via `rosey-qa`
- Post-review verification through `rosey-lint` when QA changes files
- Residual review finding durability
- PR creation or update through `rosey-pr`
- Final `<promise>DONE</promise>` signal

`rosey-lfg-quality` implements the quality and PR portion of MAINTAINER release ritual step 4. It does not merge PRs, watch or fix CI, create milestones, or publish releases. App repo PRs are handled by auto-merge workflows after this skill creates or updates the PR. Pipeline failures are handled outside this v1 flow by Cursor Bugbot and existing automation.

Do not invoke `rosey-brainstorm`, `rosey-plan`, or `rosey-work` from this skill. If code-stage context is missing, stop and ask for the `rosey-lfg-code` handoff.

In non-interactive mode, missing code-stage context is a hard blocker; stop instead of asking for the handoff.

## Required Input

Require a handoff block from `rosey-lfg-code` or equivalent structured context containing:

- `REQUIREMENTS_PATH`
- `PLAN_PATH`
- `FILES_CHANGED`
- `WHAT_WAS_IMPLEMENTED`
- `PLAN_OR_REQUIREMENTS`
- `SENTRUX_REVIEW_CONTEXT`

Also consume compact fields when present: `DONE`, `VERIFY`, `BLOCKERS`, `HINDSIGHT`, and `SENTRUX`. These fields are machine-to-machine receipts; carry them forward tersely instead of expanding them into narrative.

Stop if `PLAN_PATH` is missing. Stop if both `FILES_CHANGED` and `WHAT_WAS_IMPLEMENTED` are missing, because review scope and PR context would be ambiguous.

## Skill Resolution

When invoking a skill below, resolve its name against the available skills list and use the exact listed entry. Some hosts may namespace project skills. Do not guess an invocation name that is not available.

## Pipeline

### 1. Code Review

Invoke `rosey-qa` with:

```text
mode:autofix plan:<PLAN_PATH>
```

Pass the code-stage handoff context in the invocation context:

- `FILES_CHANGED`
- `WHAT_WAS_IMPLEMENTED`
- `PLAN_OR_REQUIREMENTS`
- `SENTRUX_REVIEW_CONTEXT`
- `DONE`, `VERIFY`, `BLOCKERS`, `HINDSIGHT`, and `SENTRUX` when present

Read the review result and run artifact path. Record:

- Safe fixes applied
- Residual actionable work
- Advisory or release notes

`rosey-qa` must not commit, push, or create a PR.

### 2. Post-Review Verification

If `rosey-qa` changed files:

1. Update `FILES_CHANGED` with every file modified by review fixes.
2. Invoke `rosey-lint` again. In non-interactive mode, include `mode:non-interactive`.
3. If lint/build verification fails and cannot be safely fixed, stop and report the failing command and relevant output.
4. Refresh Sentrux handoff context when possible. If a full refresh is unavailable, mark `SENTRUX_REVIEW_CONTEXT` as pre-review and note that QA fixes occurred afterward.

Do not output DONE while review fixes remain outside the final PR flow. `rosey-pr` must include all review-fix changes when it commits and pushes.

### 3. Residual Review Findings

If `rosey-qa` reports `Residual actionable work: none.`, continue.

If residual actionable findings remain:

- Do not prompt the user. This is an autonomous pipeline.
- Compose a `## Residual Review Findings` section with severity, file:line, title, and any suggested fix or reason the item was not auto-applied.
- Carry this section into the `rosey-pr` context so it is recorded in the PR body or plan-linked PR summary.
- If `rosey-pr` cannot create or update a PR, write the residuals into the plan-linked PR summary fallback only if that artifact is created by `rosey-pr`; otherwise stop and report that residuals were not made durable.

### 4. Pull Request

Invoke `rosey-pr` with:

```text
plan:<PLAN_PATH>
```

In non-interactive mode, invoke `rosey-pr` with:

```text
mode:non-interactive plan:<PLAN_PATH>
```

Provide context for the PR description:

- Requirements path: `REQUIREMENTS_PATH`
- Plan path: `PLAN_PATH`
- `WHAT_WAS_IMPLEMENTED`
- Testing, lint, build, memory, and Sentrux notes from `VERIFY`, `BLOCKERS`, `HINDSIGHT`, `SENTRUX`, and `SENTRUX_REVIEW_CONTEXT`
- `SENTRUX_REVIEW_CONTEXT`
- Residual review findings, if any

Gate before continuing:

- Verify a PR was created or an existing PR was updated.
- Record PR number, URL, base branch, and head branch.
- Verify `rosey-pr` wrote the plan-linked PR summary artifact when `PLAN_PATH` is known.

### 5. Done Signal

Output exactly:

```text
<promise>DONE</promise>
```

Only emit the done signal after:

- `PLAN_PATH` exists.
- QA ran and residuals are durable.
- Lint/build verification passed after QA changes, when QA changed files.
- PR was created or updated.

## Prohibited Behavior

- Do not invoke `rosey-brainstorm`, `rosey-plan`, or `rosey-work`.
- Do not use the GitHub CLI for GitHub actions.
- Do not assign or bootstrap PR labels.
- Do not create a separate product-document stage.
- Do not watch, fix, or summarize CI failures as part of this skill.
- Do not output `<promise>DONE</promise>` while uncommitted review fixes or unresolved residuals are only in transient chat.
