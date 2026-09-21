---
name: rosey-work
description: Execute work efficiently while maintaining quality and finishing features
argument-hint: "[Plan doc path. Blank uses latest software plan in rosey/plans/]"
---

# Rosey Work

Execute implementation work efficiently while maintaining quality.

## Communication while using this skill

**Caveman lite** for all assistant prose while this skill runs: strip filler and hedging; keep articles and full sentences; stay professional and tight. Technical accuracy unchanged; quoted errors and code unchanged. Drop lite only for security warnings, irreversible confirmations, ambiguous multi-step instructions, user confusion, or when the user asks for normal or long-form wording.

## Rosey gates

Always-on rules; full procedures live in those guidelines — do not duplicate them here.

1. **Hindsight** before research or implementation — always-on Hindsight guideline; CLI in [`rosey-hindsight`](../rosey-hindsight/SKILL.md)
2. **Ponytail ladder** before adding abstractions or dependencies
3. **Docker-via-Make** for app commands and tooling

See also the always-on Rosey workflow-gates guideline.

## Introduction

This command executes a plan. It completes implementation by reading the plan's decisions, following existing patterns, and maintaining quality. It does not decide what to build — `rosey-brainstorm` settles WHAT and `rosey-plan` settles HOW.

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default for direct chat invocation. The skill may ask blocking questions.
- `mode:non-interactive` — scripted or skill-to-skill execution. The skill must not ask blocking questions or wait for confirmations.

Strip the interaction mode token before treating the remainder as the input document. If no interaction mode token is present, set `INTERACTION_MODE=interactive`.

If multiple interaction mode tokens appear, stop and report the conflict.

In non-interactive mode, resolve implementation-time unknowns conservatively from the plan and codebase, record assumptions in the handoff, and stop with a concise blocker when safe progress requires human judgment.

## Rosey Overlay

This skill follows the Rosey-native work workflow with Rosey Sentrux and handoff boundaries:

- For app repos, implement on a git-flow `feature/<slug>` branch. **Default:** new plan → new branch from `develop`. Continue on the current branch only when the plan slug matches, the plan explicitly extends that branch, or the user confirms carryover in interactive mode.
- `rosey-work` does **not** own QA, PR creation, merge, or release. Those belong downstream to `rosey-qa`, `rosey-pr`, auto-merge workflows, and `rosey-release`.
- If Sentrux MCP is available, run the work session for every plan. If a topology baseline exists, compare against it. If none exists, still use session start/end when available and record that no baseline comparison occurred. If Sentrux is unavailable, do not block. If `session_end` fails, follow the remediation and override procedure in [`rosey-sentrux`](../rosey-sentrux/SKILL.md).
- Read [`rosey-hindsight`](../rosey-hindsight/SKILL.md) before substantive implementation so cross-session memory can inform the work.
- Phase 0.0 is the one required Hindsight recall. Fold that result into Phase 1; do not recall again unless plan resolution was deferred (see `references/work-intake.md`). Retain durable discoveries during work and a session summary at handoff.
- If Hindsight is unavailable or not configured, continue implementation and record `HINDSIGHT: unavailable -- <reason>` in the handoff envelope.
- Track a deduped `FILES_CHANGED` list of every file created or modified during execution. Use repo-relative paths.
- Before executing each task, run a path pre-pass against the task's declared file paths and block if a required path is outside the current project context or is missing unexpectedly.
- Do not execute prose-documentation, optional, report, summary, or retrospective tasks. Deployment manifests, config maps, secrets/config patches, and other platform/GitOps artifacts are implementation work and must not be filtered as documentation.
- Do not invent test infrastructure. Author or run automated tests only when a configured test runner already exists for the touched repo, or when the user explicitly asks for test setup.
- When the origin or plan says OpenDesign visual parity is aligned, implement remaining functionality only. Do not rerun `rosey-implement-design`; use the design iterator only when a visual-parity review identifies a discrepancy.
- After implementation completes, invoke [`rosey-lint`](../rosey-lint/SKILL.md), prepare the Sentrux review brief, and stop with handoff context. Do not invoke `rosey-qa` or `rosey-pr`.

## Input Document

<input_document> #$ARGUMENTS </input_document>

Accepted input is only:

1. A software plan from `rosey-plan`.
2. A plan path from a handoff or session context.
3. Blank input → the latest software plan in `rosey/plans/` (see intake step 0 in `references/work-intake.md`).

A plan path is required. Do not implement from a prose description, a requirements document, or a prompt. After stripping `mode:`, blank input uses the latest software plan.

## Execution Workflow

### Phase 0.0: Hindsight gate (hard)

1. Read [`rosey-hindsight`](../rosey-hindsight/SKILL.md)
2. Run `hindsight-embed daemon status` (prepend `~/.local/bin` to PATH; see [`rosey-hindsight`](../rosey-hindsight/SKILL.md))
3. Run `memory recall` OR emit `Hindsight: unavailable (<reason>)` before any file edits. First status line: `Hindsight: recalled (<brief useful context>)` or `Hindsight: unavailable (<reason>)`.
4. At handoff: `memory retain` session summary OR document why retain was skipped

Do not proceed to Phase 0 triage or Phase 1 until step 3 completes.

## Workflow

Phases run in order. Phase 0.0 above gates everything.

**Read a reference on phase entry, completely.** A read made before that phase does not satisfy it, and a terminal owner is re-read at its step even when already in context.

**A required reference that cannot be read is a stop.** Never reconstruct one from memory. In interactive mode, report which file failed and why, and stop. In `mode:non-interactive`, emit the handoff envelope with the unreadable path named in `BLOCKERS:` instead of stopping silently — an opaque halt is indistinguishable from a hang to an automated caller.

| Phase | Read first | What only those files carry |
|---|---|---|
| 0 — triage; 1 — plan read, branch, tasks, strategy | `references/work-intake.md` | plan resolution and the no-plan stop; how to size the plan read and which contract sections to carry; the branch hard gate, slug derivation, and plan↔branch alignment; the pre-work WIP inventory and the dirty-file collision rule; task derivation and naming; inline vs serial dispatch and the subagent receipt contract |
| 2 — execute | `references/implementation-loop.md` | the task loop and idempotency check; out-of-repo completion signals; evidence strategy and execution-posture guardrails; test discovery, the runner prerequisite, scenario completeness, and the system-wide test check; incremental commits and path-limiting; simplify-as-you-go |
| 3 — handoff | `references/handoff.md` | the `rosey-lint` gate and `LINT_HANDOFF` parsing; the plan's Verification Contract; the Sentrux gate and review brief; Hindsight retain; the Definition of Done final check; the `ROSEY_WORK_HANDOFF` envelope and the `ROSEY_EVIDENCE` artifact |

**STOP after Phase 3.** Do not invoke `rosey-qa`, `rosey-pr`, or any shipping workflow.

## Key Principles

### Start Fast, Execute Faster

- Get clarification once at the start, then execute
- Clarify once at intake when the plan is ambiguous. After the plan is understood, execute without reopening settled decisions.
- The goal is to **finish the feature**, not create perfect process

### The Plan is Your Guide

- Work documents should reference similar code and patterns
- Load those references and follow them
- Don't reinvent - match what exists

### Test As You Go

- Run the Phase 1 resolved command after each change (`make test` / `make lint` when those targets exist), not at the end
- Fix failures immediately
- Continuous testing prevents big surprises. Full `rosey-lint` still runs at Phase 3.

### Quality is Built In

- Follow existing patterns
- Write or update tests when the test-runner prerequisite is satisfied
- Run relevant lint/build checks while implementing
- Prepare complete handoff context so `rosey-qa` can review the change

### Complete Implementation

- Mark all tasks completed before moving on
- Don't leave features 80% done
- A complete implementation with clear handoff context beats partially finished work

## Common Pitfalls to Avoid

- **Analysis paralysis** - Don't overthink, read the plan and execute
- **Skipping clarifying questions** - Ask now, not after building wrong thing
- **Ignoring plan references** - The plan has links for a reason
- **Testing at the end** - Test continuously or suffer later
- **Forgetting to track progress** - Update task status as you go or lose track of what's done
- **80% done syndrome** - Finish the feature, don't move on early
- **Skipping handoff context** - `rosey-qa` needs the plan, changed files, implementation summary, and Sentrux context
- **Branch carryover** - A meaningful branch name for a prior plan (e.g. `feature/seo-phase-1`) is not permission to implement a new plan on it. Match plan slug or get explicit carryover confirmation before editing
- **Implementing without a plan** - A prose description of work is not an input. Resolve a plan from the argument, a blank-input latest software plan, the handoff, or the session, or stop per Phase 0
- **Re-scoping the plan into human-time phases** - The plan's Implementation Units define the scope of execution. Do not estimate human-hours per unit, propose multi-day breakdowns, or ask the user to pick a subset of units for "this session". Agents execute at agent speed, and context-window pressure is addressed by serial subagent dispatch, not by phased sessions. If a plan is genuinely too large for a single execution, say so plainly and suggest the user return to `/rosey-plan` to reduce scope, or hand the epic to `rosey-parallel` — don't invent session phases as a workaround
