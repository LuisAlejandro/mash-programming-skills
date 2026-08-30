---
name: rosey-work
description: Execute work efficiently while maintaining quality and finishing features
argument-hint: "[Plan doc path or description of work. Blank to auto use latest plan doc]"
---

# Rosey Work (live-home)

Read `references/livehome.md` first. This is a full live-home skill: stay on `master`/`main`, no PRs, no stashes, mixed dirty files expected.

Execute implementation work efficiently while maintaining quality.

## Communication while using this skill

**Caveman lite** for all assistant prose while this skill runs: strip filler and hedging; keep articles and full sentences; stay professional and tight. Technical accuracy unchanged; quoted errors and code unchanged. Drop lite only for security warnings, irreversible confirmations, ambiguous multi-step instructions, user confusion, or when the user asks for normal or long-form wording.

## Introduction

This command executes a plan, specification, or bare prompt. It completes implementation by reading requirements quickly, following existing patterns, and maintaining quality.

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default for direct chat invocation. The skill may ask blocking questions.
- `mode:non-interactive` — scripted or skill-to-skill execution. The skill must not ask blocking questions or wait for confirmations.

Strip the interaction mode token before treating the remainder as the input document. If no interaction mode token is present, set `INTERACTION_MODE=interactive`.

If multiple interaction mode tokens appear, stop and report the conflict.

In non-interactive mode, resolve implementation-time unknowns conservatively from the plan and codebase, record assumptions in the handoff, and stop with a concise blocker when safe progress requires human judgment.

## Rosey Overlay

This skill follows the Rosey-native work workflow with Rosey Sentrux and handoff boundaries, adapted for a live-home:

- Stay on `master` (or `main`). Never create `feature/*` branches, never use git-flow, never stash, never open a worktree. Record `BRANCH: master|main` and `BRANCH_DECISION: live-home-master` before the first file edit.
- Mixed dirty files are normal. Touch and commit **only** `FILES_CHANGED` from this session. Never `git add .`. Never restore or checkout files this session did not change.
- Optional `git fetch`. `git pull` only when it would not need a stash; otherwise skip pull and note it.
- `rosey-work` does **not** own QA, merge, or release. Downstream is `rosey-qa` only. Never invoke `rosey-pr`. Never mention PRs.
- Host tooling is allowed. Docker-via-Make does not apply.
- Read [`rosey-sentrux`](../rosey-sentrux/SKILL.md) when a plan has a topology artifact or when executing a `rosey-plan` plan.
- Read [`rosey-hindsight`](../rosey-hindsight/SKILL.md) before substantive implementation so cross-session memory can inform the work.
- Recall relevant Hindsight context before the first implementation task; retain durable discoveries during work and a session summary at handoff.
- If Hindsight is unavailable or not configured, continue implementation and record `HINDSIGHT: unavailable` in the handoff envelope.
- Track a deduped `FILES_CHANGED` list of every file created or modified during execution. Use repo-relative paths.
- Before executing each task, run a path pre-pass against the task's declared file paths and block if a required path is outside the current project context or is missing unexpectedly.
- Do not execute prose-documentation, optional, report, summary, or retrospective tasks. Deployment manifests, config maps, secrets/config patches, and other platform/GitOps artifacts are implementation work and must not be filtered as documentation.
- Do not invent test infrastructure. Author or run automated tests only when a configured test runner already exists for the touched repo, or when the user explicitly asks for test setup.
- After implementation completes, invoke [`rosey-lint`](../rosey-lint/SKILL.md) on session files, prepare the Sentrux review brief, and stop with handoff context. Do not invoke `rosey-qa` or `rosey-pr`.

## Input Document

<input_document> #$ARGUMENTS </input_document>

## Execution Workflow

### Phase 0.0: Hindsight gate (hard)

1. Read [`rosey-hindsight`](../rosey-hindsight/SKILL.md)
2. Run `hindsight-embed daemon status` (prepend `~/.local/bin` to PATH; see [`rosey-hindsight`](../rosey-hindsight/SKILL.md))
3. Run `memory recall` OR emit `Hindsight: unavailable — <reason>` before any file edits
4. At handoff: `memory retain` session summary OR document why retain was skipped

Do not proceed to Phase 0 triage or Phase 1 until step 3 completes.

### Phase 0: Input Triage

Determine how to proceed based on what was provided in `<input_document>`.

**Plan document** (input is a file path to an existing plan or specification) → skip to Phase 1 after Phase 0.0 gate completes.

**Bare prompt** (input is a description of work, not a file path):

1. **Scan the work area**

   - Identify files likely to change based on the prompt
   - Find existing test files for those areas (search for test/spec files that import, reference, or share names with the implementation files)
   - Note local patterns and conventions in the affected areas

2. **Assess complexity and route**

   | Complexity         | Signals                                                                             | Action                                                                                                                                                                        |
   | ------------------ | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
   | **Trivial**        | 1-2 files, no behavioral change (typo, config, rename)                              | Proceed to Phase 1 step 2 (environment setup), then implement directly — no task list, no execution loop. Apply Test Discovery if the change touches behavior-bearing code    |
   | **Small / Medium** | Clear scope, under ~10 files                                                        | Build a task list from discovery. Proceed to Phase 1 step 2                                                                                                                   |
   | **Large**          | Cross-cutting, architectural decisions, 10+ files, touches auth/payments/migrations | Recommend `/rosey-brainstorm` or `/rosey-plan` to surface edge cases and boundaries. Honor the user's choice. If proceeding, build a task list and continue to Phase 1 step 2 |

   In non-interactive mode, do not offer routing choices for Large bare prompts. Stop and require a plan path instead.

---

### Phase 1: Quick Start

1. **Read Plan and Clarify** _(skip if arriving from Phase 0 with a bare prompt)_

   - Read the work document completely. Plans are markdown (`.md`).
   - When auto-detecting the latest plan (blank invocation), glob `rosey/plans/*.md` and pick the most recent.
   - Treat the plan as a decision artifact, not an execution script
   - If the plan includes sections such as `Implementation Units`, `Work Breakdown`, `Requirements` (or legacy `Requirements Trace`), `Files`, `Test Scenarios`, or `Verification`, use those as the primary source material for execution
   - Check for `Execution note` on each implementation unit — these carry the plan's execution posture signal for that unit (for example, test-first or characterization-first). Note them when creating tasks.
   - Check for a `Deferred to Implementation` or `Implementation-Time Unknowns` section — these are questions the planner intentionally left for you to resolve during execution. Note them before starting so they inform your approach rather than surprising you mid-task
   - Check for a `Scope Boundaries` section — these are explicit non-goals. Refer back to them if implementation starts pulling you toward adjacent work
   - Review any references or links provided in the plan
   - If the plan references a Sentrux topology artifact, read it before creating tasks. If no explicit path exists, look beside the plan for `<plan-basename>.topology.json`.
   - If the user explicitly asks for TDD, test-first, or characterization-first execution in this session, honor that request even if the plan has no `Execution note`
   - If anything is unclear or ambiguous, ask clarifying questions now in interactive mode. In non-interactive mode, resolve from plan context or stop with a blocker.
   - If clarifying questions were needed above, get user approval on the resolved answers in interactive mode. If no clarifications were needed, proceed without a separate approval step — plan scope is the plan's authority, not something to renegotiate. In non-interactive mode, no approval step is allowed.
   - **Do not skip this** - better to ask questions now than build the wrong thing
   - **Do not edit the plan body during execution.** The plan is a decision artifact; progress lives in git commits and the task tracker. Legacy plans may contain `- [ ]` / `- [x]` marks on unit headings — ignore them as state; per-unit completion is determined during execution by reading the current file state.

2. **Setup Environment**

   **Hard gate:** stay on `master` or `main` and record `BRANCH` / `BRANCH_DECISION: live-home-master` before the first file edit. Do not create branches, stashes, or worktrees because the tree "looks dirty."

   ```bash
   current_branch=$(git branch --show-current)
   ```

   - If `current_branch` is `master` or `main`, continue. Record `BRANCH: $current_branch` and `BRANCH_DECISION: live-home-master`.
   - If it is anything else, **do not** create `feature/*` or run git-flow. In interactive mode, ask whether to checkout `master`/`main` **without** stashing. If checkout would lose or mix unrelated work, stay put, record `BRANCH_NOTE`, and still do not stash. In non-interactive mode, stay on the current branch, record the note, and implement in place.
   - Optional: `git fetch --no-tags`. `git pull` only when it would not require a stash to survive unrelated dirty files. If pull would need a stash, skip it and note `BRANCH_NOTE: skipped-pull-dirty-tree`.
   - Never `git stash`, never `git flow`, never `git worktree add`, never `git checkout -b`.

   Dirty mixed files are expected. A non-empty `git status` is not a blocker.

3. **Create Task List** _(skip if Phase 0 already built one, or if Phase 0 routed as Trivial)_
   - Use the platform's task tracking tool (`TaskCreate`/`TaskUpdate`/`TaskList` in Claude Code, `update_plan` in Codex, or the equivalent on other harnesses) to break the plan into actionable tasks
   - Derive tasks from the plan's implementation units, dependencies, files, test targets, and verification criteria
   - When the plan defines U-IDs for Implementation Units, preserve the unit's U-ID as a prefix in the task subject (e.g., "U3: Add parser coverage"). This keeps blocker references, deferred-work notes, and final summaries anchored to the same identifier the plan uses, so progress and traceability remain unambiguous across plan edits
   - Carry each unit's `Execution note` into the task when present
   - For each unit, read the `Patterns to follow` field before implementing — these point to specific files or conventions to mirror
   - Use each unit's `Verification` field as the primary "done" signal for that task
   - Do not expect the plan to contain implementation code, micro-step TDD instructions, or exact shell commands
   - Include dependencies between tasks
   - Prioritize based on what needs to be done first
   - Include testing and quality check tasks
   - Keep tasks specific and completable

   **Task filters and path pre-pass:**
   - Exclude prose documentation, optional items, and report/summary/retrospective tasks.
   - Keep implementation, tests allowed by the test-runner prerequisite, and platform/GitOps/config tasks.
   - Before starting each task, scan declared paths and verify they belong to the current project context. If a task requires edits in a path that does not exist and is not intended to be created, stop and report the block.
   - Maintain `FILES_CHANGED` as a deduped list across the whole run. Append every repo-relative file path created or modified after each completed task.

   **Sentrux session setup:**
   - If a topology artifact exists and Sentrux is available, read [`rosey-sentrux`](../rosey-sentrux/SKILL.md), then start an MCP `session_start` before the first implementation task.
   - Before large edits, consult MCP `git_stats` and `dsm` so hotspots, dependency direction, and topology bottlenecks influence execution.
   - If Sentrux is unavailable, continue implementation and record the reason for the final review brief.

   **Hindsight recall:**
   - Read [`rosey-hindsight`](../rosey-hindsight/SKILL.md) before the first implementation task.
   - Resolve the Hindsight bank ID using the skill's bank resolution rule.
   - Run `hindsight-embed memory recall <bank> "<task summary>"` with the plan path or bare prompt, affected modules, important risks, and U/R/A/F/AE IDs when present (see [`rosey-hindsight`](../rosey-hindsight/SKILL.md)).
   - Fold useful recalled context into the execution approach. Do not paste raw recall output into chat unless the user asks.
   - If Hindsight is unavailable, continue and record the unavailable status for handoff.

4. **Choose Execution Strategy**

   After creating the task list, decide how to execute based on the plan's size and dependency structure:

   | Strategy               | When to use                                                                                                                                                                                                                  |
   | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
   | **Inline**           | 1-2 small tasks, or tasks needing user interaction mid-flight. **Default for bare-prompt work** — bare prompts rarely produce enough structured context to justify subagent dispatch                                         |
   | **Serial subagents** | 3+ tasks. Each subagent gets a fresh context window focused on one unit. Requires plan-unit metadata (Goal, Files, Approach, Test scenarios). **This is the only subagent mode on a live-home.**                            |

   Never dispatch parallel subagents. Never pass `isolation: "worktree"`. Worktrees hide the live files this home is for. Parallel writers in the same git index are unsafe. Downgrade any plan that asks for parallel dispatch to serial inline or serial subagents, and log `execution: serial-livehome`.

   **Subagent dispatch** uses your available subagent or task spawning mechanism. For each unit, give the subagent:
   - The full plan file path (for overall context)
   - The specific unit's Goal, Files, Approach, Execution note, Patterns, Test scenarios, and Verification
   - Any resolved deferred questions relevant to that unit
   - Instruction to check whether the unit's test scenarios cover all applicable categories (happy paths, edge cases, error paths, integration) and supplement gaps before writing tests

   **Compact subagent receipt contract** — every implementation subagent must return this terse receipt and avoid narrative unless blocked:

   ```text
   UNIT: <U-ID or task name>
   FILES:
   - <repo-relative path>
   CHANGED:
   - <change, <=12 words>
   VERIFY:
   - <command or check>: <pass | failed | skipped with reason>
   BLOCKER: <none | one-line blocker>
   ```

   If the subagent produced risky behavior, failed verification, or changed files outside the declared `Files:` list, it may add `DETAIL:` with only the evidence needed for orchestrator review. Full exploration stories stay out of the parent context.

   **Serial subagent constraints** (always — this home has no worktree isolation):
   - Instruct each subagent: "Do not stage files (`git add`) or create commits. The orchestrator stages only `FILES_CHANGED` after the unit is reviewed. Do not `git add .` and do not touch unrelated dirty files."
   - One subagent at a time. Do not run concurrent writers against this checkout.

   **Permission mode:** Omit the `mode` parameter when dispatching subagents so the user's configured permission settings apply. Do not pass `mode: "auto"` — it overrides user-level settings like `bypassPermissions`.

   **After each subagent completes (serial mode):**
   1. Read the subagent receipt, then review the diff — verify changes match the unit's scope and `Files:` list
   2. Run the relevant test suite to confirm the tree is healthy
   3. If tests fail, diagnose and fix before proceeding — do not dispatch dependent units on a broken tree
   4. Update the task list (do not edit the plan body — progress is carried by the commit)
   5. Dispatch the next unit

### Phase 2: Execute

1. **Task Execution Loop**

   For each task in priority order:

   ```
   while (tasks remain):
     - Mark task as in-progress
     - Read any referenced files from the plan or discovered during Phase 0
     - **If the unit's work is already present and matches the plan's intent** (files exist with the expected capability, or the unit's `Verification` criteria are already satisfied by the current code), the work has likely shipped on a prior branch or session. Verify it matches, mark the task complete, and move on. Do not silently reimplement.
     - Look for similar patterns in codebase
     - Find existing test files for implementation files being changed (Test Discovery — see below)
     - Implement following existing conventions
     - Add, update, or remove tests to match implementation changes (see Test Discovery below)
     - Run System-Wide Test Check (see below)
     - Run tests after changes
     - Assess testing coverage: did this task change behavior? If yes, were tests written or updated? If no tests were added, is the justification deliberate (e.g., pure config, no behavioral change)?
     - Mark task as completed
     - Evaluate for incremental commit (see below)
   ```

   When a task reveals durable context, retain it immediately with `hindsight-embed memory retain` using the guidance in [`rosey-hindsight`](../rosey-hindsight/SKILL.md). Good candidates include user preferences, project conventions, failed-command fixes, environment requirements, architecture decisions, and workarounds. Do not store secrets or sensitive data.

   When a unit carries an `Execution note`, honor it. For test-first units, write the failing test before implementation for that unit. For characterization-first units, capture existing behavior before changing it. For units without an `Execution note`, proceed pragmatically.

   Guardrails for execution posture:
   - Do not write the test and implementation in the same step when working test-first
   - Do not skip verifying that a new test fails before implementing the fix or feature
   - Do not over-implement beyond the current behavior slice when working test-first
   - Skip test-first discipline for trivial renames, pure configuration, and pure styling work

   **Test Discovery** — Before implementing changes to a file, find its existing test files (search for test/spec files that import, reference, or share naming patterns with the implementation file). When a plan specifies test scenarios or test files, start there, then check for additional test coverage the plan may not have enumerated. Changes to implementation files should be accompanied by corresponding test updates — new tests for new behavior, modified tests for changed behavior, removed or updated tests for deleted behavior.

   **Test runner prerequisite** — Before creating or running automated tests, confirm the touched repo already has a configured test runner (for example `jest`, `vitest`, Playwright/Cypress, `pytest`, `go test`, `cargo test`, `mix test`, or an equivalent project-standard runner). If no runner is configured, do not create test files, do not add ad hoc test scripts, and document the skip reason. If the user explicitly asks to add test infrastructure, treat that as implementation scope and proceed according to the plan.

   **Test Scenario Completeness** — Before writing tests for a feature-bearing unit, check whether the plan's `Test scenarios` cover all categories that apply to this unit. If a category is missing or scenarios are vague (e.g., "validates correctly" without naming inputs and expected outcomes), supplement from the unit's own context before writing tests:

   | Category                | When it applies                                                           | How to derive if missing                                                                                                             |
   | ----------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
   | **Happy path**          | Always for feature-bearing units                                          | Read the unit's Goal and Approach for core input/output pairs                                                                        |
   | **Edge cases**          | When the unit has meaningful boundaries (inputs, state, concurrency)      | Identify boundary values, empty/nil inputs, and concurrent access patterns                                                           |
   | **Error/failure paths** | When the unit has failure modes (validation, external calls, permissions) | Enumerate invalid inputs the unit should reject, permission/auth denials it should enforce, and downstream failures it should handle |
   | **Integration**         | When the unit crosses layers (callbacks, middleware, multi-service)       | Identify the cross-layer chain and write a scenario that exercises it without mocks                                                  |

   **System-Wide Test Check** — Before marking a task done, pause and ask:

   | Question                                                                                                                                                                                       | What to do                                                                                                                                    |
   | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
   | **What fires when this runs?** Callbacks, middleware, observers, event handlers — trace two levels out from your change.                                                                       | Read the actual code (not docs) for callbacks on models you touch, middleware in the request chain, `after_*` hooks.                          |
   | **Do my tests exercise the real chain?** If every dependency is mocked, the test proves your logic works _in isolation_ — it says nothing about the interaction.                               | Write at least one integration test that uses real objects through the full callback/middleware chain. No mocks for the layers that interact. |
   | **Can failure leave orphaned state?** If your code persists state (DB row, cache, file) before calling an external service, what happens when the service fails? Does retry create duplicates? | Trace the failure path with real objects. If state is created before the risky call, test that failure cleans up or that retry is idempotent. |
   | **What other interfaces expose this?** Mixins, DSLs, alternative entry points (Agent vs Chat vs ChatMethods).                                                                                  | Grep for the method/behavior in related classes. If parity is needed, add it now — not as a follow-up.                                        |
   | **Do error strategies align across layers?** Retry middleware + application fallback + framework error handling — do they conflict or create double execution?                                 | List the specific error classes at each layer. Verify your rescue list matches what the lower layer actually raises.                          |

   **When to skip:** Leaf-node changes with no callbacks, no state persistence, no parallel interfaces. If the change is purely additive (new helper method, new view partial), the check takes 10 seconds and the answer is "nothing fires, skip."

   **When this matters most:** Any change that touches models with callbacks, error handling with fallback/retry, or functionality exposed through multiple interfaces.

2. **Incremental Commits**

   After completing each task, evaluate whether to create an incremental commit:

   | Commit when...                                    | Don't commit when...                |
   | ------------------------------------------------- | ----------------------------------- |
   | Logical unit complete (model, service, component) | Small part of a larger unit         |
   | Tests pass + meaningful progress                  | Tests failing                       |
   | About to switch contexts (backend → frontend)     | Purely scaffolding with no behavior |
   | About to attempt risky/uncertain changes          | Would need a "WIP" commit message   |

   **Heuristic:** "Can I write a commit message that describes a complete, valuable change? If yes, commit. If the message would be 'WIP' or 'partial X', wait."

   If the plan has Implementation Units, use them as a starting guide for commit boundaries — but adapt based on what you find during implementation. A unit might need multiple commits if it's larger than expected, or small related units might land together. Use each unit's Goal to inform the commit message.

   **Commit workflow:**

   ```bash
   # 1. Verify tests pass (use project's test command)
   # Examples: npm test, pytest, go test, etc. Host tooling is allowed.

   # 2. Stage only this session's FILES_CHANGED for the unit (never `git add .`)
   git add <session files for this unit>

   # 3. Commit with a short imperative subject (gitchangelog tags only if .gitchangelog.rc exists)
   git commit -m "feat(scope): description of this unit"
   ```

   Never stage unrelated dirty or untracked files. After a user-requested commit, `git push` to origin for backup.

   **Handling merge conflicts:** If a pull later conflicts, stop and report. Do not stash to make pull work.

   Incremental commits use clean conventional messages without attribution footers and without PR language.

   **Serial subagent mode:** subagents do not commit; the orchestrator stages only `FILES_CHANGED` after each unit.

3. **Follow Existing Patterns**

   - The plan should reference similar code - read those files first
   - Match naming conventions exactly
   - Reuse existing components where possible
   - Follow project coding standards (see AGENTS.md or `.cursorrules`; use CLAUDE.md only if the repo still keeps a compatibility shim)
   - When in doubt, grep for similar implementations

4. **Test Continuously**

   - Run relevant tests after each significant change
   - Don't wait until the end to test
   - Fix failures immediately
   - Add new tests for new behavior, update tests for changed behavior, remove tests for deleted behavior
   - **Unit tests with mocks prove logic in isolation. Integration tests with real objects prove the layers work together.** If your change touches callbacks, middleware, or error handling — you need both.

5. **Simplify as You Go**

   After completing a cluster of related implementation units (or every 2-3 units), review recently changed files for simplification opportunities — consolidate duplicated patterns, extract shared helpers, and improve code reuse and efficiency. This is especially valuable when using subagents, since each agent works with isolated context and can't see patterns emerging across units.

   Don't simplify after every single unit — early patterns may look duplicated but diverge intentionally in later units. Wait for a natural phase boundary or when you notice accumulated complexity.

   If a `/simplify` skill or equivalent is available, use it. Otherwise, review the changed files yourself for reuse and consolidation opportunities.

6. **Figma Design Sync** (if applicable)

   For UI work with Figma designs:

   - Implement components following design specs
   - Use the applicable design sync/review workflow iteratively to compare
   - Fix visual differences identified
   - Repeat until implementation matches design

7. **Track Progress**
   - Keep the task list updated as you complete tasks
   - Note any blockers or unexpected discoveries
   - Create new tasks if scope expands
   - Keep user informed of major milestones
   - When the plan defines U-IDs for Implementation Units, or the plan or origin document carries stable R-IDs (and optionally A/F/AE IDs), reference them in blockers, deferred-work notes, task summaries, and final verification — not routine status updates. U-IDs anchor units across plan edits; R/A/F/AE anchor product intent across the brainstorm-plan handoff. Use the IDs the plan supplies and do not invent ones it does not. This preserves traceability without burying signal under noise.

### Phase 3: Sentrux Review Brief and Stop

When all Phase 2 tasks are complete:

1. **Run `rosey-lint` before handoff**:
   - Load [`rosey-lint`](../rosey-lint/SKILL.md).
   - Run its discovery and execution pipeline for format, lint, type-check, and build commands **on session files only**. In non-interactive mode, invoke it with `mode:non-interactive`. If there are no session files, accept `LINT_STATUS: skipped`.
   - If `rosey-lint` applies fixes, update `FILES_CHANGED` with every file it created or modified.
   - If `rosey-lint` fails and cannot safely fix the issue, stop and report the failing command and relevant output. Do not prepare success handoff context until lint/build verification passes or, in interactive mode only, the user explicitly decides to proceed.
2. **Run the Sentrux handoff gate** when Sentrux is available:
   - Call MCP `session_end`.
   - Call MCP `test_gaps`.
   - Compare the session result against the baseline.
   - If `session_end` fails, attempt focused remediation for structural regressions, then rerun `session_end`.
   - If it still fails, stop and report the block. Continue only in interactive mode if the user gives the exact override phrase from `rosey-sentrux`: `override sentrux handoff block`. In non-interactive mode, do not wait for an override.
3. **Write the review brief** beside the plan as `<plan-basename>.sentrux-review-brief.json`.
   - Include session pass/fail, signal before/after, bottleneck after, `test_gaps`, unavailable reason if applicable, and override details if used.
4. **Retain Hindsight session memory** when Hindsight is available:
   - Use [`rosey-hindsight`](../rosey-hindsight/SKILL.md) to retain a concise but rich summary with plan path, changed files, completed work, verification commands, blockers, and important decisions.
   - If Hindsight is unavailable or not configured, skip retain and record the status in the handoff envelope.
5. **Prepare handoff context**:
   - Emit a compact, stable envelope. Keep the field names below so downstream `rosey-qa` can consume the handoff without parsing prose:

     ```text
     ROSEY_WORK_HANDOFF
     BRANCH: <master|main>
     BRANCH_DECISION: live-home-master
     BRANCH_NOTE: <none | skipped-pull-dirty-tree | one-line>
     FILES_CHANGED:
     - <repo-relative path>
     DONE:
     - <U-ID or task>: <completed change, <=12 words>
     WHAT_WAS_IMPLEMENTED:
     <1-3 terse lines summarizing completed Implementation Units>
     PLAN_OR_REQUIREMENTS: <plan path plus origin requirements path when present>
     VERIFY:
     - <command or gate>: <pass | failed | skipped with reason>
     BLOCKERS: <none | one-line blocker>
     HINDSIGHT: <available | unavailable | skipped> -- <brief reason>
     SENTRUX: <pass | failed | unavailable | override> -- <brief reason>
     SENTRUX_REVIEW_CONTEXT:
     <compact markdown summary from the review brief, or unavailable reason>
     END_ROSEY_WORK_HANDOFF
     ```

   - `BRANCH`, `BRANCH_DECISION`, `FILES_CHANGED`, `WHAT_WAS_IMPLEMENTED`, `PLAN_OR_REQUIREMENTS`, and `SENTRUX_REVIEW_CONTEXT` are required for downstream compatibility.
   - `DONE`, `VERIFY`, `BLOCKERS`, `HINDSIGHT`, and `SENTRUX` are compact machine-to-machine fields. Keep each line short; put full detail in artifacts or blocker reports only when needed.

6. **Stop**. Do not invoke `rosey-qa` or `rosey-pr`. Shipping/QA adaptation is handled separately. Never offer Create PR.

## Key Principles

### Start Fast, Execute Faster

- Get clarification once at the start, then execute
- Don't wait for perfect understanding - ask questions and move
- The goal is to **finish the feature**, not create perfect process

### The Plan is Your Guide

- Work documents should reference similar code and patterns
- Load those references and follow them
- Don't reinvent - match what exists

### Test As You Go

- Run tests after each change, not at the end
- Fix failures immediately
- Continuous testing prevents big surprises

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
- **Creating a feature branch** - Live-homes stay on `master`/`main`. Never git-flow, stash, or worktree to isolate this session
- **Staging the whole tree** - `git add .` would mix unrelated in-progress files into the commit
- **Re-scoping the plan into human-time phases** - The plan's Implementation Units define the scope of execution. Do not estimate human-hours per unit, propose multi-day breakdowns, or ask the user to pick a subset of units for "this session". Agents execute at agent speed, and context-window pressure is addressed by serial subagent dispatch (Phase 1 Step 4), not by phased sessions. If a plan-file input is genuinely too large for a single execution, say so plainly and suggest the user return to `/rosey-plan` to reduce scope — don't invent session phases as a workaround. For bare-prompt input, Phase 0's Large routing already handles oversized work
