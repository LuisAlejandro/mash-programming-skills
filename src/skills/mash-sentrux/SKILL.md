---
name: mash-sentrux
description: Shared Sentrux MCP contract for topology-aware planning and structural handoff. Used by mash-plan (scan/health) and mash-work (sessions, dsm, git_stats, session_end, test_gaps). Documents install, repo resolution, artifacts, and handoff gates.
---

# Mash Programming Skills Sentrux

## Communication while using this skill

Caveman level, drop conditions, and what stays uncompressed are in the caveman rule.

Single source of truth for Sentrux integration across **mash-plan**, **mash-work**, and **mash-qa**. Read this skill when any of the Mash Programming Skills references Sentrux, topology artifacts, or structural handoff context.

## Prerequisites

### Install (required on the machine running the agent)

- **macOS:** `brew install sentrux/tap/sentrux`
- **Linux:** `curl -fsSL https://sentrux.dev/install.sh | sh`
- **Windows / from source:** `cargo install sentrux` or build from [github.com/sentrux/sentrux](https://github.com/sentrux/sentrux)

Verify: `sentrux --version`

### Do not use `sentrux scan` in the terminal

The CLI subcommand **`sentrux scan`** (and bare **`sentrux`** / **`sentrux /path`**) **opens the desktop GUI** and blocks the terminal until you close the window. That is expected Sentrux behavior, not a hang.

| Need | Use | Never use |
|------|-----|-----------|
| Agent planning / QA (quality_signal, health, sessions) | **MCP tools** via `sentrux mcp` (see below) | `sentrux scan` |
| Manual headless metrics in terminal | **`sentrux gate`** | `sentrux scan` |
| CI rules file | **`sentrux check`** (needs `.sentrux/rules.toml`) | `sentrux scan` |

**Mash Programming Skills must call Sentrux only through MCP** — never the CLI — for `scan`, `health`, `session_start`, `session_end`, `dsm`, `git_stats`, `test_gaps`, etc. Match the MCP transport **by capability**, not by a literal tool name: use whatever call-MCP-tool primitive the current harness exposes (see **MCP (workspace)** below).

### Headless CLI fallback (humans / MCP down)

When MCP is unavailable but the binary is installed:

```bash
# From the workspace root (.), not a subdirectory such as src/.
sentrux gate --save .                    # once: saves .sentrux/baseline.json, prints Quality (0–10000 scale)
sentrux gate .                           # after edits: compares baseline, exits 0/1, no GUI
```

Read `quality_signal` from the `Quality:` line or `.sentrux/baseline.json` (display scale = JSON value × 10000 when value &lt; 1). For bottleneck/root_causes you still need MCP **`health`** or enable MCP.

Do **not** commit `.sentrux/baseline.json` unless the team adopts `sentrux gate` as a repo baseline (out of scope for v1).

### MCP (workspace)

Sentrux is configured in the global MCP config (Cursor `~/.cursor/mcp.json`, OpenCode `~/.config/opencode/opencode.json`, or Pi's shared MCP config):

```json
"sentrux": {
  "command": "sentrux",
  "args": ["mcp"]
}
```

Before calling tools, read the MCP tool descriptors exposed by the `sentrux` server in the current harness, then invoke them with the enabled server identifier — not only the short name `sentrux`.

Transport by harness (match by capability, as in `mash-plan/references/research.md`):

| Harness | Call primitives | Server identifier shape |
|---|---|---|
| Cursor | `CallMcpTool` | `project-0-<workspace>-sentrux` (from the MCP file system) |
| Pi | `mcp({ server, tool, args })`, or `mcpScript` to batch several calls | `sentrux` |
| OpenCode | the native MCP tool surface | `sentrux` |

Read the descriptors before the first call so the correct tool names and arguments come from the server, not from this document.

### Unavailable fallback

If the binary or MCP server is missing:

- Set `status: "unavailable"` in the topology artifact
- **mash-plan:** still writes the plan; omit numeric signals; note unavailability in the Architecture Baseline (Sentrux) section
- **mash-work:** skip session gate; document reason in review brief; do **not** block handoff context preparation
- **mash-qa:** proceed with `SENTRUX_REVIEW_CONTEXT` marked unavailable

## Repository scope

The application repository is the workspace root itself. All Sentrux commands run relative to the workspace root directory (e.g., `.`).

1. **Workspace root** is the single scan target.
2. Do not attempt to resolve or scan multiple sibling or child repositories.

## MCP tools by phase

| Phase | Caller | Tools | Purpose |
|-------|--------|-------|---------|
| Plan | mash-plan | `scan`, `health` | Baseline `quality_signal`, `bottleneck`, `root_causes` |
| Execute | mash-work | `session_start`, `dsm`, `git_stats`, `rescan` (optional) | Session baseline; hotspots; dependency direction |
| Handoff prep | mash-work | `session_end`, `test_gaps` | Delta vs baseline; untested paths near edits |

### Planning notes from bottleneck

When writing `planning_notes` or plan guidance, map bottleneck to actions:

| Bottleneck | Planning / execution guidance |
|------------|-------------------------------|
| **equality** | Split work across existing modules; avoid new god files in `components/`, `services/`, `lib/` |
| **acyclicity** | Avoid new import cycles; fix cycles in early days if plan allows |
| **modularity** | Keep new code inside existing package boundaries |
| **depth** | Prefer shallow wrappers before deep dependency chains |
| **redundancy** | Edit existing helpers; do not duplicate utilities |

## Artifacts

All artifacts live beside the implementation plan in **`.mash/plans/`**, sharing the plan basename.

| File | Writer | Example basename |
|------|--------|------------------|
| `<plan-basename>.topology.json` | mash-plan | `2025-05-22-001-feat-feature-plan.topology.json` |
| `<plan-basename>.sentrux-review-brief.json` | mash-work | `2025-05-22-001-feat-feature-plan.sentrux-review-brief.json` |

Derive basename from the implementation plan filename (strip `.md`, append suffix).

Use one key for the actual scan root (typically `"."`). Use a child path only when the tool response explicitly scopes the repository there.

### topology.json schema

```json
{
  "generatedAt": "2026-05-22T12:00:00Z",
  "tool": "sentrux",
  "repos": {
    ".": {
      "quality_signal": 6772,
      "bottleneck": "equality",
      "root_causes": {
        "modularity": 6700,
        "acyclicity": 10000,
        "depth": 10000,
        "equality": 6100,
        "redundancy": 8800
      },
      "planning_notes": "Prefer extending existing components; avoid new top-level utils.",
      "status": "ok"
    }
  }
}
```

**Per-repo `status` values:** `ok` | `skipped` | `unavailable`

For `skipped` or `unavailable`, omit numeric fields; include `skip_reason` string.

### sentrux-review-brief.json schema

```json
{
  "generatedAt": "2026-05-22T18:00:00Z",
  "sessions": {
    ".": {
      "pass": true,
      "signal_before": 6772,
      "signal_after": 6810,
      "bottleneck_after": "equality",
      "test_gaps": ["src/features/foo/handler.ts"]
    }
  },
  "blocked": false,
  "override": null
}
```

Top-level `blocked`: `true` if any session has `pass: false` and no valid override.

### Override (block QA handoff)

When **mash-work** `session_end` reports `pass: false` for the workspace root:

1. Attempt remediation (refactor imports, split files, remove cycles); re-run `session_end`
2. If still failing, **stop** — do not prepare success handoff context
3. User may unblock with exact phrase: **`override sentrux handoff block`**
4. On override, set:

```json
"override": {
  "by": "user",
  "at": "2026-05-22T18:30:00Z",
  "reason": "<full user message quoting the override request>"
},
"blocked": false
```

Then allow handoff context preparation; include override in `SENTRUX_REVIEW_CONTEXT`.

## SENTRUX_REVIEW_CONTEXT (markdown for review/QA)

Build from `sentrux-review-brief.json` and topology:

```markdown
## Sentrux summary

| Repo | Session | Signal | Test gaps |
| . | pass (6772 → 6810) | equality | src/.../handler.ts |

**Override:** none
```

If unavailable, pass: `Sentrux unavailable — structural review skipped.`

## Session state (optional)

**mash-work** may store Sentrux session state in the task tracker or a small sidecar artifact when crash recovery requires it:

```json
"sentruxSessions": {
  ".": "started"
}
```

Use only for crash recovery: on resume, do not call `session_start` again if the session is already marked `started`. Do not restore the old progress JSON as primary execution state.

## References

- [Sentrux docs](https://sentrux.dev/)
- [MCP setup](https://sentrux.dev/docs/mcp/)
