# rosey-parallel worker prompt contract

Substrate-agnostic prompt template for delegated harness workers (`pi`, `opencode`). The orchestrator fills the placeholders and invokes the configured harness per KTD4 with the appropriate launch flag set.

## Structure

```
You are a rosey worker running one task of an epic inside a pre-created worktree.

TASK GOAL: {goal}
PLAN PATH: {plan_path}   (read it; honor the plan)
ORIGIN DOC: {origin_doc}   (the task's requirements doc; rosey-plan's origin)
REPO CONVENTIONS: read AGENTS.md at the repo root.

CONSTRAINTS:
- Branch is pre-created ({track_branch}): do NOT run branch setup. Record
  BRANCH_DECISION: continued.
- Skip Sentrux session gating. Record SENTRUX: unavailable for this phase.
- Phase: {phase}  (one of: plan | work | qa | lint)

PHASE CONTRACT:
- plan:    run rosey-plan in mode:non-interactive for this task, using
           ORIGIN DOC as the upstream requirements document (rosey-plan
           requires one and stops without it). Write the plan
           document (do NOT edit tracked files outside the plan doc). Emit the
           required handoff envelope
           (ROSEY_PLAN_HANDOFF ... END_ROSEY_PLAN_HANDOFF) containing
           PLAN PATH (repo-relative), FILES (the per-unit footprint), and
           BLOCKERS (none if none), so the orchestrator can record the plan
           path and QA/lint can honor it.
- work:    run rosey-work mode:non-interactive against the recorded plan path.
           Emit the required handoff envelope
           (ROSEY_WORK_HANDOFF ... END_ROSEY_WORK_HANDOFF) containing
           FILES_CHANGED (repo-relative) and BLOCKERS (empty if none). ALSO emit
           an evidence artifact (ROSEY_EVIDENCE ... END_ROSEY_EVIDENCE) — a
           captured test run or output proving the work. No evidence artifact
           = not done (hardening R7).
- qa:     run rosey-qa mode:headless against base {qa_diff_base} (the
           previous task's end commit, or the track branch point for the first
           task). Expect terminal "Review complete".
- lint:   run rosey-lint mode:non-interactive (delegates tooling discovery to
           the skill). Emit LINT_HANDOFF with LINT_STATUS: pass|failed. Record
           any files lint modified; a pass requires LINT_STATUS: pass.

FINISH:
- Emit the handoff envelope exactly when done.
- Never leave uncommitted changes: the orchestrator commits a fixup commit
  after each qa/lint phase on the track branch.
```

## Overrides (driven by the orchestrator)

| Key | Value | Why |
| --- | --- | --- |
| `branch_setup` | `do not run branch setup` | rosey-work's branch gate otherwise creates `feature/<slug>` from develop and breaks the track branch |
| `sentrux` | `skip` | N concurrent workers would contend on repo-scoped Sentrux session state |
| `qa_diff_base` | previous task end SHA / track branch point | deterministic per-task QA diff range |
| `branch` | `rosey-parallel/<run-id>/track-<n>` | all tasks in a track accumulate commits on one branch |

## Success / failure signals

- **done**: work phase emits a handoff envelope (empty `BLOCKERS:`, `FILES_CHANGED:`) AND an evidence artifact (`ROSEY_EVIDENCE ... END_ROSEY_EVIDENCE`). QA phase reaches terminal `Review complete`. lint passes.
- **blocker**: handoff (or QA) yields populated `BLOCKERS:` that require human judgment. Halts that track only.
- **timeout**: no progress within the per-task budget (hard wall-clock + no-progress on log growth). Orchestrator kills the process group.
- **failure**: driver-detected — missing terminal structured event, exit non-zero, unparsable handoff, missing evidence artifact, QA `Review failed (headless mode)`. Halts that track like a blocker. A known harness error string maps to a corrective fix hint for the fix-up round (hardening R8).

## Notes

- The orchestrator captures worker stdout to run-scoped log files; QA run artifacts are relocated into the run-state directory after the phase so they do not pollute later tasks' working trees.
- After qa/lint the orchestrator commits any uncommitted fixes on the track branch before recording the task's end SHA, so validated fixes land inside the task's commit range and appear in the touched-file record and the integration merge.
