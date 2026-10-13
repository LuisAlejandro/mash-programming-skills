# mash-parallel worker prompt contract

Substrate-agnostic prompt template for delegated harness workers (`pi`, `opencode`, `cursor-agent`, `codex`, `claude`). The orchestrator fills the placeholders and invokes the configured harness per KTD4 with the appropriate launch flag set.

## Structure

```
You are a Mash Programming Skills worker running one task of an epic inside a pre-created worktree.

TASK GOAL: {goal}
PLAN PATH: {plan_path}   (read it; honor the plan)
ORIGIN DOC: {origin_doc}   (the task's requirements doc; mash-plan's origin. Empty when no matching .mash/brainstorms/*-requirements.md exists — mash-plan then stops at its missing-origin gate and you report the gap in BLOCKERS; do not invent the requirements yourself)
REPO CONVENTIONS: read AGENTS.md at the repo root.

CONSTRAINTS:
- Branch is pre-created ({track_branch}): `mash-work` works in place on the current branch and never runs branch setup, so no override argument is needed. Stay on it: do not create `feature/<slug>` or switch branches. The orchestrator verifies the worktree's branch after each committed phase and fails the task on a mismatch.
- Skip Sentrux session gating. Record SENTRUX: unavailable for this phase.
- Phase: {phase}  (one of: plan | work | qa | lint | scaffold | verify)

PHASE CONTRACT:
- plan:    run mash-plan in mode:non-interactive for this task, using
           ORIGIN DOC as the upstream requirements document (mash-plan
           requires one and stops without it). If ORIGIN DOC is empty there is
           no real origin for this task: do not invent requirements to satisfy
           the gate — emit the missing-origin BLOCKERS and stop. Write the plan
           document (do NOT edit tracked files outside the plan doc). Emit the
           required handoff envelope
           (MASH_PLAN_HANDOFF ... END_MASH_PLAN_HANDOFF) containing
           PLAN PATH (repo-relative), FILES (the per-unit footprint), and
           BLOCKERS (none if none), so the orchestrator can record the plan
           path and QA/lint can honor it.
- work:    run mash-work mode:non-interactive against the recorded plan path.
           Emit the required handoff envelope
           (MASH_WORK_HANDOFF ... END_MASH_WORK_HANDOFF) containing
           FILES_CHANGED (repo-relative) and BLOCKERS (empty if none). ALSO emit
           an evidence artifact (MASH_EVIDENCE ... END_MASH_EVIDENCE) — a
           captured test run or output proving the work. No evidence artifact
           = not done (hardening R7).
- qa:     run mash-qa mode:headless against base {qa_diff_base} (the
           previous task's end commit, or the track branch point for the first
           task). Expect terminal "Review complete".
- lint:   run mash-lint mode:non-interactive (delegates tooling discovery to
           the skill). Emit LINT_HANDOFF with LINT_STATUS: pass|failed. Record
           any files lint modified; a pass requires LINT_STATUS: pass.
- scaffold: (orchestrator-level single architect; not a per-task phase) Define
           the shared contracts the epic's tasks depend on and write
           .mash/parallel/scaffold-contract.md. The PHASE CONTEXT block below
           names the tasks and the contract's source of truth.
- verify:  (orchestrator-level integrated verification; not a per-task phase)
           Review the merged result at the integrated tip, over the diff range
           named in the PHASE CONTEXT block. Report a pass as terminal `done`;
           report any rejection as populated `BLOCKERS:` naming file and
           problem. An empty BLOCKERS means nothing was found.

FINISH:
- Emit the handoff envelope exactly when done.
- Never leave uncommitted changes: the orchestrator commits a fixup commit
  after each qa/lint phase on the track branch.
```

## Overrides (driven by the orchestrator)

| Key | Value | Why |
| --- | --- | --- |
| `sentrux` | `skip` | N concurrent workers would contend on repo-scoped Sentrux session state |
| `qa_diff_base` | previous task end SHA / track branch point | deterministic per-task QA diff range |
| `branch` | `mash-parallel/<run-id>/track-<n>` | all tasks in a track accumulate commits on one branch |

## Phase context block (scaffold and verify only)

`scaffold` and `verify` are orchestrator-level phases, not per-task ones, so
they are rendered by the same driver but with no task goal or origin document.
The driver therefore appends a `PHASE CONTEXT` block after the template:

- **scaffold** — names the epic's task goals, states that contracts come from
the task list (not invention), and fixes the output path
(`.mash/parallel/scaffold-contract.md`) and its success condition.
- **verify** — names the verifier role, the exact integrated tip under review,
and the `base..tip` diff range to inspect.

Without this block those phases reached the worker as a bare phase label and a
placeholder task id (`__scaffold__`, `__verify__/<verifier>`), so "success" was
whatever the harness's generic non-empty-output signal said. The block is the
phase's actual contract.

## Integration gate

`options.integration_command` is the epic-level integration check, run in the
merged integration worktree. When it is absent and the target repo has no
`src/skills/mash-parallel/tests` suite, the gate reports
`integration gate not configured` in the run report rather than reporting a
pass for checks that never ran.

(There is no `branch_setup` override. `mash-work` no longer has a branch setup step — it works in place on the pre-created track branch unconditionally.)

## Success / failure signals

- **done**: work phase emits a handoff envelope (empty `BLOCKERS:`, `FILES_CHANGED:`) AND an evidence artifact (`MASH_EVIDENCE ... END_MASH_EVIDENCE`). QA phase reaches terminal `Review complete`. lint passes.
- **blocker**: handoff (or QA) yields populated `BLOCKERS:` that require human judgment. Halts that track only.
- **timeout**: no progress within the per-task budget (hard wall-clock + no-progress on log growth). Orchestrator kills the process group.
- **failure**: driver-detected — missing terminal structured event, exit non-zero, unparsable handoff, missing evidence artifact, QA `Review failed (headless mode)`. Halts that track like a blocker. A known harness error string maps to a corrective fix hint for the fix-up round (hardening R8).

## Notes

- The orchestrator captures worker stdout to run-scoped log files; QA run artifacts are relocated into the run-state directory after the phase so they do not pollute later tasks' working trees.
- After qa/lint the orchestrator commits any uncommitted fixes on the track branch before recording the task's end SHA, so validated fixes land inside the task's commit range and appear in the touched-file record and the integration merge.
