# Rosey Agentic Environment

This is a standalone, portable Agentic Environment for Cursor, containing rules, skills, and MCP configurations.

It's designed to be injected directly into target application repositories so they gain the intelligence of the Rosey agents, with the agentic environment and application code sharing the same workspace root.

## Installation into a target repository

To scaffold this environment into any project, simply run the installation script in the root directory of your target repository:

```bash
curl -sSL https://raw.githubusercontent.com/LuisAlejandro/rosey-agentic-env/main/install.sh | bash
```

*Note: Update the URL above to point to the raw location of the `install.sh` file in your actual remote repository.*

For local orchestration from `rosey-maintainer-tools`, run from the target repository root:

```bash
ROSEY_AGENTIC_ENV=/Users/luisalejandro/Development/rosey-agentic-env \
  bash /Users/luisalejandro/Development/rosey-agentic-env/install.sh --write-pin --agents
```

### What the installer does:
1. Downloads the latest rules and skills from this repository.
2. Creates and populates the `.cursor/rules` and `.cursor/skills` folders in your target repository.
3. Automatically updates your `.gitignore` to keep Rosey-local artifacts out of version control: `.cursor/`, `rosey/brainstorms/`, `rosey/plans/`, `rosey/designs/`, `rosey/solutions/`, `rosey/insights/`, `rosey/design-system/`, `rosey/qa/`, `rosey/deepening/`, `rosey/agentic-env.json`, and `rosey/maintainer-manifest.json`.
4. Creates `rosey/agentic-env.json` so orchestrators can detect the installed version.
5. Always writes agent guidance (overwrites on each install unless `--no-agents`):
   - Default: minimal `AGENTS.md` with IDE-conditional paths for Cursor (`.cursor/…`) and VS Code / Copilot (`.github/…`, `.vscode/…`).
   - Agent-home targets (folder basename `.hermes`, `.openclaw`, `rosey-hermes`, `rosey-openclaw`, or `winston-openclaw`): writes `.cursorrules` instead of `AGENTS.md` (does not delete an existing `AGENTS.md`).
   Neither file stores preferences.
6. Seeds `rosey-design-candidates` skill `.env` from `.env.example` using `CURSOR_API_KEY` in `rosey-agentic-env/.env` (never overwrites an existing skill `.env`).
7. Seeds `.cursor/mcp.json` and `.vscode/mcp.json` from `.cursor/mcp.json.example`, substituting `GITHUB_TOKEN` and `OBSIDIAN_API_KEY` from `rosey-agentic-env/.env`. The example is tracked; seeded `mcp.json` files stay local (gitignored under `.cursor/` / `.vscode/mcp.json`).

## Updating the environment
To update the rules and skills in a target repository, simply run the install command again. It will overwrite the `.cursor` files with the latest versions from the remote repository.

## Orchestration flags

- `--version`: print the agentic environment version.
- `--check`: verify `.cursor/`, `rosey/agentic-env.json`, and `AGENTS.md` (or `.cursorrules` on agent-home targets) exist in the target.
- `--write-pin` / `--no-write-pin`: enable or disable writing `rosey/agentic-env.json`.
- `--agents` / `--no-agents`: enable or disable writing `AGENTS.md` / `.cursorrules` (default: always overwrite).

## Optional: Hindsight local memory

Rosey can use [Hindsight](https://github.com/hindsight/hindsight) for cross-session memory via the `hindsight-embed` CLI (not MCP). This is optional.

1. Install [uv](https://docs.astral.sh/uv/) if needed.
2. Put the keys listed in `.cursor/hindsight-embed.example` in `rosey-agentic-env/.env` (or the environment). Typical keys: `HINDSIGHT_API_LLM_*`, `HINDSIGHT_EMBED_BANK_ID`, `HINDSIGHT_EMBED_DAEMON_IDLE_TIMEOUT`. Never commit secrets.
3. Run `install.sh` in a target repository. When no `~/.hindsight/embed` exists yet, the installer seeds it from `.cursor/hindsight-embed.example` (every `KEY=` filled from that `.env`), then installs the CLI **once per machine** if `hindsight-embed --help` does not already respond:

   ```bash
   pin="$(tr -d '[:space:]' < .cursor/hindsight-pin)"
   uv tool install "hindsight-embed==${pin}" --with "hindsight-api==${pin}"
   ```

   The first install may take 30–60+ minutes while large dependencies download. Later `install.sh` / `autoinstall.sh` runs skip the tool install when the CLI already responds. Daemon warm-start is left to IDE hooks after the first install.

   Fallback without a key: interactive `uvx "hindsight-embed@${pin}" configure`, then re-run `install.sh`.

   Sentrux is also installed only when `sentrux --version` does not already respond.

4. Warm-start the daemon when the IDE opens:

   - **Cursor:** `.cursor/hooks/ensure-hindsight-daemon.sh` on `sessionStart` (via `.cursor/hooks.json`)
   - **VS Code:** the same script under `.github/hooks/`, via a `.vscode/tasks.json` task with `"runOn": "folderOpen"` (Copilot has no session-start hooks). Allow automatic tasks once: **Tasks: Manage Automatic Tasks**

Routine agent commands use `hindsight-embed` with `PATH="${HOME}/.local/bin:${PATH}"`. See `.cursor/skills/rosey-hindsight/SKILL.md` for the full contract.