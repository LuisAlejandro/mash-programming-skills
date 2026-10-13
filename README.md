# Mash Programming Skills

Mash Programming Skills is a machine-global agent environment for Cursor, OpenCode, and Pi. The
installer distributes Mash Programming Skills, rules, agents, guidance, MCP configuration,
and Hindsight hooks into each IDE's global home. It does **not** write IDE trees,
`AGENTS.md`, `DESIGN.md`, MCP files, pins, or `.mash/*` directories into the
current repository.

Scoped skills that belong to a particular repository are owned locally by that
repository and are not installed by Mash Programming Skills. See
`rosey/plans/2026-09-21-scoped-skills-repo-ownership.md` for that migration.

## Installation

No checkout is required. This downloads the `develop` tarball and installs from it:

```bash
curl -fsSL https://raw.githubusercontent.com/LuisAlejandro/mash-programming-skills/develop/install.sh | bash
```

Pipe to `bash`. Flags go through as `bash -s -- --check`. Until the repository is
public, set `GITHUB_TOKEN` to a token that can read it.

A checkout installs from that checkout. `MASH_PROGRAMMING_SKILLS` points the
same script at another checkout:

```bash
MASH_PROGRAMMING_SKILLS=/path/to/mash-programming-skills \
  bash /path/to/mash-programming-skills/install.sh
```

The command is global-only and is safe to run from any directory. Re-running it
refreshes Mash Programming Skills-owned global skills, rules, agents, hooks, references, and
configuration entries without touching project files.

### Global destinations

| Surface | Destination |
|---|---|
| Mash Programming Skills state, pins, guidance, contracts | `~/.config/mash/` |
| Always-on rules (IDE-neutral) | `~/.config/mash/always-on-rules.md` |
| Skill npm dependencies | `~/.config/mash/node_modules/<skill>/` |
| Skill Python virtualenvs | `~/.config/mash/venvs/<skill>/` |
| Cursor rules | `~/.cursor/rules/` |
| Cursor skills | `~/.cursor/skills/` |
| Cursor agents | `~/.cursor/agents/` |
| Cursor hooks | `~/.cursor/hooks.json`, `~/.cursor/hooks/` |
| OpenCode skills | `~/.config/opencode/skills/` |
| OpenCode agents | `~/.config/opencode/agents/` |
| OpenCode global guidance | `config.instructions[]` in `~/.config/opencode/opencode.json` |
| OpenCode warm-start | `~/.config/opencode/plugin/mash-hindsight-daemon.ts` |
| Pi skills and context | `~/.pi/agent/skills/`, `~/.pi/agent/AGENTS.md` |
| Pi always-on rules | `~/.pi/agent/APPEND_SYSTEM.md` |
| Pi agents | `~/.agents/` |
| Pi warm-start | `~/.pi/agent/extensions/`, `~/.pi/agent/scripts/` |
| Pi shared MCP config | `~/.config/mcp/mcp.json` (plus the accepted `mcpServers` mirror in Pi settings) |

### Skill runtime dependencies

Each skill is copied into all three IDE homes, so dependencies are installed
**once** under `~/.config/mash/` and symlinked into each copy:

```text
~/.config/mash/node_modules/<skill>/   npm install, from the skill's package.json
~/.config/mash/venvs/<skill>/          Python venv, from the skill's requirements.txt

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
| OpenCode | `~/.config/mash/always-on-rules.md` via `config.instructions[]` |
| Pi | `~/.pi/agent/APPEND_SYSTEM.md` (appends to the system prompt) |

The bundle is generated from `src/rules/*.mdc`; those `.mdc` files remain
the single source of truth.

### Invoking a skill

Invocation syntax differs per IDE, so the rules and skills name skills in **prose**
("invoke the mash-plan skill") rather than with slash syntax. Prose is the only
form correct in all three; a rule is copied verbatim to every IDE, so any slash
form would be wrong in at least two of them.

| IDE | Invocation |
|---|---|
| Cursor | `/mash-plan` (bare slash command) |
| Pi | `/skill:mash-plan` (skills register with the `skill:` prefix) |
| OpenCode | No slash surface; the model invokes the skill through its skill tool |

Slash syntax appears only in this table, never inside a rule or skill.

## Requirements Mash Programming Skills does not install

### An agent harness

Mash Programming Skills installs skills, rules, and agents — not the harness that runs them. Install at
least one of `pi`, `opencode`, `cursor-agent`, `codex`, or `claude`. The installer
checks and **warns without blocking** when none is found; `mash-parallel` also uses
these as its delegated workers, probing in that order. Pi extensions install only when
the `pi` CLI is present, so install a harness first and re-run to finish that setup.

### MCP servers (optional)

On a terminal, the installer asks whether to include each MCP server it
ships. A declined server is left out, and if a previous install
had written it, this run removes it. A later install asks again. With no
terminal, every example server is merged, except `github` when `GITHUB_TOKEN`
is not already set.

- `github` powers PR review, issue creation, and PR description updates in
  `mash-qa`, `mash-pr`, and `mash-dogfood`. Including it asks for a token.
  Enter drops the server instead of writing a broken entry; those skills then
  fall back to the `gh` CLI or local git. A token already in the environment
  can be reused. Fine-grained scopes: Contents read-only, Pull requests
  read-only (read and write to post updates), Issues read and write to file
  issues, Metadata read-only. A classic token with the `repo` scope also works.
- `context7` has no credential.
- `sentrux`, `cua-driver`, and `agent-browser` ask for permission to install
  when the program is missing. Refusing drops the server, and the installer
  does not install the program. With no terminal, those installs still run
  when the tools are missing.
- `chrome-devtools` has no installer. It stays an `npx` package. If `npx` is
  absent, the installer says so and still writes the server when you include it.

GitHub is the only issue tracker Mash Programming Skills writes to.

## What installation does

1. Prunes skills, agents, rules, and shared dependency stores that the previous
   install manifest owned but the current source tree no longer contains.
2. Copies every one of the Mash Programming Skills in this source tree into the Cursor, OpenCode, and
   Pi global skill homes. Repository-scoped skills are absent from Mash Programming Skills's
   source and remain local untracked files in their owning repositories.
3. Copies specialist agents to Cursor, OpenCode, and the Pi-subagents home.
4. Copies Cursor's always-apply rules to `~/.cursor/rules/`, then generates
   `~/.config/mash/always-on-rules.md` and `~/.pi/agent/APPEND_SYSTEM.md` so
   OpenCode and Pi receive the same always-on rules.
5. Installs global Hindsight warm-start hooks for all three supported IDEs.
6. Writes `~/.config/mash/AGENTS.md` and the Pi global context file. Mash Programming Skills never
   creates or edits a repository-root `AGENTS.md`.
7. Installs the three shared contract references in
   `~/.config/mash/references/` and updates global skill call sites to use
   those paths.
8. Merges the MCP servers you accepted into the global Cursor, OpenCode, and Pi
   config files. Owned names you declined are removed. Same-name Mash Programming Skills
   entries overwrite existing entries; this accepted risk has no backup or rollback.
   With no terminal, every example server is merged (except `github` without a token).
9. Installs skill runtime dependencies once under `~/.config/mash/` (npm for
   skills with `package.json`, a virtualenv for skills with `requirements.txt`)
   and symlinks them into each IDE copy.
10. Installs optional machine tools and Pi extensions only when enabled and
    missing. On a terminal, Sentrux, CUA Driver, and agent-browser install only
    after you agree. With no terminal, those installs still run when the tools
    are missing. Existing commands are not reinstalled.
11. Updates the machine-global Git excludes file so only Mash Programming Skills working-output
    directories and the maintainer manifest remain ignored. `AGENTS.md` and
    `DESIGN.md` are not ignored.

Skills create `.mash/*` working files and directories lazily as needed. Mash Programming Skills
does not ship a design-to-code pipeline. The sibling repository `mash-design-skills`
installs those skills, shares `~/.config/mash/` through `design-install-manifest.json`,
and writes `.mash/designs/` and `.mash/design-system/` in the app. Root `DESIGN.md`
stays in the app.

## Verification and flags

```bash
./install.sh --check
./install.sh --version
./install.sh --no-write-pin
./install.sh --no-agents       # skip global Mash Programming Skills guidance files
```

`--agents`/`--guidance` explicitly enable global guidance. They no longer mean
"write a repository AGENTS.md".

## Uninstallation

Install copies `uninstall.sh` to `~/.config/mash/uninstall.sh`. That copy reads
`~/.config/mash/install-manifest.json` and does not need this repository.
`./uninstall.sh` in a checkout is the same script. Uninstallation is global-only
and dry-run by default:

```bash
~/.config/mash/uninstall.sh                 # show what would be removed
~/.config/mash/uninstall.sh --check         # exit 0 if global Mash Programming Skills artifacts exist
~/.config/mash/uninstall.sh --apply         # remove Mash Programming Skills global payload
~/.config/mash/uninstall.sh --apply --force # also remove edited Mash Programming Skills guidance files
```

It removes the Mash Programming Skills-owned global skills, agents, rules, and
MCP servers recorded by the last install manifest, plus hooks, plugins,
guidance, pins, contract references, shared dependency stores, and the manifest.
It preserves unrelated user entries in shared JSON files, machine tools,
Hindsight memory, and all repositories. A manifest with no `managed` inventory
leaves skills, agents, and rules in place.

## Optional Hindsight local memory

Hindsight is optional and machine-global. On a terminal, when neither
`~/.hindsight/embed` nor `~/.hindsight/config.env` exists, the installer asks
which LLM provider to use. The choices are the providers Hindsight 0.8 accepts,
including `none` (no LLM). Any choice other than `none` then asks for the
model (optional; Enter uses the provider default), an API key (required except
for `ollama`, `lmstudio`, `llamacpp`, and `vertexai`), and a base URL
(optional; Enter leaves it empty). Native providers do not need a base URL; an
OpenAI-compatible gateway is `openai` plus that URL. An existing
`~/.hindsight/embed` or `~/.hindsight/config.env` is never overwritten.

With no terminal, the installer does not ask. It seeds from the environment or
this checkout's `.env`. Never commit secrets. After a successful seed it still
installs the pinned Hindsight CLI.

```bash
uv tool install "hindsight-embed@$(tr -d '[:space:]' < ~/.config/mash/hindsight-pin)" \
  --with "hindsight-api@$(tr -d '[:space:]' < ~/.config/mash/hindsight-pin)"
```

### Pointing Hindsight at an OpenAI-compatible gateway

Hindsight has no generic gateway provider. Use `openai` plus a base URL, for
example OmniRoute:

```dotenv
HINDSIGHT_API_LLM_PROVIDER=openai
HINDSIGHT_API_LLM_MODEL=omniroute-hindsight
HINDSIGHT_API_LLM_API_KEY=<gateway key>
HINDSIGHT_API_LLM_BASE_URL=https://assistant.fundere.app/v1
```

Enter those four values at the prompts, or set them in `.env` for an
unattended install, and re-run `install.sh` on an unconfigured machine.
Existing `~/.hindsight/embed` files are never overwritten, so a machine
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
  `~/.config/mash/hindsight-pin`. The embed installs that binary from a vendor
  installer outside the `uv` pin and only when it is missing, so a stale binary
  would otherwise never upgrade.
- Health checks must not rely on `hindsight-embed daemon status` alone: it is a
  bare `GET /health == 200`, so any service on the port looks like a running
  daemon. The Mash Programming Skills hook and `install.sh` require the `/version` fingerprint
  (`api_version`) instead.
- Seeding never writes an active empty assignment. Hindsight parses integer
  settings with `int(os.getenv(KEY, default))` and the embed forwards every
  `HINDSIGHT_*` profile key into the daemon environment, so `KEY=` (set but
  empty) would abort daemon startup with `ValueError`.

Warm-start locations are:

- Cursor: `~/.cursor/hooks/ensure-hindsight-daemon.sh` via user `hooks.json`
- OpenCode: native plugin under `~/.config/opencode/plugin/`
- Pi: global extension and `~/.pi/agent/scripts/ensure-hindsight-daemon.sh`

Routine Mash Programming Skills commands use `hindsight-embed` with
`PATH="${HOME}/.local/bin:${PATH}"`. See
`src/skills/mash-hindsight/SKILL.md` for the full Hindsight contract.

## Repository files

Mash Programming Skills does not generate repository guidance or scaffolding. If a project needs
project-specific instructions, its owner may create and track `AGENTS.md`.
`DESIGN.md` is owned by the user or by whichever repository installs a
design-to-code pipeline. Skills create `.mash/plans/`, `.mash/insights/`,
`.mash/qa/`, and other working paths only when invoked.
