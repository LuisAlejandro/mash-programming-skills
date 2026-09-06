---
name: docs-loop
description: Orchestrates an autonomous documentation audit-and-apply loop. Delegates to the bundled docs-loop-driver.sh script, which re-invokes the docs-loop-iteration skill once per repository until the ledger records every repository as terminal. Always applies documentation fixes; never opens pull requests. Always runs fully unattended (the agent runs in a shell the user cannot see or answer). State lives under rosey/loops/docs/. Use when the user wants repository documentation audited and fixed without manual re-invocation.
argument-hint: "[REPO_PATH ...] [--max-iterations=N] [--agent=AGENT] [--workspace=PATH] [--model=MODEL]"
---

# docs-loop

Orchestrate an autonomous loop that audits and fixes repository documentation. This skill does not
perform the work itself; it delegates to the bundled driver script, which re-invokes the
`docs-loop-iteration` skill once per repository until the ledger records every repository as terminal
(`DONE`, `DEFERRED`, `SKIPPED`, or `BLOCKED`).

This skill **always applies** documentation fixes and **never opens pull requests**.

## 1. Parse the invocation

Recognize options only while they are leading, whitespace-delimited tokens:

- `--max-iterations=N` (hard cap on passes; default `50`)
- `--agent=AGENT` (agent binary to invoke; default `cursor-agent`)
- `--workspace=PATH` (workspace root; default current directory)
- `--model=MODEL` (optional model override)

Any remaining text is the repository path list (or empty for the workspace root). Stop option
parsing at the first unrecognized token.

Require positive integers for numeric options. If no goal remains and no existing ledger can be resumed,
ask for a goal.

## 2. Delegate to the driver

Locate `scripts/docs-loop-driver.sh` relative to this skill's directory and execute it with the parsed
options and any repository paths. The driver always runs **unattended** — it passes `--yolo --trust` to
the agent so no approval prompt can hang the run, because the agent executes in a shell the user cannot
see or answer. State always lives under `<workspace>/rosey/loops/docs/`; it is not configurable. The
script invokes the `docs-loop-iteration` skill once per repository in single-repository mode (never this
orchestrator), so this delegation is not recursive.

Report the script's final outcome — the run result (`SUCCESS`, `BLOCKED`, or `PARTIAL`) and the
repository count — and stop. This skill performs no repository work itself; all work happens inside
`docs-loop-iteration` passes driven by the script.
