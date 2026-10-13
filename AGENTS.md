# Mash Programming Skills Agent Guidance

This repository is the canonical Mash Programming Skills source. The installer
is machine-global: it distributes Mash Programming Skills-owned artifacts to the global Cursor,
OpenCode, and Pi homes and never writes IDE trees or guidance into target
repositories.

## Supported IDEs

### Cursor

For work in this source repository, follow the rules in `src/rules/*.mdc`.
All eight are `alwaysApply: true`: `browser-desktop-automation`, `caveman`,
`docker-via-make`, `gitchangelog-commits`, `hindsight-memory`, `ponytail`,
`mash-workflow-gates`, and `save-insights`. `src/skills/` and `src/agents/` are the canonical source
trees. The installer copies them to `~/.cursor/rules/`, `~/.cursor/skills/`,
and `~/.cursor/agents/`; Cursor loads those installed paths.

### OpenCode

OpenCode receives global Mash Programming Skills guidance through its `config.instructions[]`
entry pointing to `~/.config/mash/AGENTS.md`. It receives global skills and
agents under `~/.config/opencode/`. Do not expect a repository-local
`.opencode/` tree to be installed by Mash Programming Skills.

### Pi

Pi receives global Mash Programming Skills context at `~/.pi/agent/AGENTS.md`, skills at
`~/.pi/agent/skills/`, and subagents at `~/.agents/`. The local `src/`
trees remain canonical source files in this repository.

Mash Programming Skills distributes to Cursor, OpenCode, and Pi only. These three are the
supported targets; do not add install paths for others.

### Naming skills across IDEs

Invocation syntax differs per IDE (Cursor `/name`, Pi `/skill:name`, OpenCode
has no slash surface). A rule or skill is copied verbatim to every IDE, so any
slash form would be wrong in at least two of them. Name skills in **prose**
("invoke the mash-plan skill"). The only slash syntax in the corpus is the
reference table in `README.md`.

## Global state

| Store | Path | What it holds |
|---|---|---|
| Curated insights | `.mash/insights/*.md` | Durable repository lessons |
| Curated solutions | `.mash/solutions/` | Institutional how-tos |
| Global Mash Programming Skills state | `~/.config/mash/` | Guidance, pins, and contract references |
| Skill runtime deps | `~/.config/mash/node_modules/`, `~/.config/mash/venvs/` | Per-skill npm store and virtualenv, symlinked into each IDE home |
| Hindsight memory | Hindsight (`hindsight-embed`) | Cross-session memory |

The two contract references (`model-tiers.md`, `markdown-rendering.md`) are
sourced from `references/` in this repo and installed at
`~/.config/mash/references/`. The source nests `model-tiers` one level deep
(`references/model-tiers/model-tiers.md`); the installer flattens it on copy,
which is why consumers reference the flat global path. Do not restore
repo-relative `.agents/shared/references/` links in global skills, and do not
host reference documentation under `.agents/` here.

Always-on rules are sourced from `src/rules/*.mdc` with `alwaysApply: true`.
The installer copies them to `~/.cursor/rules/`, where Cursor reads them
natively, and also emits them as one
frontmatter-stripped bundle at `~/.config/mash/always-on-rules.md`, referenced by
OpenCode `config.instructions[]` and copied to Pi as
`~/.pi/agent/APPEND_SYSTEM.md`. Do not hand-edit the bundle — regenerate it by
re-running `install.sh`.

Skill dependencies are installed once and shared. A skill's `package.json` drives
an npm install into `~/.config/mash/node_modules/<skill>/`; its
`requirements.txt` drives a virtualenv at `~/.config/mash/venvs/<skill>/`. Each
IDE's copy of the skill gets a symlink to the shared store, so the documented
`node_modules/` and `.venv/bin/python` paths keep working without installing
dependencies three times. Never commit a real `.venv/` or `node_modules/` under
`src/skills/`.

The install manifest records every Mash Programming Skills-owned skill, agent, rule, shared
dependency store, and MCP server name. On the next install, entries owned by the previous manifest
but absent from the current source tree are pruned from all IDE homes. Install copies
`uninstall.sh` to `~/.config/mash/uninstall.sh`. That copy reads the manifest and uninstalls
without the source checkout, so a deleted or renamed source artifact remains uninstallable
without touching unrelated user entries.

The shared *library* references (domain, strategy, and engineering library) are
not hosted here. They live only in the repository whose skills consume them —
`founders-lounge/.agents/shared/references/` — because no other scoped repo links
them. Do not re-add the library to this source repo: pi-subagents scans
everything under `<repo>/.agents/` recursively as project agent definitions, so
non-agent documentation there is a latent phantom-agent hazard.

## Scope: what Mash Programming Skills does not own

Mash Programming Skills ships planning, implementation, review, and release skills. It does **not**
ship a design-to-code pipeline. That pipeline lives in the sibling repository
`mash-design-skills`. The two packs share `~/.config/mash/` and the three IDE
homes, and they keep separate manifests: this repo writes `install-manifest.json`,
and mash-design-skills writes `design-install-manifest.json`. Design skills write
`.mash/designs/` and `.mash/design-system/` in the app. Do not reintroduce design
skills, design agents, or design paths here.

Personal, site-specific, or single-repository skills also do not belong in this
source tree. They live in their owning repository's local (untracked) skill
tree.

## Why `.pi/` exists here

`.pi/.gitkeep` is a deliberate project-root marker — do not delete it. Pi's
subagent discovery treats a directory as a project root only when it contains
`.pi/` or `.agents/`. Without it, this repo stops qualifying, so Pi walks up to
`$HOME` (which has both), resolves the project root to `$HOME`, and loads
`~/.agents/*.md` a second time as *project* agents while reading
`~/.pi/agent/settings.json` as *project* settings. A bare `.pi/` directory is
enough, and Pi's docs confirm it does not trigger the project-trust prompt.

## Hindsight

Hindsight is consulted only when a gated skill is active. The hindsight-memory
rule owns that list and is authoritative. If the daemon is unavailable,
continue and record `Hindsight: unavailable`. Do not store secrets in Hindsight
or insight files.

The global Hindsight pin is `~/.config/mash/hindsight-pin`. The installer and
IDE warm-start hooks use that pin; repository-local Hindsight pin files are
legacy and must not be recreated.
