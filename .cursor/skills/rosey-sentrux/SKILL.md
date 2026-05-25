---
name: rosey-sentrux
description: Shared Sentrux MCP contract for topology-aware planning and QA. Used by rosey-manager (scan/health), rosey-developer (sessions, dsm, git_stats), and rosey-qa (session_end, test_gaps). Documents install, repo resolution, artifacts, and handoff gates.
---

# Rosey Sentrux

Single source of truth for Sentrux integration across **rosey-manager**, **rosey-developer**, and **rosey-qa**. Read this skill when any of those skills reference Sentrux, topology artifacts, or structural QA.

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

**Rosey skills must call Sentrux only through MCP** (`CallMcpTool`, server `sentrux`) for `scan`, `health`, `session_start`, `session_end`, `dsm`, `git_stats`, `test_gaps`, etc.

### Headless CLI fallback (humans / MCP down)

When MCP is unavailable but the binary is installed:

```bash
cd src/   # repo root
sentrux gate --save .                    # once: saves .sentrux/baseline.json, prints Quality (0–10000 scale)
sentrux gate .                           # after edits: compares baseline, exits 0/1, no GUI
```

Read `quality_signal` from the `Quality:` line or `.sentrux/baseline.json` (display scale = JSON value × 10000 when value &lt; 1). For bottleneck/root_causes you still need MCP **`health`** or enable MCP.

Do **not** commit `.sentrux/baseline.json` unless the team adopts `sentrux gate` as a repo baseline (out of scope for v1).

### MCP (workspace)

Sentrux is configured in [`.cursor/mcp.json`](../../mcp.json):

```json
"sentrux": {
  "command": "sentrux",
  "args": ["--mcp"]
}
```

Before calling tools, read MCP tool descriptors under the `sentrux` server folder. Invoke via `CallMcpTool` with `server: "sentrux"`.

### Unavailable fallback

If the binary or MCP server is missing:

- Set `status: "unavailable"` in the topology artifact
- **rosey-manager:** still writes the plan; omit numeric signals; note unavailability in the Architecture baseline section
- **rosey-developer:** skip session gate; document reason in review brief; do **not** block QA handoff
- **rosey-qa:** proceed without `SENTRUX_REVIEW_CONTEXT`

## Repository scope

The application repository is the workspace root itself. All Sentrux commands run relative to the workspace root directory (e.g., `.`).

1. **Workspace root** is the single scan target.
2. Do not attempt to resolve or scan multiple sibling or child repositories.

## MCP tools by phase

| Phase | Caller | Tools | Purpose |
|-------|--------|-------|---------|
| Plan | rosey-manager | `scan`, `health` | Baseline `quality_signal`, `bottleneck`, `root_causes` |
| Execute | rosey-developer | `session_start`, `dsm`, `git_stats`, `rescan` (optional) | Session baseline; hotspots; dependency direction |
| QA prep | rosey-developer | `session_end`, `test_gaps` | Delta vs baseline; untested paths near edits |

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

All artifacts live in **`docs/plans/<prd-slug>/`**, sharing the implementation plan basename.

| File | Writer | Example basename |
|------|--------|------------------|
| `<plan-basename>.topology.json` | rosey-manager | `2025-05-22-feature-implementation-plan.topology.json` |
| `<plan-basename>.sentrux-review-brief.json` | rosey-developer | `2025-05-22-feature-implementation-plan.sentrux-review-brief.json` |

Derive basename from the implementation plan filename (strip `.md`, append suffix).

### topology.json schema

```json
{
  "generatedAt": "2026-05-22T12:00:00Z",
  "tool": "sentrux",
  "repos": {
    "src/": {
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
    "src/": {
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

When **rosey-developer** `session_end` reports `pass: false` for any in-scope repo:

1. Attempt remediation (refactor imports, split files, remove cycles); re-run `session_end`
2. If still failing, **stop** — do not invoke rosey-qa
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

Then allow QA handoff; include override in `SENTRUX_REVIEW_CONTEXT`.

## SENTRUX_REVIEW_CONTEXT (markdown for rosey-qa)

Build from `sentrux-review-brief.json` and topology:

```markdown
## Sentrux summary

| Repo | Session | Signal | Test gaps |
| src/ | pass (6772 → 6810) | equality | src/.../handler.ts |

**Override:** none
```

If unavailable, pass: `Sentrux unavailable — structural review skipped.`

## Progress file (optional)

**rosey-developer** may add to `<plan-basename>.progress.json`:

```json
"sentruxSessions": {
  "src/": "started"
}
```

Use for crash recovery: on resume, do not call `session_start` again if the session is already marked `started`.

## References

- [Sentrux docs](https://sentrux.dev/)
- [MCP setup](https://sentrux.dev/docs/mcp/)
