---
name: rosey-work
description: Execute work efficiently while maintaining quality and finishing features
argument-hint: "[Plan doc path or description of work. Blank to auto use latest plan doc]"
---

# Rosey Work

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

This skill follows the Rosey-native work workflow with Rosey Sentrux and handoff boundaries:

- For app repos, implement on a git-flow `feature/<slug>` branch. **Default:** new plan → new branch from `develop`. Continue on the current branch only when the plan slug matches, the plan explicitly extends that branch, or the user confirms carryover in interactive mode.
- `rosey-work` does **not** own QA, PR creation, merge, or release. Those belong downstream to `rosey-qa`, `rosey-pr`, `rosey-lfg-quality`, auto-merge workflows, and `rosey-release`.
- Read [`rosey-sentrux`](../rosey-sentrux/SKILL.md) when a plan has a topology artifact or when executing a `rosey-plan` plan.
- Read [`rosey-hindsight`](../rosey-hindsight/SKILL.md) before substantive implementation so cross-session memory can inform the work.
- Recall relevant Hindsight context before the first implementation task; retain durable discoveries during work and a session summary at handoff.
- If Hindsight is unavailable or not configured, continue implementation and record `HINDSIGHT: unavailable` in the handoff envelope.
- Track a deduped `FILES_CHANGED` list of every file created or modified during execution. Use repo-relative paths.
- Before executing each task, run a path pre-pass against the task's declared file paths and block if a required path is outside the current project context or is missing unexpectedly.
- Do not execute prose-documentation, optional, report, summary, or retrospective tasks. Deployment manifests, config maps, secrets/config patches, and other platform/GitOps artifacts are implementation work and must not be filtered as documentation.
- Do not invent test infrastructure. Author or run automated tests only when a configured test runner already exists for the touched repo, or when the user explicitly asks for test setup.
- After implementation completes, invoke [`rosey-lint`](../rosey-lint/SKILL.md), prepare the Sentrux review brief, and stop with handoff context. Do not invoke `rosey-qa` or `rosey-pr`.

## Input Document

<input_document> #$ARGUMENTS </input_document>

## Execution Workflow

### Phase 0.0: Hindsight gate (hard)

1. Read [`rosey-hindsight`](../rosey-hindsight/SKILL.md)
2. Run `uvx hindsight-embed@0.8.2 daemon status`
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

   - Read the work document completely. Plans may be markdown (`.md`) or HTML (`.html`) — both formats are read as text linearly. HTML plans carry the same section names and IDs as markdown plans, just wrapped in semantic HTML elements (`<section>`, `<article>`, etc.); section-finding works the same way (substring match on section names, ignoring HTML wrapper noise).
   - When auto-detecting the latest plan (blank invocation), glob `rosey/plans/*.md` AND `rosey/plans/*.html` and pick the most recent regardless of extension.
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

   App repos use `develop` as the fixed integration branch.
   **Hard gate:** complete branch setup and record `BRANCH` / `BRANCH_DECISION` in the handoff envelope before the first file edit. Do not skip because the current branch "looks fine."

   First, check the current branch and verify `origin/develop` exists:

   ```bash
   current_branch=$(git branch --show-current)
   git rev-parse --verify origin/develop >/dev/null
   ```

   **Derive the plan slug** (same rule as [`rosey-pr`](../rosey-pr/SKILL.md) branch naming):

   - From plan path basename without extension: strip leading date/id tokens (e.g. `2026-06-22-seo-phase-2-content-plan` → `seo-phase-2-content`); kebab-case; max ~50 characters.
   - From bare prompt: kebab-case summary of the work.
   - Expected branch: `feature/<slug>`.

   **Plan ↔ branch alignment** (run whenever a plan path or bare-prompt slug exists):

   | Signal                                                                                             | Action                                                                                                        |
   | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
   | `current_branch` is `feature/<slug>` and slug matches plan slug                                    | Continue (record `BRANCH_DECISION: continued`)                                                                |
   | Plan explicitly says it extends or continues `<branch>`                                            | Continue on that branch                                                                                       |
   | Slug mismatch (e.g. plan `seo-phase-2-content`, branch `feature/seo-phase-1`)                      | **Recommend new branch from `develop`** — a meaningful but wrong-phase name is still a mismatch               |
   | Branch name opaque or auto-generated (e.g. `worktree-jolly-beaming-raven`)                         | Rename or create new `feature/<slug>`                                                                         |
   | Open PR on current branch (GitHub MCP `search_pull_requests` when available) **and** slug mismatch | Require new branch or explicit "add to existing PR" confirmation — do not silently stack unrelated plan scope |

   **If already on a feature branch** (not `develop`):

   Apply the alignment table above first. When slug mismatches or an open PR stacks unrelated scope, ask (interactive):

   > "Plan expects `feature/<plan-slug>` but current branch is `[current_branch]`. Create a new branch from `develop`, or continue on the current branch?"
   - **New branch** → follow **Create feature branch from `develop`** below. Preserve uncommitted work via stash when needed.
   - **Continue** → only after explicit confirmation when slug mismatched or open PR stacks scope. Record `BRANCH_DECISION: continued` and a one-line `BRANCH_NOTE` explaining why.
   - **Rename only** (opaque name, slug otherwise matches intent):

     ```bash
     git branch -m feature/<slug>
     ```

   In non-interactive mode: create `feature/<plan-slug>` from `develop` when slug mismatches and movement is safe; stop if uncommitted work or unpushed commits would be lost. Never silently continue on a mismatched branch.

   **If on `develop`**, choose how to proceed:

   **Option A: Create feature branch from `develop`** (default for new plan work)

   Read [`../rosey-pr/references/branch-creation.md`](../rosey-pr/references/branch-creation.md) when local `develop` may be stale or has unpushed commits. Then:

   ```bash
   git fetch --no-tags origin develop
   git pull origin develop
   git config --get gitflow.branch.master >/dev/null 2>&1 || git flow init -d
   git flow feature start <slug>
   ```

   Record `BRANCH_DECISION: new-from-develop`.

   **Leaving an existing feature branch to create new** (slug mismatch, user chose new branch):

   ```bash
   git stash push -u -m "rosey-work: pre-branch feature/<slug>"   # when uncommitted changes exist
   git fetch --no-tags origin develop
   git checkout origin/develop   # or follow branch-creation.md when local develop has unpushed commits
   git flow feature start <slug>
   git stash pop                 # when stashed; stop on conflicts — do not auto-resolve
   ```

   **Option B: Use a worktree (recommended for parallel development)**
   Use the platform's worktree support or an available worktree helper. The worktree must create a new `feature/<slug>` branch from `develop` in an isolated checkout. Keep worktree isolation for parallel implementation; shared-directory parallel writes are unsafe.

   **Option C: Continue on `develop`**
   - Requires explicit user confirmation
   - Only proceed after user explicitly says "yes, commit to develop"
   - Never commit directly to `develop` without explicit permission
   - In non-interactive mode, never continue on `develop`; create a new feature branch.

   Use a meaningful slug based on the plan or work (e.g. `user-authentication`). `git flow feature start <slug>` creates and checks out `feature/<slug>`. Keep branch names on `feature/<slug>` for `pr-auto-merge.yml` head filter compatibility.

   **Recommendation**: Use worktree if:
   - You want to work on multiple features simultaneously
   - You want to keep `develop` clean while experimenting
   - You plan to switch between branches frequently

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
   - Run `uvx hindsight-embed@0.8.2 memory recall <bank> "<task summary>"` with the plan path or bare prompt, affected modules, important risks, and U/R/A/F/AE IDs when present.
   - Fold useful recalled context into the execution approach. Do not paste raw recall output into chat unless the user asks.
   - If Hindsight is unavailable, continue and record the unavailable status for handoff.

4. **Choose Execution Strategy**

   After creating the task list, decide how to execute based on the plan's size and dependency structure:

   | Strategy               | When to use                                                                                                                                                                                                                  |
   | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
   | **Inline**             | 1-2 small tasks, or tasks needing user interaction mid-flight. **Default for bare-prompt work** — bare prompts rarely produce enough structured context to justify subagent dispatch                                         |
   | **Serial subagents**   | 3+ tasks with dependencies between them. Each subagent gets a fresh context window focused on one unit — prevents context degradation across many tasks. Requires plan-unit metadata (Goal, Files, Approach, Test scenarios) |
   | **Parallel subagents** | 3+ tasks that pass the Parallel Safety Check (below). Dispatch independent units simultaneously, run dependent units after their prerequisites complete. Requires plan-unit metadata                                         |

   **Parallel Safety Check** — required before choosing parallel dispatch:

   1. Build a file-to-unit mapping from every candidate unit's `Files:` section (Create, Modify, and Test paths)
   2. Check for intersection — any file path appearing in 2+ units means overlap
   3. **If overlap is found AND worktree isolation is unavailable**: downgrade to serial subagents. Log the reason (e.g., "Units 2 and 4 share `config/routes.rb` — using serial dispatch"). Serial subagents still provide context-window isolation without shared-directory write races.
   4. **If overlap is found AND worktree isolation is available**: parallel dispatch is still safe — subagents work in isolation, and the overlap surfaces as a predictable merge conflict the orchestrator handles via the post-batch flow below. Log the predicted overlap so the post-batch flow knows which merges to expect conflicts on.

   Even with no file overlap, parallel subagents sharing the orchestrator's working directory face git index contention (concurrent staging/committing corrupts the index) and test interference (concurrent test runs pick up each other's in-progress changes). Worktree isolation eliminates both; the shared-directory fallback constraints below mitigate them.

   **Subagent isolation** — give each parallel subagent its own working tree:
   - **Claude Code (`Agent` tool):** pass `isolation: "worktree"` and `run_in_background: true`. The harness creates a per-subagent worktree under `.claude/worktrees/agent-<id>` on its own branch. Verify `.claude/worktrees/` is gitignored before relying on this.
   - **Other platforms** without built-in worktree isolation (e.g., Codex `spawn_agent`, Pi `subagent`): subagents share the orchestrator's directory.

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

   **Shared-directory fallback constraints** — apply only when worktree isolation is unavailable:
   - Instruct each subagent: "Do not stage files (`git add`), create commits, or run the project test suite. The orchestrator handles testing, staging, and committing after all parallel units complete."
   - These constraints prevent git index contention and test interference between concurrent subagents.
   - With worktree isolation active, omit these constraints — subagents may stage, commit, and run their unit's tests within their own worktree branch.

   **Permission mode:** Omit the `mode` parameter when dispatching subagents so the user's configured permission settings apply. Do not pass `mode: "auto"` — it overrides user-level settings like `bypassPermissions`.

   **After each subagent completes (serial mode):**
   1. Read the subagent receipt, then review the diff — verify changes match the unit's scope and `Files:` list
   2. Run the relevant test suite to confirm the tree is healthy
   3. If tests fail, diagnose and fix before proceeding — do not dispatch dependent units on a broken tree
   4. Update the task list (do not edit the plan body — progress is carried by the commit)
   5. Dispatch the next unit

   **After all parallel subagents in a batch complete (worktree-isolated mode):**
   1. Wait for every subagent in the current parallel batch to finish.
   2. For each completed subagent, in dependency order: read the receipt and review the worktree's diff against the orchestrator's branch. If the subagent did not commit its own work, stage and commit it inside that worktree.
   3. Merge each subagent's branch into the orchestrator's branch sequentially in dependency order. **If a merge conflict surfaces, abort the merge (`git merge --abort`) and re-dispatch the conflicting unit serially against the now-merged tree** — hand-resolving silently picks a side and discards one unit's intent. (Predicted overlap from the Parallel Safety Check surfaces here as a conflict, not as silent data loss in shared-directory mode.)
   4. After each merge, run the relevant test suite. If tests fail, diagnose and fix before merging the next branch.
   5. Update the task list (progress is carried by the merge commits).
   6. After merging, remove each subagent's worktree and delete its branch. Use the absolute path and branch name returned in the subagent's result.
      - Unlock the worktree first — the harness locks per-subagent worktrees: `git worktree unlock <absolute-path>`
      - Remove the worktree: `git worktree remove <absolute-path>`
      - Delete the branch: `git branch -d <branch-name>` (the branch outlives the worktree by default and accumulates as orphans if not cleaned up; `-d` lowercase refuses to delete unmerged branches, which is the safety we want — if it fails, investigate before forcing)
   7. Dispatch the next batch of independent units, or the next dependent unit.

   **After all parallel subagents in a batch complete (shared-directory fallback):**
   1. Wait for every subagent in the current parallel batch to finish before acting on any of their results
   2. Cross-check receipts and discovered file collisions: compare the actual files modified by all subagents in the batch (not just their declared `Files:` lists). Subagents may create or modify files not anticipated during planning — this is expected, since plans describe _what_ not _how_. A collision only matters when 2+ subagents in the same batch modified the same file. In a shared working directory, only the last writer's version survives — the other unit's changes to that file are lost. If a collision is detected: commit all non-colliding files from all units first, then re-run the affected units serially for the shared file so each builds on the other's committed work
   3. For each completed unit, in dependency order: review the diff, run the relevant test suite, stage only that unit's files, and commit with a conventional message derived from the unit's Goal
   4. If tests fail after committing a unit's changes, diagnose and fix before committing the next unit
   5. Update the task list (do not edit the plan body — progress is carried by the commits just made)
   6. Dispatch the next batch of independent units, or the next dependent unit

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

   When a task reveals durable context, retain it immediately with `uvx hindsight-embed@0.8.2 memory retain` using the guidance in [`rosey-hindsight`](../rosey-hindsight/SKILL.md). Good candidates include user preferences, project conventions, failed-command fixes, environment requirements, architecture decisions, and workarounds. Do not store secrets or sensitive data.

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
   # Examples: bin/rails test, npm test, pytest, go test, etc.

   # 2. Stage only files related to this logical unit (not `git add .`)
   git add <files related to this logical unit>

   # 3. Commit with conventional message
   git commit -m "feat(scope): description of this unit"
   ```

   **Handling merge conflicts:** If conflicts arise during rebasing or merging, resolve them immediately. Incremental commits make conflict resolution easier since each commit is small and focused.

   **Note:** Incremental commits use clean conventional messages without attribution footers. The final Phase 4 commit/PR includes the full attribution.

   **Parallel subagent mode:** Commit ownership is split by isolation mode (see Phase 1 Step 4):
   - **Worktree-isolated:** subagents may stage and commit inside their own worktree branch; the orchestrator merges those branches in dependency order after the batch.
   - **Shared-directory fallback:** subagents do not commit; the orchestrator stages and commits each unit after the entire parallel batch completes.

3. **Follow Existing Patterns**

   - The plan should reference similar code - read those files first
   - Match naming conventions exactly
   - Reuse existing components where possible
   - Follow project coding standards (see AGENTS.md; use CLAUDE.md only if the repo still keeps a compatibility shim)
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
   - Run its discovery and execution pipeline for format, lint, type-check, and build commands available in the current repository. In non-interactive mode, invoke it with `mode:non-interactive`.
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
   - Emit a compact, stable envelope. Keep the legacy field names below so `rosey-lfg-code` and `rosey-lfg-quality` can consume the handoff without parsing prose:

     ```text
     ROSEY_WORK_HANDOFF
     BRANCH: <feature/slug>
     BRANCH_DECISION: <new-from-develop | continued | renamed>
     BRANCH_NOTE: <none | one-line reason when continued on mismatched or open-PR branch>
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

6. **Stop**. Do not invoke `rosey-qa`, `rosey-pr`, or any shipping workflow. Shipping/QA adaptation is handled by a separate plan.

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
- Prepare complete handoff context so `rosey-qa` and `rosey-lfg-quality` can review the change

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
- **Skipping handoff context** - `rosey-qa` and `rosey-lfg-quality` need the plan, changed files, implementation summary, and Sentrux context
- **Branch carryover** - A meaningful branch name for a prior plan (e.g. `feature/seo-phase-1`) is not permission to implement a new plan on it. Match plan slug or get explicit carryover confirmation before editing
- **Re-scoping the plan into human-time phases** - The plan's Implementation Units define the scope of execution. Do not estimate human-hours per unit, propose multi-day breakdowns, or ask the user to pick a subset of units for "this session". Agents execute at agent speed, and context-window pressure is addressed by subagent dispatch (Phase 1 Step 4), not by phased sessions. If a plan-file input is genuinely too large for a single execution, say so plainly and suggest the user return to `/rosey-plan` to reduce scope — don't invent session phases as a workaround. For bare-prompt input, Phase 0's Large routing already handles oversized work
