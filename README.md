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
5. Always writes a minimal `AGENTS.md` (overwrites on each install unless `--no-agents`). It does not store preferences; it gives IDE-conditional paths for Cursor (`.cursor/…`) and VS Code / Copilot (`.github/…`, `.vscode/…`).

## Updating the environment
To update the rules and skills in a target repository, simply run the install command again. It will overwrite the `.cursor` files with the latest versions from the remote repository.

## Orchestration flags

- `--version`: print the agentic environment version.
- `--check`: verify `.cursor/`, `rosey/agentic-env.json`, and `AGENTS.md` exist in the target repo.
- `--write-pin` / `--no-write-pin`: enable or disable writing `rosey/agentic-env.json`.
- `--agents` / `--no-agents`: enable or disable writing `AGENTS.md` (default: always overwrite).

## Optional: Hindsight local memory

Rosey can use [Hindsight](https://github.com/hindsight/hindsight) for cross-session memory via the `hindsight-embed` CLI (not MCP). This is optional.

1. Install [uv](https://docs.astral.sh/uv/) if needed.
2. Run interactive setup once (use the pin from `.cursor/hindsight-pin`):

   ```bash
   pin="$(tr -d '[:space:]' < .cursor/hindsight-pin)"
   uvx "hindsight-embed@${pin}" configure
   ```

3. Re-run `install.sh` in your target repository. When Hindsight is configured, the installer runs (same pin file):

   ```bash
   pin="$(tr -d '[:space:]' < .cursor/hindsight-pin)"
   uv tool install "hindsight-embed==${pin}" --with "hindsight-api==${pin}"
   ```

   The first install may take 30–60+ minutes while large dependencies download. Subsequent installs are fast.

4. On each Cursor session, `.cursor/hooks/ensure-hindsight-daemon.sh` performs a fast daemon health check and warm restart via the installed `hindsight-embed` binary.

Routine agent commands use `hindsight-embed` with `PATH="${HOME}/.local/bin:${PATH}"`. See `.cursor/skills/rosey-hindsight/SKILL.md` for the full contract.