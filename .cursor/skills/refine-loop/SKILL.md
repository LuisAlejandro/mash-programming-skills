---
name: refine-loop
description: Orchestrates an autonomous refinement loop. Delegates to the bundled refine-loop-driver.sh script, which re-invokes the refine-loop-iteration skill once per round until the backlog records a terminal outcome. Always runs fully unattended (the agent runs in a shell the user cannot see or answer). State lives under rosey/loops/refine/. Use when the user wants a working repository refined through behavior-preserving improvements without manual re-invocation.
argument-hint: "[theta=N] [focus=LENS,...] [--max-iterations=N] [--agent=AGENT] [--workspace=PATH] [--model=MODEL] <intent>"
---

# refine-loop

Orchestrate an autonomous loop that refines a working repository through small, behavior-preserving
changes. This skill does not perform the work itself; it delegates to the bundled driver script, which
re-invokes the `refine-loop-iteration` skill once per round until the backlog records a terminal outcome
(`SUCCESS`, `BUDGET`, `ERROR`, `NEEDS-FIX`, or `CANCELLED`).

## 1. Parse the invocation

Recognize options only while they are leading, whitespace-delimited tokens:

- `theta=N` (ROI threshold; default `2.0`)
- `focus=LENS,...` (allowlisted subset of `architecture`, `usability`, `production`, `refactoring`)
- `--max-iterations=N` (hard cap on rounds; default `50`)
- `--agent=AGENT` (agent binary to invoke; default `cursor-agent`)
- `--workspace=PATH` (workspace root; default current directory)
- `--model=MODEL` (optional model override)

Stop option parsing at the first unrecognized token. The exact remaining text, including spacing and
line breaks, is the refinement intent. Do not interpret option-looking text after the intent begins.

Require positive integers for numeric options. If no intent remains and no existing state can be
resumed, ask what should be refined.

## 2. Delegate to the driver

Locate `scripts/refine-loop-driver.sh` relative to this skill's directory and execute it with the parsed
options and the intent. The driver always runs **unattended** — it passes `--yolo --trust` to the agent
so no approval prompt can hang the run, because the agent executes in a shell the user cannot see or
answer. The target is always the workspace root; state always lives under
`<workspace>/rosey/loops/refine/`; neither is configurable. The script invokes the
`refine-loop-iteration` skill once per round in single-round mode (never this orchestrator), so this
delegation is not recursive.

Report the script's final outcome — the terminal outcome and the round count — and stop. This skill
performs no repository work itself; all work happens inside `refine-loop-iteration` rounds driven by the
script.
