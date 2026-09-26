# Rosey Agent Guidance

This repository is the canonical Rosey Agentic Environment source. The installer
is machine-global: it distributes Rosey-owned artifacts to the global Cursor,
OpenCode, and Pi homes and never writes IDE trees or guidance into target
repositories.

## Supported IDEs

### Cursor

For work in this source repository, follow the local source rules in
`.cursor/rules/*.mdc`. All seven are `alwaysApply: true`:
`caveman`, `docker-via-make`, `gitchangelog-commits`, `hindsight-memory`,
`ponytail`, `rosey-workflow-gates`, and `save-insights`.

Use `.cursor/skills/` and `.cursor/agents/` as the canonical source trees.

### OpenCode

OpenCode receives global Rosey guidance through its `config.instructions[]`
entry pointing to `~/.config/rosey/AGENTS.md`. It receives global skills and
agents under `~/.config/opencode/`. Do not expect a repository-local
`.opencode/` tree to be installed by Rosey.

### Pi

Pi receives global Rosey context at `~/.pi/agent/AGENTS.md`, skills at
`~/.pi/agent/skills/`, and subagents at `~/.agents/`. The local `.cursor/`
trees remain canonical source files in this repository.

Rosey distributes to Cursor, OpenCode, and Pi only. These three are the
supported targets; do not add install paths for others.

### Naming skills across IDEs

Invocation syntax differs per IDE (Cursor `/name`, Pi `/skill:name`, OpenCode
has no slash surface). A rule or skill is copied verbatim to every IDE, so any
slash form would be wrong in at least two of them. Name skills in **prose**
("invoke the rosey-plan skill"). The only slash syntax in the corpus is the
reference table in `README.md`.

## Global state

| Store | Path | What it holds |
|---|---|---|
| Curated insights | `rosey/insights/*.md` | Durable repository lessons |
| Curated solutions | `rosey/solutions/` | Institutional how-tos |
| Global Rosey state | `~/.config/rosey/` | Guidance, pins, and contract references |
| Skill runtime deps | `~/.config/rosey/node_modules/`, `~/.config/rosey/venvs/` | Per-skill npm store and virtualenv, symlinked into each IDE home |
| Hindsight memory | Hindsight (`hindsight-embed`) | Cross-session memory |

The three contract references (`model-tiers.md`, `scoping-synthesis.md`,
`markdown-rendering.md`) are sourced from `references/` in this repo and
installed at `~/.config/rosey/references/`. The source nests two of them one
level deep (`references/model-tiers/model-tiers.md`); the installer flattens
them on copy, which is why consumers reference the flat global path. Do not
restore repo-relative `.agents/shared/references/` links in global skills, and
do not host reference documentation under `.agents/` here.

Always-on rules are sourced from `.cursor/rules/*.mdc` with `alwaysApply: true`.
Cursor reads those natively; the installer also emits them as one
frontmatter-stripped bundle at `~/.config/rosey/always-on-rules.md`, referenced by
OpenCode `config.instructions[]` and copied to Pi as
`~/.pi/agent/APPEND_SYSTEM.md`. Do not hand-edit the bundle — regenerate it by
re-running `install.sh`.

Skill dependencies are installed once and shared. A skill's `package.json` drives
an npm install into `~/.config/rosey/node_modules/<skill>/`; its
`requirements.txt` drives a virtualenv at `~/.config/rosey/venvs/<skill>/`. Each
IDE's copy of the skill gets a symlink to the shared store, so the documented
`node_modules/` and `.venv/bin/python` paths keep working without installing
dependencies three times. Never commit a real `.venv/` or `node_modules/` under
`.cursor/skills/`.

The installer copies in but never prunes. A skill removed from this source tree
stays behind in `~/.cursor/skills/`, `~/.config/opencode/skills/`, and
`~/.pi/agent/skills/` (agents likewise in `~/.cursor/agents/`, `~/.agents/`, and
`~/.config/opencode/agents/`), and its shared dependency store under
`~/.config/rosey/node_modules/` and `~/.config/rosey/venvs/` also persists.
After deleting or relocating a skill, remove those installed copies explicitly
or the IDEs keep offering it.

The shared *library* references (domain, strategy, and engineering library) are
not hosted here. They live only in the repository whose skills consume them —
`founders-lounge/.agents/shared/references/` — because no other scoped repo links
them. Do not re-add the library to this source repo: pi-subagents scans
everything under `<repo>/.agents/` recursively as project agent definitions, so
non-agent documentation there is a latent phantom-agent hazard.

## Scope: what Rosey does not own

Rosey ships planning, implementation, review, and release skills. It does **not**
ship a design-to-code pipeline. Design skills, their `DESIGN.md`, and
`rosey/designs/` artifacts belong to whichever repository installs them. Do not
reintroduce design skills, design agents, or design paths here.

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

Hindsight is consulted only when `/rosey-brainstorm`, `/rosey-plan`,
`/rosey-work`, or `/rosey-qa` is active. If the daemon is unavailable,
continue and record `Hindsight: unavailable`. Do not store secrets in Hindsight
or insight files.

The global Hindsight pin is `~/.config/rosey/hindsight-pin`. The installer and
IDE warm-start hooks use that pin; repository-local Hindsight pin files are
legacy and must not be recreated.
