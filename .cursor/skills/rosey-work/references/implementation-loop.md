# Implementation Loop

Read this before the first implementation write, including on the Trivial route. It owns the task execution loop, evidence strategy, test discovery and completeness, the system-wide test check, incremental commits, and pattern-following.

## Phase 2: Execute

1. **Task Execution Loop**

   For each task in priority order:

   ```text
   while (tasks remain):
     - Mark task as in-progress
     - Read any referenced files from the plan or discovered during Phase 0
     - **If the unit's completion signal is repository-derived and that work is already present** (files exist with the expected capability, or the unit's `Verification` criteria are already satisfied by the current code), the work has likely shipped on a prior branch or session. Verify it matches, mark the task complete, and move on. Do not silently reimplement.
     - **If any part of the unit depends on out-of-repo state, that part has no git-derived completion signal** (see below)
     - Look for similar patterns in codebase
     - Find existing test files for implementation files being changed (Test Discovery — see below)
     - Choose the evidence strategy for this task before changing behavior (see below)
     - When the strategy calls for pre-implementation proof, create/update/strengthen the test now and observe the expected failure or baseline
     - Implement following existing conventions
     - Add, update, or remove any remaining tests to match implementation changes
     - Run System-Wide Test Check (see below)
     - Run tests after changes
     - Assess testing coverage: did this task change behavior? If yes, were existing tests inspected, and were tests added, updated, strengthened, or deliberately left unchanged with a reason? If none were touched, is the justification deliberate (pure config, no behavioral change, manual-only surface) and paired with replacement verification?
     - Mark task as completed
     - Evaluate for incremental commit (see below)
   ```

   **Batch independent reads.** The plan's referenced files, pattern searches, and test discovery do not depend on one another — request them in one response rather than one per turn. Only the write-and-verify steps are inherently sequential.

   **Out-of-repo completion signals** — when any part of a unit's completion depends on state outside the repository (a console setting, a DNS record, a CMS object, live-system rows), that part has **no git-derived completion signal**. Decide it from the observed state of the deliverable, never from a clean tree and never from a tracker write — a task marked done in the todo tool is not evidence. Mark it complete only when that state is already satisfied; execute only when it is observably unsatisfied and re-applying is safe or the user authorized it; otherwise ask, or block in non-interactive mode. This matters because deployment manifests, config maps, and secrets/config patches are in scope for this skill: a repo-side manifest existing does not mean the cluster-side state was ever applied.

   When a task reveals durable context, retain it immediately with `hindsight-embed memory retain` using the guidance in [`rosey-hindsight`](../../rosey-hindsight/SKILL.md). Good candidates include user preferences, project conventions, failed-command fixes, environment requirements, architecture decisions, and workarounds. Do not store secrets or sensitive data.

   When a unit carries an `Execution note`, honor it. For test-first units, write the failing test before implementation for that unit. For characterization-first units, capture existing behavior before changing it. For units without an `Execution note`, **default to proof-first when the code and test surface make it practical** — an unannotated behavior change should not silently become test-after.

   Guardrails for execution posture:
   - Do not write the test and implementation in the same step when working test-first
   - Do not skip verifying that a new or changed test fails **for the expected reason** before implementing the fix or feature
   - Do not over-implement beyond the current behavior slice when working test-first
   - Do not add a duplicate regression test when an existing test is the right home — update or strengthen that test, then observe the failure
   - Skip proof-first discipline for trivial renames, pure configuration, pure styling, generated artifacts, and manual-only surfaces — but record the reason and the replacement verification rather than staying silent

   **Test Discovery** — Before implementing changes to a file, find its existing test files (search for test/spec files that import, reference, or share naming patterns with the implementation file). When a plan specifies test scenarios or test files, start there, then check for additional test coverage the plan may not have enumerated. Changes to implementation files should be accompanied by corresponding test updates — new tests for new behavior, modified tests for changed behavior, removed or updated tests for deleted behavior.

   **Evidence Strategy** — Test Discovery decides *where the proof belongs*. Make this call before changing behavior, not after:

   | Situation | Action |
   | --- | --- |
   | An existing test already fails for the intended behavior | Use that as the red evidence; do not add a duplicate |
   | An existing test covers the contract but asserts the old or wrong expectation | Update that test, run it, and verify the expected failure before implementing |
   | An existing test is over-mocked or misses the real chain | Strengthen it narrowly, then verify it fails for the right reason |
   | No existing test covers the behavior | Add the smallest focused failing test, or a characterization test, that proves this behavior slice |
   | Testing is genuinely inappropriate for the task | Record the no-test exception **and its replacement verification** before marking the task complete |

   The last row is not a silence: name what was checked instead. Note also that the test-runner prerequisite below resolves the strategy to that row by construction — with no configured runner there is no test to place, so record the exception and move on rather than treating the two rules as being in conflict.

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

   # 3. Commit with conventional message, path-limited to those same files
   git commit -m "feat(scope): description of this unit" -- <files related to this logical unit>
   ```

   **Path-limit every commit.** A bare `git commit` absorbs whatever the user already had staged before this run started. Pass the same file list to `git commit -- <paths>` so only this unit's files land.

   **Handling merge conflicts:** If conflicts arise during rebasing or merging, resolve them immediately. Incremental commits make conflict resolution easier since each commit is small and focused.

   **Note:** Commits use clean conventional messages. No attribution footers, at any stage — `rosey-pr` does not add them either.

   **Commit ownership is the orchestrator's, always.** Serial subagents implement and may run their own unit's focused tests as a self-check; staging, committing, and the authoritative test run happen here after the diff is reviewed.

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
