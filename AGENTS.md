# Rosey Agent Guidance

This repository is the canonical Rosey Agentic Environment source. The installer
is machine-global: it distributes Rosey-owned artifacts to the global Cursor,
OpenCode, and Pi homes and never writes IDE trees or guidance into target
repositories.

## Supported IDEs

### Cursor

For work in this source repository, follow the local source rules in:

- `.cursor/rules/rosey-workflow-gates.mdc`
- `.cursor/rules/hindsight-memory.mdc`
- `.cursor/rules/ponytail.mdc`
- `.cursor/rules/save-insights.mdc`

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

VS Code / GitHub Copilot distribution is not supported.

## Global state

| Store | Path | What it holds |
|---|---|---|
| Curated insights | `rosey/insights/*.md` | Durable repository lessons |
| Curated solutions | `rosey/solutions/` | Institutional how-tos |
| Global Rosey state | `~/.config/rosey/` | Guidance, pins, and contract references |
| Hindsight memory | Hindsight (`hindsight-embed`) | Cross-session memory |

The shared contract references are installed at
`~/.config/rosey/references/`. Do not restore repo-relative
`.agents/shared/references/` links in global skills.

## Hindsight

Hindsight is consulted only when `/rosey-brainstorm`, `/rosey-plan`,
`/rosey-work`, or `/rosey-qa` is active. If the daemon is unavailable,
continue and record `Hindsight: unavailable`. Do not store secrets in Hindsight
or insight files.

The global Hindsight pin is `~/.config/rosey/hindsight-pin`. The installer and
IDE warm-start hooks use that pin; repository-local Hindsight pin files are
legacy and must not be recreated.
