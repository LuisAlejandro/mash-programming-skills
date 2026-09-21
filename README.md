# Rosey Agentic Environment

Rosey is a machine-global agent environment for Cursor, OpenCode, and Pi. The
installer distributes Rosey skills, rules, agents, guidance, MCP configuration,
and Hindsight hooks into each IDE's global home. It does **not** write IDE trees,
`AGENTS.md`, `DESIGN.md`, MCP files, pins, or `rosey/*` directories into the
current repository.

Scoped skills that belong to a particular repository are owned locally by that
repository and are not installed by Rosey. See
`rosey/plans/2026-09-21-scoped-skills-repo-ownership.md` for that migration.

## Installation

Run the installer from this source checkout, or point `ROSEY_AGENTIC_ENV` at the
checkout:

```bash
ROSEY_AGENTIC_ENV=/path/to/rosey-agentic-env \
  bash /path/to/rosey-agentic-env/install.sh
```

The command is global-only and is safe to run from any directory. Re-running it
refreshes Rosey-owned global skills, rules, agents, hooks, references, and
configuration entries without touching project files.

### Global destinations

| Surface | Destination |
|---|---|
| Rosey state, pins, guidance, contracts | `~/.config/rosey/` |
| Cursor rules | `~/.cursor/rules/` |
| Cursor skills | `~/.cursor/skills/` |
| Cursor agents | `~/.cursor/agents/` |
| Cursor hooks | `~/.cursor/hooks.json`, `~/.cursor/hooks/` |
| OpenCode skills | `~/.config/opencode/skills/` |
| OpenCode agents | `~/.config/opencode/agents/` |
| OpenCode global guidance | `config.instructions[]` in `~/.config/opencode/opencode.json` |
| OpenCode warm-start | `~/.config/opencode/plugin/rosey-hindsight-daemon.ts` |
| Pi skills and context | `~/.pi/agent/skills/`, `~/.pi/agent/AGENTS.md` |
| Pi agents | `~/.agents/` |
| Pi warm-start | `~/.pi/agent/extensions/`, `~/.pi/agent/scripts/` |
| Pi shared MCP config | `~/.config/mcp/mcp.json` (plus the accepted `mcpServers` mirror in Pi settings) |

OpenCode uses `config.instructions[]` rather than
`~/.config/opencode/AGENTS.md`; this preserves repository-local `AGENTS.md`
loading. Cursor receives global guidance through `~/.cursor/rules/*.mdc`, not a
home-level `~/.cursor/AGENTS.md`.

## What installation does

1. Copies every remaining Rosey skill into the Cursor, OpenCode, and Pi global
   skill homes. The 27 repository-scoped skills are absent from Rosey's source
   and remain local untracked files in their owning repositories.
2. Copies specialist agents to Cursor, OpenCode, and the Pi-subagents home.
3. Copies Cursor's always-apply rules to `~/.cursor/rules/`.
4. Installs global Hindsight warm-start hooks for all three supported IDEs.
5. Writes `~/.config/rosey/AGENTS.md` and the Pi global context file. Rosey never
   creates or edits a repository-root `AGENTS.md`.
6. Installs the three shared contract references in
   `~/.config/rosey/references/` and updates global skill call sites to use
   those paths.
7. Merges Rosey's MCP servers into the global Cursor, OpenCode, and Pi config
   files. Same-name Rosey entries overwrite existing entries; this accepted
   risk has no backup or rollback.
8. Seeds the design-candidates `.env` in global skill homes from
   `.env.example` and `CURSOR_API_KEY` when available.
9. Installs optional machine tools and Pi extensions only when enabled and
   missing. Existing commands are not reinstalled.
10. Updates the machine-global Git excludes file so only Rosey working-output
    directories and the maintainer manifest remain ignored. `AGENTS.md` and
    `DESIGN.md` are not ignored.

A design-system skill may create `DESIGN.md` when the user invokes it manually.
The installer never creates that file. Other skills create `rosey/*` working
files and directories lazily as needed.

## Verification and flags

```bash
./install.sh --check
./install.sh --version
./install.sh --no-write-pin
./install.sh --no-agents       # skip global Rosey guidance files
```

`--agents`/`--guidance` explicitly enable global guidance. They no longer mean
"write a repository AGENTS.md".

## Uninstallation

Uninstallation is global-only and dry-run by default:

```bash
./uninstall.sh                 # show what would be removed
./uninstall.sh --check         # exit 0 if global Rosey artifacts exist
./uninstall.sh --apply         # remove Rosey global payload
./uninstall.sh --apply --force # also remove edited Rosey guidance files
```

It removes Rosey-owned global skills, agents, rules, hooks, plugins, guidance,
pins, contract references, manifest, and MCP entries. It preserves unrelated
user entries in shared JSON files, machine tools, Hindsight memory, and all
repositories.

## Optional Hindsight local memory

Hindsight is optional and machine-global. Configure keys in this checkout's
`.env` or the process environment; never commit secrets.

```bash
uv tool install "hindsight-embed@$(tr -d '[:space:]' < ~/.config/rosey/hindsight-pin)" \
  --with "hindsight-api@$(tr -d '[:space:]' < ~/.config/rosey/hindsight-pin)"
```

The installer seeds `~/.hindsight/embed` from
`.cursor/hindsight-embed.example` when configured and starts the daemon when
possible. Warm-start locations are:

- Cursor: `~/.cursor/hooks/ensure-hindsight-daemon.sh` via user `hooks.json`
- OpenCode: native plugin under `~/.config/opencode/plugin/`
- Pi: global extension and `~/.pi/agent/scripts/ensure-hindsight-daemon.sh`

Routine Rosey commands use `hindsight-embed` with
`PATH="${HOME}/.local/bin:${PATH}"`. See
`.cursor/skills/rosey-hindsight/SKILL.md` for the full Hindsight contract.

## Repository files

Rosey does not generate repository guidance or scaffolding. If a project needs
project-specific instructions, its owner may create and track `AGENTS.md`.
`DESIGN.md` is similarly user/design-skill owned. Skills create `rosey/plans/`,
`rosey/insights/`, `rosey/qa/`, and other working paths only when invoked.
