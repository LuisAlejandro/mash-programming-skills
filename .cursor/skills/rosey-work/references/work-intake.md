# Work Intake

Read this on entering Phase 0. It owns input triage and complexity routing, plan reading, task-list construction, and dispatch strategy. Return to the kernel with the resolved plan, task list, and execution strategy.

## Phase 0: Input Triage

`rosey-work` executes a plan. Resolve one from `<input_document>` or from the session, in this order:

Branch setup does not exist in this skill — work happens in place on the current branch; branching and PRs belong to `rosey-pr` (invoked explicitly by the user).

0. **Blank input — latest software plan.** After stripping `mode:` (and the bypass phrase if present), if the remaining input is empty:
   1. Glob `rosey/plans/*-plan.md`.
   2. Keep only **software** plans: YAML frontmatter is present. Skip universal plans that start with `# Title` plus a `Created:` date and have no YAML frontmatter.
   3. Pick the newest remaining file by mtime.
   4. Interactive: if more than one software plan was modified today, confirm which one. Otherwise announce the chosen path and use it.
   5. Non-interactive: use that unique latest match. If none exist, use the no-plan envelope below (`BLOCKERS: no plan path supplied or resolvable`).
1. **Explicit path** — the input is a file path to a plan. Use it.
2. **Handoff** — `rosey-plan` loaded this skill and passed a plan path. Use it.
3. **Session context** — a plan was written earlier in this conversation and the user is now asking to implement it, possibly after clarifying questions. Use that plan; name the path so the user can correct it.

**Software-plan shape.** After resolving a path (explicit, handoff, or session), inspect the document:
- YAML frontmatter plus software plan sections (Implementation Units) → continue.
- No YAML and no Implementation Units → stop: "This is a non-software plan; `rosey-work` does not execute it." In `mode:non-interactive`, emit the handoff envelope with that sentence in `BLOCKERS:`.

Once a software plan is resolved, continue to Phase 1 after the Phase 0.0 gate completes.

**No plan resolved — stop.** Do not implement from a prose description. The pipeline is `rosey-brainstorm` → `rosey-plan` → `rosey-work`, and the plan is what carries the Goal Capsule, Verification Contract, Definition of Done, and Implementation Units this skill executes against. Without one, there is nothing to execute and no contract to verify against.

In `mode:interactive`, name the gap and offer the route:

```text
No plan found for this work.

rosey-work implements a plan — it does not decide what to build. Point me at a
plan in rosey/plans/, or run /rosey-plan first (which needs a requirements doc
from /rosey-brainstorm).

If a plan exists somewhere I did not look, give me the path.
```

Offer to load `rosey-plan` in-session. If the user supplies a path, treat it as the plan and continue. Do not proceed on any other answer.

In `mode:non-interactive`, do not halt silently — emit the handoff envelope with the gap named in `BLOCKERS:`, so an automated caller sees a result rather than a hang:

```text
ROSEY_WORK_HANDOFF
FILES_CHANGED:
BLOCKERS: no plan path supplied or resolvable; rosey-work requires a plan. Pass one explicitly.
END_ROSEY_WORK_HANDOFF
```

---

## Phase 1: Quick Start

1. **Read Plan and Clarify**

   - **Size the read.** Plans are markdown (`.md`). Read them as `rosey-plan`'s [`plan-sections.md`](../../rosey-plan/references/plan-sections.md) prescribes: a short plan in full; anything longer heading-scanned first (`rg -n '^#{1,3} ' <plan>`), then read in ranges — Goal Capsule, the active unit plus what it cites, Verification Contract, Definition of Done. That file owns the reading protocol; do not restate its mechanics here.
   - Treat the plan as a decision artifact, not an execution script
   - If the plan includes sections such as `Implementation Units`, `Work Breakdown`, `Requirements`, `Files`, `Test Scenarios`, or `Verification`, use those as the primary source material for execution
   - **Read the three contract sections when present**, and carry them forward:
     - **Goal Capsule** — the Objective, the Means when an approach is pinned, and the stop conditions. When implementation starts pulling away from the Objective, that is the signal to stop, not to improvise.
     - **Verification Contract** — the repo's actual commands and gates. Phase 3 runs these; note them now.
     - **Definition of Done** — global and per-unit completion criteria, including the cleanup criterion.

     **A missing section is a noted degradation, not a blocker.** Fall back to per-unit `Verification` plus `rosey-lint`, and record the gap in the handoff envelope (e.g. `no Verification Contract`). This matches how the skill already treats an unavailable Sentrux, an unavailable Hindsight, and a missing test runner.
   - Check for `Execution note` on each implementation unit — these carry the plan's execution posture signal for that unit (for example, test-first or characterization-first). Note them when creating tasks.
   - Check for `### Deferred to Implementation` under `## Open Questions` — these are questions the planner intentionally left for you to resolve during execution. Note them before starting so they inform your approach rather than surprising you mid-task. See the lifecycle mapping in [`plan-sections.md`](../../rosey-plan/references/plan-sections.md).
   - Check for a `Scope Boundaries` section — these are explicit non-goals. Refer back to them if implementation starts pulling you toward adjacent work
   - Review any references or links provided in the plan
   - If the plan references a Sentrux topology artifact, read it before creating tasks. If no explicit path exists, look beside the plan for `<plan-basename>.topology.json`.
   - If the user explicitly asks for TDD, test-first, or characterization-first execution in this session, honor that request even if the plan has no `Execution note`
   - If anything is unclear or ambiguous, ask clarifying questions now in interactive mode. In non-interactive mode, resolve from plan context or stop with a blocker.
   - If clarifying questions were needed above, get user approval on the resolved answers in interactive mode. If no clarifications were needed, proceed without a separate approval step — plan scope is the plan's authority, not something to renegotiate. In non-interactive mode, no approval step is allowed.
   - **Do not skip this** - better to ask questions now than build the wrong thing
   - **Do not edit the plan body during execution.** The plan is a decision artifact; progress lives in git commits and the task tracker. Per-unit completion is determined during execution by reading the current file state.

2. **Setup Environment**

   **Work in place on the current branch.** No branch setup, no git-flow, no checkout, no stash. Record `BRANCH: <current branch>` (from `git branch --show-current`) in the handoff envelope before the first edit. Branching and PRs belong to `rosey-pr` — the user invokes it explicitly after work completes.

   **Pre-work inventory — record this before the first edit:**

   ```bash
   git branch --show-current
   git status --short --untracked-files=all    # the user's in-progress files
   git log @{u}..HEAD --oneline                # local commits not yet pushed
   ```

   **Nothing in that set is this run's to commit or publish.** Path-limited commits (Phase 2) keep untouched WIP out of every commit automatically, so this inventory exists for the one case they cannot separate: a unit that must edit a file that was _already dirty_.

   When that happens, ask _once_, at the first commit that would include such a file, covering every file in that situation: commit those files with the user's edits included, or leave them uncommitted for the rest of the run and name them as unshipped in the final summary. In non-interactive mode, do not ask and do not edit them — stop with a blocker naming the files, so "commit, then re-run" is a clean recovery. List any file this run deliberately left uncommitted in the handoff envelope so `rosey-pr` does not publish it silently.

   **Resolve verification commands** (reuse in the Phase 2 loop; still run full `rosey-lint` at Phase 3):
   1. Use the plan's `## Verification Contract` when present.
   2. Otherwise inspect Makefile targets (`make test`, `make lint`) and Compose services.
   3. Otherwise resolve through [`rosey-lint`](../../rosey-lint/SKILL.md) discovery and the Docker-via-Make always-on guideline.
   4. Prefer Docker-via-Make (containers when a working Compose + Make setup exists); otherwise use host commands per the always-on guideline.

3. **Create Task List**
   - Use the harness's task-tracking tool (its todo/plan primitive — match by capability) to break the plan into actionable tasks. When the harness exposes none, keep the task list in your own working context rather than simulating one in chat
   - Derive tasks from the plan's implementation units, dependencies, files, test targets, and verification criteria
   - When the plan defines U-IDs for Implementation Units, name the task from a brief outcome-led form of the unit's Goal and **append** the U-ID (e.g., "Add parser coverage (U3)"). Never lead with the identifier — the reader should understand the work before the traceability label; aim for five words or fewer before the ID. This keeps blocker references, deferred-work notes, and final summaries anchored to the same identifier the plan uses, so progress and traceability remain unambiguous across plan edits. Skip ordinal counts ("unit 1 of 5") when the full task list is already visible
   - Carry each unit's `Execution note` into the task when present
   - For each unit, read the `Patterns to follow` field before implementing — these point to specific files or conventions to mirror
   - Use each unit's `Verification` field as the primary "done" signal for that task
   - Do not expect Implementation Units to contain implementation code, micro-step TDD instructions, or shell choreography. The Verification Contract names real repo commands — resolve those in Setup Environment above.
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
   - If a topology artifact exists and Sentrux is available, read [`rosey-sentrux`](../../rosey-sentrux/SKILL.md), then start an MCP `session_start` before the first implementation task.
   - Before large edits, consult MCP `git_stats` and `dsm` so hotspots, dependency direction, and topology bottlenecks influence execution.
   - If Sentrux is unavailable, continue implementation and record the reason for the final review brief.

   **Hindsight recall:**
   - Phase 0.0 already ran the required recall. Fold that result into the execution approach. Do not paste raw recall output into chat unless the user asks.
   - Do **not** call `memory recall` again.
   - **Deferred-recall exception:** if the plan path was unknown at Phase 0.0 (blank-input latest-plan glob or session resolve after the gate) and the first query could not include plan context, run **one** additional `hindsight-embed memory recall` with the plan path, affected modules, important risks, and U/R/A/F/AE IDs. That is the only second recall this skill allows.
   - If Hindsight is unavailable, continue and record `HINDSIGHT: unavailable -- <reason>` for handoff.

4. **Choose Execution Strategy**

   After creating the task list, decide how to execute based on the plan's size and dependency structure:

   | Strategy             | When to use                                                                                                                                                                                                                  |
   | -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
   | **Inline**           | 1-2 small tasks, or tasks needing user interaction mid-flight. Also the whole run when the harness exposes no subagent primitive: execute every unit inline under the same unit packet and verification contract |
   | **Serial subagents** | 3+ tasks. Each subagent gets a fresh context window focused on one unit — prevents context degradation across many tasks. Requires plan-unit metadata (Goal, Files, Approach, Test scenarios) |

   **`rosey-work` does not dispatch parallel subagents.** Concurrent implementation belongs to [`rosey-parallel`](../../rosey-parallel/SKILL.md), which owns real per-task worktrees, deterministic file-disjoint sequencing, a batched human gate, and bounded integration. Serial dispatch already buys the thing that matters here — a fresh context window per unit — and parallelism is a latency optimization, not a quality one. When a plan is large enough to want concurrency, invoke `rosey-parallel` explicitly rather than improvising it here.

   Dispatch tiering and the degradation ladder (no per-dispatch model override → inherit and keep the read budgets; no subagent primitive → run inline; how to classify a rejected dispatch) follow `~/.config/rosey/references/model-tiers.md`.

   **Subagent dispatch** uses your available subagent or task spawning mechanism. For each unit, give the subagent:
   - The full plan file path (for overall context)
   - The specific unit's Goal, Files, Approach, Execution note, Patterns, Test scenarios, and Verification
   - Any resolved deferred questions relevant to that unit
   - Instruction to check whether the unit's test scenarios cover all applicable categories (happy paths, edge cases, error paths, integration) and supplement gaps before writing tests
   - Instruction to choose the unit's evidence strategy and **capture the red failure or characterization baseline as it happens** — the orchestrator cannot reconstruct it afterward

   **Compact subagent receipt contract** — every implementation subagent must return this terse receipt and avoid narrative unless blocked:

   ```text
   UNIT: <U-ID or task name>
   FILES:
   - <repo-relative path>
   CHANGED:
   - <change, <=12 words>
   VERIFY:
   - <command or check>: <pass | failed | skipped with reason>
   EVIDENCE:
   - behavior_changed: <yes | no>
   - existing tests inspected: <paths or none>
   - tests added/changed/used-unchanged: <which, or none + reason>
   - red observed: <how it failed before the fix | characterization baseline | n/a>
   - verification run: <command>: <result>
   BLOCKER: <none | one-line blocker>
   ```

   `EVIDENCE:` exists because the worker is the only party that witnesses red-before-implementation; `VERIFY:` records a result, not proof. When a worker omits it, re-derive what the tree allows and mark the rest **unverified** — never write an observation nobody made.

   If the subagent produced risky behavior, failed verification, or changed files outside the declared `Files:` list, it may add `DETAIL:` with only the evidence needed for orchestrator review. Full exploration stories stay out of the parent context.

   **Permission mode:** Omit the `mode` parameter when dispatching subagents so the user's configured permission settings apply. Do not pass `mode: "auto"` — it overrides user-level settings like `bypassPermissions`.

   **After each subagent completes:**
   1. Read the receipt, then **review the actual diff** — `git status` / diff, not the reported paths. Declared `Files:` lists are routinely incomplete because plans describe _what_, not _how_, so workers legitimately touch files nobody anticipated. Reported paths are a starting hint you verify
   2. Run the relevant test suite to confirm the tree is healthy. **A clean merge is not proof of compatibility** — two units can integrate without conflict and still be semantically incompatible
   3. If tests fail, diagnose and fix before proceeding — do not dispatch dependent units on a broken tree
   4. Roll the worker's `EVIDENCE:` into the run's evidence record
   5. Update the task list (do not edit the plan body — progress is carried by the commit)
   6. **Retire the worker handle.** A handle is bound to exactly one unit: it may retry or recover _that_ unit, never receive a different one. Dispatch the next unit in a fresh context
