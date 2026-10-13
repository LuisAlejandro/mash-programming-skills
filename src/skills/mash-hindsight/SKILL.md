---
name: mash-hindsight
description: Shared Hindsight embed CLI contract for Mash Programming Skills cross-session memory. Use only when a gated skill is active — the hindsight-memory rule lists them — not for generic planning, implementation, or diff review.
---

# Mash Programming Skills Hindsight

## Proof of compliance

First Mash Programming Skills status message after the Hindsight gate MUST include exactly one of:

- `Hindsight: recalled (<brief useful context>)`
- `Hindsight: unavailable (<reason>)`

No line → gate not run. "Unavailable" requires a failed `daemon status` — not silent skip.

## Communication while using this skill

Caveman level, drop conditions, and what stays uncompressed are in the caveman rule.

Mash Programming Skills uses Hindsight through the local `hindsight-embed` CLI. This is a CLI-only integration: do not add Hindsight to the workspace MCP config.

## CLI usage

The machine-global pin in `~/.config/mash/hindsight-pin` records the expected Hindsight version. Agents do not install or upgrade Hindsight from this skill.

**Routine commands** use the `hindsight-embed` binary on the machine (`PATH` often needs the uv tool shim — Cursor shells and hooks may omit it):

```bash
export PATH="${HOME}/.local/bin:${PATH}"
hindsight-embed <command> ...
```

Hindsight memory complements, but does not replace, curated `.mash/solutions/` learnings or Sentrux topology data:

- `.mash/solutions/` and `mash-learnings-researcher` are curated institutional knowledge.
- Hindsight is dynamic cross-session memory for preferences, procedure outcomes, task discoveries, and recurring project context.
- Sentrux is structural and session topology signal.

## Availability

This skill owns the **single executable availability-and-recall procedure**. The hindsight-memory rule points here; gated skills name only their gate point, and must not restate the sequence.

Before relying on memory, check whether the local embed daemon is running:

```bash
export PATH="${HOME}/.local/bin:${PATH}"
hindsight-embed daemon status
```

`daemon status` alone is not proof of availability. It is a bare `GET /health == 200` on the configured port, so any unrelated service squatting on that port is reported as a running daemon. Confirm the fingerprint before trusting it:

```bash
export PATH="${HOME}/.local/bin:${PATH}"
port="$(sed -n 's/^HINDSIGHT_API_PORT=\([0-9][0-9]*\).*/\1/p' "${HOME}/.hindsight/embed" | tail -1)"
port="${port:-8888}"
curl -fsS -m 2 "http://127.0.0.1:${port}/version"   # must return a Hindsight api_version
```

A 200 with HTML, or a body without `api_version`, means the daemon is not answering and the port is held by something else. Record that as `Hindsight: unavailable (port N held by a non-Hindsight service)` — do not treat it as availability, and do not attempt to free the port yourself.

If status fails (CLI missing, not configured, or daemon down):

1. Record `Hindsight: unavailable (<reason>)` in the first status message.
2. Continue the Mash Programming Skills workflow without memory.
3. Do not attempt to install, configure, or upgrade Hindsight from this skill.
4. Optionally note that local memory is unavailable and the user can enable it via their Mash Programming Skills setup outside this repo — do not invent install steps here.

Daemon warm-restart (installed globally by Mash Programming Skills):

- **Cursor:** `~/.cursor/hooks/ensure-hindsight-daemon.sh` via user `~/.cursor/hooks.json` `sessionStart`
- **OpenCode:** native plugin `~/.config/opencode/plugin/mash-hindsight-daemon.ts`, which invokes the global script
- **Pi:** `~/.pi/agent/scripts/ensure-hindsight-daemon.sh` via `~/.pi/agent/extensions/mash-hindsight-daemon.ts` on `session_start`

Do not run `daemon start` manually during Mash Programming Skills workflows; use `daemon status` only.

`hindsight-embed` forwards memory commands to a standalone `hindsight` CLI binary. It is versioned separately from the embed and API, so `hindsight --version` should match the pin in `~/.config/mash/hindsight-pin`; `install.sh` enforces that.

If status still fails after the hook runs, check `~/.hindsight/hook-last-run.log` for clues. Record `Hindsight: unavailable (<reason>)` and continue.

Do not block Mash Programming Skills planning, implementation, QA, or handoff when Hindsight is unavailable. Continue the workflow and record `HINDSIGHT: unavailable -- <reason>` where a handoff envelope asks for memory status.

## Bank Resolution

Use this bank ID rule for every command:

1. If `HINDSIGHT_EMBED_BANK_ID` is set, use it.
2. Otherwise derive a repo-local bank from the git root folder name:

```bash
bank="${HINDSIGHT_EMBED_BANK_ID:-$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9][^a-z0-9]*/-/g; s/^-//; s/-$//')}"
```

This keeps memory scoped to the current cloned repository by default.

## Recall

Recall at the gate point in the hindsight-memory rule, and only while one of those skills is active. Do not recall for generic planning, implementation, or diff review outside them.

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

At the end of `mash-work`, retain a concise but rich session summary: plan path, files changed, what shipped, verification commands, blockers, and important decisions.

## Reflect

Use `reflect` when the next step requires synthesis rather than raw recall:

```bash
export PATH="${HOME}/.local/bin:${PATH}"
hindsight-embed memory reflect "$bank" "Based on past work in this repository, what constraints should guide this implementation?"
```

Use reflect sparingly; recall is cheaper and sufficient for most workflow entry points.

## Safety

- Do not store secrets, credentials, tokens, private keys, or sensitive customer data.
- Do not duplicate full `.mash/solutions/` documents into memory. Store a short pointer and the outcome if it helps future recall.
- Do not let Hindsight failures block Mash Programming Skills workflows.
- Do not assume memory is complete or authoritative; verify against the current repository before acting.
- Do not install, configure, or upgrade Hindsight from this skill (that lives in the agentic-env installer, not in app repos).
