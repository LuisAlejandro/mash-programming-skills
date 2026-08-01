---
name: rosey-hindsight
description: Shared Hindsight embed CLI contract for Rosey cross-session memory. Use before non-trivial Rosey planning, work, or QA to recall relevant context and retain durable preferences, procedures, and learnings.
---

# Rosey Hindsight

## Proof of compliance

First Rosey status message after the Hindsight gate MUST include exactly one of:

- `Hindsight: recalled (<brief useful context>)`
- `Hindsight: unavailable (<reason>)`

No line → gate not run. "Unavailable" requires a failed `daemon status` — not silent skip.

## Communication while using this skill

**Caveman ultra** for assistant status prose while this skill runs: abbreviate routine workflow words, strip conjunctions where safe, use arrows for causality, and keep one word when one word is enough. Technical accuracy unchanged; CLI commands, bank IDs, quoted errors, memory content, and command output unchanged. Drop ultra for setup instructions, security/privacy warnings, user confusion, or when the user asks for normal or long-form wording.

**Memory boundary:** Caveman ultra applies to chat/status prose, not memory recall text, retain payloads, handoff fields, or instructions the user must run exactly.

Rosey uses Hindsight through the local `hindsight-embed` CLI. This is a CLI-only integration: do not add a Hindsight server to `.cursor/mcp.json` for this flow.

## CLI usage

The pin in `rosey/hindsight-pin` (fallback: `.cursor/hindsight-pin`) records the expected Hindsight version for this checkout. Agents do not install or upgrade Hindsight from this skill.

**Routine commands** use the `hindsight-embed` binary on the machine (`PATH` often needs the uv tool shim — Cursor shells and hooks may omit it):

```bash
export PATH="${HOME}/.local/bin:${PATH}"
hindsight-embed <command> ...
```

Hindsight memory complements, but does not replace, curated `rosey/solutions/` learnings or Sentrux topology data:

- `rosey/solutions/` and `rosey-learnings-researcher` are curated institutional knowledge.
- Hindsight is dynamic cross-session memory for preferences, procedure outcomes, task discoveries, and recurring project context.
- Sentrux is structural and session topology signal.

## Availability

Before relying on memory, check whether the local embed daemon is running:

```bash
export PATH="${HOME}/.local/bin:${PATH}"
hindsight-embed daemon status
```

If status fails (CLI missing, not configured, or daemon down):

1. Record `Hindsight: unavailable — <reason>` in the first status message.
2. Continue the Rosey workflow without memory.
3. Do not attempt to install, configure, or upgrade Hindsight from this skill.
4. Optionally note that local memory is unavailable and the user can enable it via their Rosey agentic-env setup outside this repo — do not invent install steps here.

Daemon warm-restart (already wired when Rosey was installed into the repo):

- **Cursor:** `.cursor/hooks/ensure-hindsight-daemon.sh` via `.cursor/hooks.json` `sessionStart`
- **VS Code:** same script at `.github/hooks/ensure-hindsight-daemon.sh` via `.vscode/tasks.json` `runOn: folderOpen` (Copilot has no session-start hooks). Allow automatic tasks once per workspace (`Tasks: Manage Automatic Tasks`)

Do not run `daemon start` manually during Rosey workflows; use `daemon status` only.

If status still fails after the hook runs, check `~/.hindsight/hook-last-run.log` for clues. Record `Hindsight: unavailable — <reason>` and continue.

Do not block Rosey planning, implementation, QA, or handoff when Hindsight is unavailable. Continue the workflow and record `HINDSIGHT: unavailable` where a handoff envelope asks for memory status.

## Bank Resolution

Use this bank ID rule for every command:

1. If `HINDSIGHT_EMBED_BANK_ID` is set, use it.
2. Otherwise derive a repo-local bank from the git root folder name:

```bash
bank="${HINDSIGHT_EMBED_BANK_ID:-$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9][^a-z0-9]*/-/g; s/^-//; s/-$//')}"
```

This keeps memory scoped to the current cloned repository by default.

## Recall

Recall before substantive work:

- Before `rosey-plan` gathers local research
- Before `rosey-work` starts implementation
- Before `rosey-qa` reviews a known diff scope, when memory may affect risk assessment

Use a task-specific query with the plan path, feature summary, relevant modules, PR scope, and stable IDs when present:

```bash
export PATH="${HOME}/.local/bin:${PATH}"
hindsight-embed memory recall "$bank" "Task summary, plan path, modules, risks, and stable requirement IDs"
```

Fold useful recalled context into the approach. Do not dump raw CLI output into chat unless the user asks.

## Retain

Retain only durable, non-secret information. Pass rich context, not a pre-compressed one-liner; Hindsight extracts structured facts internally.

Use `--context` to label the memory type:

```bash
export PATH="${HOME}/.local/bin:${PATH}"
hindsight-embed memory retain "$bank" "User prefers strict TypeScript and explicit return types in this repository." --context preferences

hindsight-embed memory retain "$bank" "Running npm test without NODE_ENV=test fails because the config loader expects TEST_DATABASE_URL. Setting NODE_ENV=test fixed the suite." --context procedures

hindsight-embed memory retain "$bank" "During the auth refactor, the existing middleware order required permission checks before session refresh. Reversing the order caused stale-session redirects." --context learnings
```

Retain during a task when you discover:

- User preferences or project conventions
- Commands that work or fail and why
- Setup or environment requirements
- Architecture decisions and rationale
- Bugs, regressions, or workarounds worth carrying forward

At the end of `rosey-work`, retain a concise but rich session summary: plan path, files changed, what shipped, verification commands, blockers, and important decisions.

## Reflect

Use `reflect` when the next step requires synthesis rather than raw recall:

```bash
export PATH="${HOME}/.local/bin:${PATH}"
hindsight-embed memory reflect "$bank" "Based on past work in this repository, what constraints should guide this implementation?"
```

Use reflect sparingly; recall is cheaper and sufficient for most workflow entry points.

## Safety

- Do not store secrets, credentials, tokens, private keys, or sensitive customer data.
- Do not duplicate full `rosey/solutions/` documents into memory. Store a short pointer and the outcome if it helps future recall.
- Do not let Hindsight failures block Rosey workflows.
- Do not assume memory is complete or authoritative; verify against the current repository before acting.
- Do not install, configure, or upgrade Hindsight from this skill (that lives in the agentic-env installer, not in app repos).
