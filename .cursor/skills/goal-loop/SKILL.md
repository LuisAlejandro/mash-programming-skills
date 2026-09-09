---
name: goal-loop
description: Orchestrates an autonomous goal loop. Delegates to the bundled goal-loop-driver.sh script, which re-invokes the goal-loop-iteration skill once per pass until the worklog records a terminal stop state. Always runs fully unattended (the agent runs in a shell the user cannot see or answer). State lives under rosey/loops/goal/. Use when the user wants a repository driven toward a goal without manual re-invocation.
argument-hint: "[--max-iterations=N] [--no-progress-limit=N] [--failure-limit=N] [--agent=AGENT] [--workspace=PATH] [--model=MODEL] <goal>"
---

# goal-loop

Orchestrate an autonomous loop that drives a repository toward a goal. This skill does not perform
the work itself; it delegates to the bundled driver script, which re-invokes the
`goal-loop-iteration` skill once per pass until the worklog records a terminal stop state
(`SUCCESS`, `BUDGET`, `ERROR`, `BLOCKED`, or `CANCELLED`).

## 1. Parse the invocation

Recognize options only while they are leading, whitespace-delimited tokens:

- `--max-iterations=N` (default `50`)
- `--no-progress-limit=N` (default `3`)
- `--failure-limit=N` (default `3`)
- `--agent=AGENT` (agent binary to invoke; default `opencode`, alternative `pi`)
- `--workspace=PATH` (workspace root; default current directory)
- `--model=MODEL` (optional model override)

Stop option parsing at the first unrecognized token. The exact remaining text, including spacing and
line breaks, is the goal. Do not interpret option-looking text after the goal begins.

Require positive integers for numeric options. If no goal remains and no existing `GOAL.md` can be
resumed, ask for a goal.

## 2. Delegate to the driver

Locate `scripts/goal-loop-driver.sh` relative to this skill's directory and execute it with the parsed
options and the goal. The driver always runs **unattended** — it passes `--auto` (opencode) or
`--approve` (pi) to the agent so no approval prompt can hang the run, because the agent executes in a
shell the user cannot see or answer. State always lives under `<workspace>/rosey/loops/goal/`; it is not configurable. The script
invokes the `goal-loop-iteration` skill once per pass in single-iteration mode (never this
orchestrator), so this delegation is not recursive.

Report the script's final outcome — the terminal stop state and the iteration count — and stop. This
skill performs no repository work itself; all work happens inside `goal-loop-iteration` passes driven
by the script.
