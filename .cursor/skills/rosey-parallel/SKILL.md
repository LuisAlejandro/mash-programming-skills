---
name: rosey-parallel
description: Orchestrate an epic's task list through the rosey pipeline (plan → work → qa → lint) in parallel — per-task planning worktrees, deterministic file-disjoint track sequencing, one batched human gate, delegated external-harness workers (pi → opencode), local-only integration with a bounded fix-up loop, and resumable run state.
argument-hint: "[run-inputs.json] or [--resume <run-id>]"
---

# Rosey Parallel

## Communication while using this skill

**Caveman lite** for status prose during the run: strip filler and hedging; keep articles and full sentences; stay professional and tight. Technical accuracy unchanged; quoted plans, worker output, and handoffs unchanged.

## What this skill does

Runs a *task list* (an epic) through the rosey pipeline concurrently. Independent tasks run in parallel; tasks touching the same files or declaring dependencies run serially on one **track**. One batched human review happens before execution; after it, work → qa → lint and integration run non-interactive.

The skill **delegates** to external harness workers (`pi` / `opencode`); it never runs parallel work inside its own agent context. It is **local-only**: integrates into the base branch locally and stops — no push, no PR. State lives in a run-scoped directory so interrupted runs resume.

## Pipeline

`epic (task list) → validate → per-task origin docs → scaffold (contracts-before-code) → per-task planning (worktrees, rosey-plan) → sequencing → batched human gate → parallel track execution (per-task rosey-plan → rosey-work → rosey-qa → rosey-lint) → integration (local) → parallel verification → final report + run state`

## Run inputs

A run receives:

- `tasks`: list of `{id, goal, deps?: [ids]}`
- `base_branch` (default `develop`)
- optional harness override (`pi` | `opencode`)
- optional tunables: `max_parallel`, `timeout_budget`

The epic-level brainstorm that produced the validated task list happens **outside** the run (origin 5.1). The task list arrives as a pre-existing input.

**Per-task origin docs.** `rosey-plan` requires an upstream requirements document and stops without one. Before planning, each task's `{id, goal, deps}` is projected into `rosey/parallel/origins/<task-slug>-requirements.md` and passed to the worker as `ORIGIN DOC`. If a real `rosey/brainstorms/*-requirements.md` already exists whose slug matches the task, that file is used and no projection is written. `rosey/parallel/` is never a search root for brainstorm or plan origin discovery.

## Helper

All state transitions, validation, footprint parsing, sequencing, worktree ops, harness drivers, phase runners, and integration live in the helper module. The coordinating agent invokes helper subcommands and narrates status — it does not reimplement logic in prose.

**Working directory:** cwd is this skill's directory (the folder that contains this `SKILL.md`).

`.venv/` is a symlink to the machine-global skill virtualenv at `~/.config/rosey/venvs/rosey-parallel`, created by `install.sh` from this skill's `requirements.txt`. It carries `pytest` so the skill's own suite can run; the orchestrator itself is stdlib-only and also runs under a plain `python3`.

```bash
# self-check / smoke
.venv/bin/python scripts/rosey_parallel.py --self-check

# run an epic (loads run-inputs.json, orchestrates, saves state)
# First invocation plans and STOPS at the human gate (tasks stay PLANNED).
.venv/bin/python scripts/rosey_parallel.py run run-inputs.json [--max-parallel N]

# After reviewing the plans, resume with --approve to run work/qa/lint.
# A plain --resume (no --approve) re-stops at the gate and does NOT re-plan.
.venv/bin/python scripts/rosey_parallel.py run run-inputs.json --resume <run-id> --approve [--max-parallel N]

# scaffold phase only
.venv/bin/python scripts/rosey_parallel.py scaffold run-inputs.json

# parallel verification on an integrated tip
.venv/bin/python scripts/rosey_parallel.py verify <integrated-tip>
```

## Flow

1. **Validate** the task list fail-fast (R2): duplicate ids, unknown deps, self-deps, cycles, empty list all named in one error.
2. **Scaffold** (hardening R10): one architect worker defines shared contracts (interfaces, types, schemas, stubs) before executors fan out, so parallel workers code against a stable surface.
3. **Snapshot base** SHA; create per-task planning worktrees+branches (R4).
4. **Plan in parallel**: one delegated harness worker per task, plan-only. Each plan yields a machine-readable file footprint (R5) parsed from the plan's `**Files:**` sections.
5. **Sequence** (deterministic, U4): overlap graph → connected components = tracks; within a track, topological order over declared deps; tracks ordered by smallest id. Empty-footprint tasks default to singleton tracks. Track membership is footprint-overlap only; dependency edges are handled by frontier admission (hardening R3).
6. **Batched human gate** (R10): review all N plans + the track grouping/ordering in one sitting. Per-plan: drop / re-plan (then re-sequence) / abort. Dropping a task others depend on is rejected at the gate. **Sequencing is file-footprint-only, so the gate is where non-file contention gets caught** — scan the batch for tasks that share a contract (types, APIs, interfaces), a migration (ordering is global even when files differ), a lockfile or generated artifact, a registry/config/schema surface two tasks both append to, or an environment singleton (one dev server or port, a shared database, a browser session, a package install, a rate limit). None of these appear in a `**Files:**` footprint. When two tasks contend on one of them, merge their tracks or re-order at the gate rather than discovering it at integration.
7. **Execute tracks** (hardening R3/R4): dependency-frontier admission — a task runs the moment its deps are done and a slot is free; file-overlap tasks stay serialized on a track; oversubscribed tasks park in a FIFO denied queue. One harness worker per task: work (rosey-work non-interactive) → qa (rosey-qa headless, base = previous task's end SHA) → lint. A task is `done` only when it emits an evidence artifact (hardening R7). Worker outcomes: `done` / `blocker` / `timeout` / `failure`; a failure carries a corrective fix hint (hardening R8). A blocker/timeout/failure halts that track only, and its dependents cascade to `skipped` at quiescence (hardening R6). **Drift check** at every task boundary (R16): a task touching files another live track declared pivots that other track to the fix-up path.
8. **Integrate locally** (R19): dedicated integration worktree, `merge-tree` dry-run, merge tracks in order, lint+test gates, base ref moves only when gates pass. Residual issues become fix-up rounds (cap 2, R20).
9. **Parallel verification** (hardening R9): after integration, three verifiers (code review + test runner + architecture/contract check) fan out concurrently on the integrated result; a rejection sends the task back to fix-and-re-verify (bounded rounds).
10. **Final report** (U9): per-track status, blocker/timeout/failure detail, integrated commit list, base SHA vs integration tip, leftover worktrees/branches, outstanding fix-ups or human blockers, and fast-forward instruction for the user's live base checkout.

## Resume

Re-invoke with the same run id (`--resume <run-id>`). The helper loads recorded state, kills orphaned harness processes, re-runs missing planners, resets and relaunches the interrupted task, and skips completed tasks. Run state lives in gitignored `rosey/parallel/runs/<run-id>/`; epic inputs live in tracked `rosey/parallel/epics/<slug>/run-inputs.json`.

## Worker prompt contract

The substrate-agnostic worker prompt plus phase-runner details are in [`references/worker-prompt.md`](references/worker-prompt.md). It carries the task goal, plan path, the rosey-work/rosey-qa/lint non-interactive contracts, tracked-driver overrides (branch pre-created — skip branch setup; skip Sentrux session gating), and expected handoff-envelope emission.

## Harness drivers

Selection is deterministic: explicit override first, else the highest-priority available via probe (pi → opencode). Per-harness invocation shapes and signal verification are in the helper's driver layer (U6). No harness provides its own run timeout — the orchestrator enforces per-task budgets and kills/reaps process groups.

## Logs

The orchestrator writes exactly one file: `rosey/parallel/runs/<run-id>/logs/run.log` — a timestamped timeline of heartbeat and outcome lines. There are no per-task logs, no `summary.log`, and no `.out` redirect. Deep detail lives in the harness's own session store (see below). `pi` is launched **without** `--no-session` so its `.jsonl` session logs are retained.

## Debugging a failed run

Triage from the orchestrator log, then the harness session, then the plan and phase.

1. Open `rosey/parallel/runs/<run-id>/logs/run.log`. Find the first `[plan]|[work]|[qa]|[lint]` line that is not `done`, and note `task id`, `phase`, and `pgid`.
2. Load `rosey/parallel/runs/<run-id>/state.json`. Read that task's `plan_path`, `branch`, `worktree_path`, `status`, and `blockers`.
3. Follow the harness that ran the worker:

   - **pi** — session `.jsonl` under `~/.pi/agent/sessions/` (or `.pi/` in the repo). Match by start time near the `run.log` spawn line. Search the jsonl for `PLAN PATH`, `ROSEY_EVIDENCE`, and the last `agent_end`.
   - **opencode** — session database (sqlite) under the opencode data dir. Query sessions by timestamp; inspect message/part rows for the task prompt and the final `text` event.

4. Flow: harness session → `plan_path` in state → failing phase in `run.log`. If work failed the evidence gate, the session will show a missing `ROSEY_EVIDENCE` body even when interpret looked successful. If a timeout, the `pgid` was killed; the session log stops mid-turn.

