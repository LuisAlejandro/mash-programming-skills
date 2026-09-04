---
name: rosey-parallel
description: Orchestrate an epic's task list through the rosey pipeline (plan → work → qa → lint) in parallel — per-task planning worktrees, deterministic file-disjoint track sequencing, one batched human gate, delegated external-harness workers (pi → opencode → cursor-agent), local-only integration with a bounded fix-up loop, and resumable run state.
argument-hint: "[run-inputs.json] or [--resume <run-id>]"
---

# Rosey Parallel

## Communication while using this skill

**Caveman lite** for status prose during the run: strip filler and hedging; keep articles and full sentences; stay professional and tight. Technical accuracy unchanged; quoted plans, worker output, and handoffs unchanged.

## What this skill does

Runs a *task list* (an epic) through the rosey pipeline concurrently. Independent tasks run in parallel; tasks touching the same files or declaring dependencies run serially on one **track**. One batched human review happens before execution; after it, work → qa → lint and integration run non-interactive.

The skill **delegates** to external harness workers (`pi` / `opencode` / `cursor-agent`); it never runs parallel work inside its own agent context. It is **local-only**: integrates into the base branch locally and stops — no push, no PR. State lives in a run-scoped directory so interrupted runs resume.

## Pipeline

`epic (task list) → validate → scaffold (contracts-before-code) → per-task planning (worktrees) → sequencing → batched human gate → parallel track execution → integration (local) → parallel verification → final report + run state`

## Run inputs

A run receives:

- `tasks`: list of `{id, goal, deps?: [ids]}`
- `base_branch` (default `develop`)
- optional harness override (`pi` | `opencode` | `cursor-agent`)
- optional tunables: `max_parallel`, `timeout_budget`

The epic-level brainstorm that produced the validated task list happens **outside** the run (origin 5.1). The task list arrives as a pre-existing input.

## Helper

All state transitions, validation, footprint parsing, sequencing, worktree ops, harness drivers, phase runners, and integration live in the helper module. The coordinating agent invokes helper subcommands and narrates status — it does not reimplement logic in prose.

```bash
# self-check / smoke
.cursor/skills/rosey-parallel/.venv/bin/python .cursor/skills/rosey-parallel/scripts/rosey_parallel.py --self-check
```

## Flow

1. **Validate** the task list fail-fast (R2): duplicate ids, unknown deps, self-deps, cycles, empty list all named in one error.
2. **Scaffold** (hardening R10): one architect worker defines shared contracts (interfaces, types, schemas, stubs) before executors fan out, so parallel workers code against a stable surface.
3. **Snapshot base** SHA; create per-task planning worktrees+branches (R4).
4. **Plan in parallel**: one delegated harness worker per task, plan-only. Each plan yields a machine-readable file footprint (R5) parsed from the plan's `**Files:**` sections.
5. **Sequence** (deterministic, U4): overlap graph → connected components = tracks; within a track, topological order over declared deps; tracks ordered by smallest id. Empty-footprint tasks default to singleton tracks. Track membership is footprint-overlap only; dependency edges are handled by frontier admission (hardening R3).
6. **Batched human gate** (R10): review all N plans + the track grouping/ordering in one sitting. Per-plan: drop / re-plan (then re-sequence) / abort. Dropping a task others depend on is rejected at the gate.
7. **Execute tracks** (hardening R3/R4): dependency-frontier admission — a task runs the moment its deps are done and a slot is free; file-overlap tasks stay serialized on a track; oversubscribed tasks park in a FIFO denied queue. One harness worker per task: work (rosey-work non-interactive) → qa (rosey-qa headless, base = previous task's end SHA) → lint. A task is `done` only when it emits an evidence artifact (hardening R7). Worker outcomes: `done` / `blocker` / `timeout` / `failure`; a failure carries a corrective fix hint (hardening R8). A blocker/timeout/failure halts that track only, and its dependents cascade to `skipped` at quiescence (hardening R6). **Drift check** at every task boundary (R16): a task touching files another live track declared pivots that other track to the fix-up path.
8. **Integrate locally** (R19): dedicated integration worktree, `merge-tree` dry-run, merge tracks in order, lint+test gates, base ref moves only when gates pass. Residual issues become fix-up rounds (cap 2, R20).
9. **Parallel verification** (hardening R9): after integration, three verifiers (code review + test runner + architecture/contract check) fan out concurrently on the integrated result; a rejection sends the task back to fix-and-re-verify (bounded rounds).
10. **Final report** (U9): per-track status, blocker/timeout/failure detail, integrated commit list, base SHA vs integration tip, leftover worktrees/branches, outstanding fix-ups or human blockers, and fast-forward instruction for the user's live base checkout.

## Resume

Re-invoke with the same run id (`--resume <run-id>`). The helper loads recorded state, kills orphaned harness processes, re-runs missing planners, resets and relaunches the interrupted task, and skips completed tasks. Run state lives in gitignored `rosey/parallel/<run-id>/`.

## Worker prompt contract

The substrate-agnostic worker prompt plus phase-runner details are in [`references/worker-prompt.md`](references/worker-prompt.md). It carries the task goal, plan path, the rosey-work/rosey-qa/lint non-interactive contracts, tracked-driver overrides (branch pre-created — skip branch setup; skip Sentrux session gating), and expected handoff-envelope emission.

## Harness drivers

Selection is deterministic: explicit override first, else the highest-priority available via probe (pi → opencode → cursor-agent). Per-harness invocation shapes and signal verification are in the helper's driver layer (U6). No harness provides its own run timeout — the orchestrator enforces per-task budgets and kills/reaps process groups.
