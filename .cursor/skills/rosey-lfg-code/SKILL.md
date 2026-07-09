---
name: rosey-lfg-code
description: "Run the autonomous Rosey code-production pipeline — brainstorm requirements, create a plan, implement it with rosey-work, run lint/build through rosey-work, and emit handoff context for rosey-lfg-quality. Use only when explicitly requested for hands-off code-stage execution of a software task."
argument-hint: "[feature description]"
disable-model-invocation: true
---

# Rosey LFG Code

Run the code-production half of the Rosey autonomous pipeline. This skill produces implementation plus handoff context. It does not run code review, create a PR, handle post-PR CI, or emit the final DONE signal.

## Communication while using this skill

**Caveman full** for assistant status prose while this skill runs: drop articles, use fragments when clear, prefer short synonyms, and keep technical terms exact. Technical accuracy unchanged; quoted errors, code, commands, and tool output unchanged. Drop full for security warnings, irreversible confirmations, ambiguous multi-step instructions, user confusion, blockers requiring careful explanation, or when the user asks for normal or long-form wording.

**Handoff boundary:** Caveman full applies to chat/status prose, not requirements documents, plans, `ROSEY_LFG_QUALITY_HANDOFF` blocks, file lists, verification output, or assumptions recorded for downstream agents.

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default for direct chat invocation. Child skills may ask blocking questions and wait for user answers.
- `mode:non-interactive` — scripted or skill-to-skill execution. Child skills must not ask blocking questions or wait for confirmations.

Strip the interaction mode token before treating the remainder as the feature description. If no interaction mode token is present, set `INTERACTION_MODE=interactive`.

If multiple interaction mode tokens appear, stop and report the conflict.

### Non-Interactive Mode Rules

When `INTERACTION_MODE=non-interactive`:

- Do not ask optional clarification questions or use blocking question tools.
- Make conservative assumptions from the task, issue context, repo conventions, and generated artifacts.
- Record material assumptions in requirements or plan artifacts.
- Prefer markdown and stable machine-readable outputs.
- If safe progress requires human judgment, stop with a concise blocker instead of prompting.

## Stage Boundary

`rosey-lfg-code` owns:

- Requirements via `rosey-brainstorm`
- Plan via `rosey-plan`
- Implementation, lint/build, and Sentrux handoff via `rosey-work`

`rosey-lfg-quality` owns QA, PR creation/update, residual durability, and `<promise>DONE</promise>`. It does not watch or fix CI; Bugbot and existing automation handle CI failures after PR creation.

Do not invoke `rosey-qa` or `rosey-pr` from this skill. `rosey-work` must also stop before QA and PR.

## Skill Resolution

When invoking a skill below, resolve its name against the available skills list and use the exact listed entry. Some hosts may namespace project skills. Do not guess an invocation name that is not available.

## Input Gate

Require a concrete software feature description in `$ARGUMENTS`. If the input is empty, non-software, or too vague for execution:

- In interactive mode, ask the user to re-invoke or clarify `rosey-lfg-code` with a specific software task.
- In non-interactive mode, stop with a blocker and do not ask for clarification.

In non-interactive mode, do not ask optional clarification questions during the pipeline. If a child skill reaches a hard blocker that requires user input, stop and report the blocker rather than improvising scope.

## Pipeline

### 1. Requirements

Invoke `rosey-brainstorm` with the original feature description. In non-interactive mode, include `mode:non-interactive`.

Non-interactive mode must produce markdown requirements. If output format is configurable, force or rely on non-interactive markdown behavior.

Gate before continuing:

- Verify a requirements document was created under `rosey/brainstorms/`.
- Record `REQUIREMENTS_PATH`.
- If no requirements document was created, invoke `rosey-brainstorm` once more with the original feature description.
- If it still does not create a requirements document, stop and report the failure.
- If the request is classified as too vague or not suitable for software pipeline execution, stop before planning.

### 2. Plan

Invoke `rosey-plan` with `REQUIREMENTS_PATH`. In non-interactive mode, include `mode:non-interactive`.

Gate before continuing:

- Verify a plan document was created under `rosey/plans/`.
- Record `PLAN_PATH`.
- If no plan was created, invoke `rosey-plan` once more with `REQUIREMENTS_PATH`.
- If it still does not create a plan, stop and report the failure.
- Record any Sentrux topology artifact referenced by or stored beside the plan.

### 3. Work

Invoke `rosey-work` with `PLAN_PATH`. In non-interactive mode, include `mode:non-interactive`.

Gate before continuing:

- Verify implementation work occurred beyond requirements and plan artifacts.
- Capture the handoff context from `rosey-work`:
  - `FILES_CHANGED`
  - `WHAT_WAS_IMPLEMENTED`
  - `PLAN_OR_REQUIREMENTS`
  - `SENTRUX_REVIEW_CONTEXT`
  - `DONE`, `VERIFY`, `BLOCKERS`, `SENTRUX`, and `HINDSIGHT` when present
- If no implementation files changed and no existing implementation was verified as already satisfying the plan, stop.
- If `rosey-work` stops on lint/build failure or a Sentrux handoff block, stop and report the blocker. Continue only if the relevant child skill documents an explicit user override.

## Handoff Output

When code-stage work is complete, output a handoff block for `rosey-lfg-quality`:

```text
ROSEY_LFG_QUALITY_HANDOFF
REQUIREMENTS_PATH: <path>
PLAN_PATH: <path>
FILES_CHANGED:
- <repo-relative path>
DONE:
- <U-ID or task>: <completed change, <=12 words>
WHAT_WAS_IMPLEMENTED:
<concise implementation summary>
PLAN_OR_REQUIREMENTS:
<plan path plus origin requirements path when present>
VERIFY:
- <command or gate>: <pass | failed | skipped with reason>
BLOCKERS: <none | one-line blocker>
HINDSIGHT: <available | unavailable | skipped> -- <brief reason>
SENTRUX: <pass | failed | unavailable | override> -- <brief reason>
SENTRUX_REVIEW_CONTEXT:
<markdown sentrux summary or unavailable reason>
CHILD_MODES:
- rosey-brainstorm: non-interactive
- rosey-plan: non-interactive
- rosey-work: non-interactive
END_ROSEY_LFG_QUALITY_HANDOFF
```

When `INTERACTION_MODE=non-interactive`, every child skill invocation must include
`mode:non-interactive` in the prompt. Record the three child receipts in
`CHILD_MODES` as shown above.

Do not emit `<promise>DONE</promise>`. The full autonomous pipeline is complete only after `rosey-lfg-quality` finishes QA and PR handling.
