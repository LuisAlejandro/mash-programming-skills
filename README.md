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
| Always-on rules (IDE-neutral) | `~/.config/rosey/always-on-rules.md` |
| Skill npm dependencies | `~/.config/rosey/node_modules/<skill>/` |
| Skill Python virtualenvs | `~/.config/rosey/venvs/<skill>/` |
| Cursor rules | `~/.cursor/rules/` |
| Cursor skills | `~/.cursor/skills/` |
| Cursor agents | `~/.cursor/agents/` |
| Cursor hooks | `~/.cursor/hooks.json`, `~/.cursor/hooks/` |
| OpenCode skills | `~/.config/opencode/skills/` |
| OpenCode agents | `~/.config/opencode/agents/` |
| OpenCode global guidance | `config.instructions[]` in `~/.config/opencode/opencode.json` |
| OpenCode warm-start | `~/.config/opencode/plugin/rosey-hindsight-daemon.ts` |
| Pi skills and context | `~/.pi/agent/skills/`, `~/.pi/agent/AGENTS.md` |
| Pi always-on rules | `~/.pi/agent/APPEND_SYSTEM.md` |
| Pi agents | `~/.agents/` |
| Pi warm-start | `~/.pi/agent/extensions/`, `~/.pi/agent/scripts/` |
| Pi shared MCP config | `~/.config/mcp/mcp.json` (plus the accepted `mcpServers` mirror in Pi settings) |

### Skill runtime dependencies

Each skill is copied into all three IDE homes, so dependencies are installed
**once** under `~/.config/rosey/` and symlinked into each copy:

```text
~/.config/rosey/node_modules/<skill>/   npm install, from the skill's package.json
~/.config/rosey/venvs/<skill>/          Python venv, from the skill's requirements.txt

~/.cursor/skills/<skill>/node_modules   -> shared store
~/.cursor/skills/<skill>/.venv          -> shared venv
```

Both Node and Python resolve through a symlinked directory, so a skill's
documented `node_modules/...` and `.venv/bin/python` paths work unchanged in
every IDE home. Per-skill isolation is preserved (no shared package set) while
nothing is installed three times. Uninstall removes the shared stores.

A skill that pulls in Playwright also gets the Chromium build it needs;
Playwright caches browsers machine-wide, so that download happens once.

OpenCode uses `config.instructions[]` rather than
`~/.config/opencode/AGENTS.md`; this preserves repository-local `AGENTS.md`
loading. Cursor receives global guidance through `~/.cursor/rules/*.mdc`, not a
home-level `~/.cursor/AGENTS.md`.

### Always-on rules in each IDE

Cursor applies `.mdc` rules natively through `alwaysApply: true`. OpenCode and Pi
have no rule frontmatter, so the installer also emits the same always-on subset as
one frontmatter-stripped Markdown bundle:

| IDE | Transport |
|---|---|
| Cursor | `~/.cursor/rules/*.mdc` (`alwaysApply: true`) |
| OpenCode | `~/.config/rosey/always-on-rules.md` via `config.instructions[]` |
| Pi | `~/.pi/agent/APPEND_SYSTEM.md` (appends to the system prompt) |

The bundle is generated from `.cursor/rules/*.mdc`; those `.mdc` files remain
the single source of truth.

### Invoking a skill

Invocation syntax differs per IDE, so the rules and skills name skills in **prose**
("invoke the rosey-plan skill") rather than with slash syntax. Prose is the only
form correct in all three; a rule is copied verbatim to every IDE, so any slash
form would be wrong in at least two of them.

| IDE | Invocation |
|---|---|
| Cursor | `/rosey-plan` (bare slash command) |
| Pi | `/skill:rosey-plan` (skills register with the `skill:` prefix) |
| OpenCode | No slash surface; the model invokes the skill through its skill tool |

Slash syntax appears only in this table, never inside a rule or skill.

## Requirements Rosey does not install

### An agent harness

Rosey installs skills, rules, and agents — not the harness that runs them. Install at
least one of `pi`, `opencode`, `cursor-agent`, `codex`, or `claude`. The installer
checks and **warns without blocking** when none is found; `rosey-parallel` also uses
these as its delegated workers, probing in that order. Pi extensions install only when
the `pi` CLI is present, so install a harness first and re-run to finish that setup.

### A GitHub token (optional)

The installer prompts once for a token to configure the GitHub MCP server, which powers
PR review, issue creation, and PR description updates in `rosey-qa`, `rosey-pr`, and
`rosey-dogfood`. Fine-grained token scopes:

| Scope | Level |
|---|---|
| Contents | Read-only |
| Pull requests | Read-only, or Read and write to post PR updates |
| Issues | Read and write, only for issue creation |
| Metadata | Read-only (automatic) |

A classic token with the `repo` scope also works. Press Enter to skip: the GitHub MCP
server is then left unconfigured rather than written with an unusable credential, and
those skills fall back to the `gh` CLI or local git. Set `GITHUB_TOKEN` in `.env` or the
environment to skip the prompt, and re-run the installer later to enable the server.

GitHub is the only issue tracker Rosey writes to.

## What installation does

1. Prunes skills, agents, rules, and shared dependency stores that the previous
   install manifest owned but the current source tree no longer contains.
2. Copies every Rosey skill in this source tree into the Cursor, OpenCode, and
   Pi global skill homes. Repository-scoped skills are absent from Rosey's
   source and remain local untracked files in their owning repositories.
3. Copies specialist agents to Cursor, OpenCode, and the Pi-subagents home.
4. Copies Cursor's always-apply rules to `~/.cursor/rules/`, then generates
   `~/.config/rosey/always-on-rules.md` and `~/.pi/agent/APPEND_SYSTEM.md` so
   OpenCode and Pi receive the same always-on rules.
5. Installs global Hindsight warm-start hooks for all three supported IDEs.
6. Writes `~/.config/rosey/AGENTS.md` and the Pi global context file. Rosey never
   creates or edits a repository-root `AGENTS.md`.
7. Installs the three shared contract references in
   `~/.config/rosey/references/` and updates global skill call sites to use
   those paths.
8. Merges Rosey's MCP servers into the global Cursor, OpenCode, and Pi config
   files. Same-name Rosey entries overwrite existing entries; this accepted
   risk has no backup or rollback.
9. Installs skill runtime dependencies once under `~/.config/rosey/` (npm for
   skills with `package.json`, a virtualenv for skills with `requirements.txt`)
   and symlinks them into each IDE copy.
10. Installs optional machine tools and Pi extensions only when enabled and
    missing. Existing commands are not reinstalled.
11. Updates the machine-global Git excludes file so only Rosey working-output
    directories and the maintainer manifest remain ignored. `AGENTS.md` and
    `DESIGN.md` are not ignored.

Skills create `rosey/*` working files and directories lazily as needed. Rosey
does not ship a design-to-code pipeline; design skills and their `DESIGN.md` /
`rosey/designs/` artifacts belong to the repository that installs them.

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

It removes the exact Rosey-owned global skills, agents, and rules recorded by
the last install manifest, plus hooks, plugins, guidance, pins, contract
references, shared dependency stores, the manifest, and MCP entries. It
preserves unrelated user entries in shared JSON files, machine tools, Hindsight
memory, and all repositories.

## Optional Hindsight local memory

Hindsight is optional and machine-global. Configure keys in this checkout's
`.env` or the process environment; never commit secrets.

```bash
uv tool install "hindsight-embed@$(tr -d '[:space:]' < ~/.config/rosey/hindsight-pin)" \
  --with "hindsight-api@$(tr -d '[:space:]' < ~/.config/rosey/hindsight-pin)"
```

The installer seeds `~/.hindsight/embed` from
`.cursor/hindsight-embed.example` when configured and starts the daemon when
possible. Every active `KEY=` line in that template is filled from this
checkout's `.env`, so a fresh machine inherits the configured provider.

### Pointing Hindsight at an OpenAI-compatible gateway

Hindsight has no generic gateway provider. Use `openai` plus a base URL, for
example OmniRoute:

```dotenv
HINDSIGHT_API_LLM_PROVIDER=openai
HINDSIGHT_API_LLM_MODEL=omniroute-hindsight
HINDSIGHT_API_LLM_API_KEY=<gateway key>
HINDSIGHT_API_LLM_BASE_URL=https://assistant.fundere.app/v1
```

Set those four keys in `.env` and re-run `install.sh` on an unconfigured
machine. Existing `~/.hindsight/embed` files are never overwritten, so a machine
already configured for another provider must be updated by hand (or removed) and
the daemon restarted with `hindsight-embed daemon restart`. Use a purpose-built
combo such as `omniroute-hindsight` rather than a generic routing alias such as
`auto/*`, because Hindsight runs repeated structured extraction over the same
memory and needs stable behavior.
Embeddings stay on the local provider by default; switching them to a gateway
changes the vector dimensions and invalidates existing memories.

### Ports, client version, and health checks

- `HINDSIGHT_API_PORT` in `.env` seeds the daemon port (default `8888`). Set it
  when another service already owns `8888`, for example a Stream Deck install.
- `install.sh` also aligns the standalone `hindsight` CLI binary with
  `~/.config/rosey/hindsight-pin`. The embed installs that binary from a vendor
  installer outside the `uv` pin and only when it is missing, so a stale binary
  would otherwise never upgrade.
- Health checks must not rely on `hindsight-embed daemon status` alone: it is a
  bare `GET /health == 200`, so any service on the port looks like a running
  daemon. The Rosey hook and `install.sh` require the `/version` fingerprint
  (`api_version`) instead.
- Seeding never writes an active empty assignment. Hindsight parses integer
  settings with `int(os.getenv(KEY, default))` and the embed forwards every
  `HINDSIGHT_*` profile key into the daemon environment, so `KEY=` (set but
  empty) would abort daemon startup with `ValueError`.

Warm-start locations are:

- Cursor: `~/.cursor/hooks/ensure-hindsight-daemon.sh` via user `hooks.json`
- OpenCode: native plugin under `~/.config/opencode/plugin/`
- Pi: global extension and `~/.pi/agent/scripts/ensure-hindsight-daemon.sh`

Routine Rosey commands use `hindsight-embed` with
`PATH="${HOME}/.local/bin:${PATH}"`. See
`.cursor/skills/rosey-hindsight/SKILL.md` for the full Hindsight contract.

## Repository files

Rosey does not generate repository guidance or scaffolding. If a project needs
project-specific instructions, its owner may create and track `AGENTS.md`.
`DESIGN.md` is owned by the user or by whichever repository installs a
design-to-code pipeline. Skills create `rosey/plans/`, `rosey/insights/`,
`rosey/qa/`, and other working paths only when invoked.
