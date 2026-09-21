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
2. Creates and populates the `.cursor/rules` and `.cursor/skills` folders in your target repository, plus per-IDE skill/agent trees for VS Code/Copilot (`.github/…`), OpenCode (`.opencode/…`), and Pi (`.pi/…`).
3. Keeps Rosey-local artifacts out of version control by appending a marked block once to your **global** git excludes file (resolved from `git config --global core.excludesFile`, falling back to `$XDG_CONFIG_HOME/git/ignore` or `~/.config/git/ignore`): `.cursor/`, `.opencode/`, `.pi/`, `rosey/…`, `AGENTS.md`, `.cursorrules`, `DESIGN.md`, `.agents/`, plus the `.github/…`, `.vscode/mcp.json`, and `opencode.json` Rosey paths. It no longer edits per-repository `.gitignore` files.
4. Creates `rosey/agentic-env.json` so orchestrators can detect the installed version.
5. Always writes agent guidance (overwrites on each install unless `--no-agents`):
   - Default: minimal `AGENTS.md` with IDE-conditional paths for Cursor (`.cursor/…`), VS Code / Copilot (`.github/…`, `.vscode/…`), OpenCode (`.opencode/…`), and Pi (`.pi/…`).
   - Agent-home targets (folder basename `.hermes`, `.openclaw`, `rudi-hermes`, or `winston-openclaw`): writes `.cursorrules` instead of `AGENTS.md` (does not delete an existing `AGENTS.md`).
   - Always-on Cursor rules (`alwaysApply: true`) are distributed per IDE: `.github/copilot-instructions.md` (VS Code/Copilot), `.opencode/rules/*.mdc` (OpenCode, via the `opencode-cursor-rules` plugin), and `.pi/APPEND_SYSTEM.md` (Pi, project-local). Cursor paths inside each are rewritten to that IDE's native paths.
   Neither file stores preferences.
6. Seeds `rosey-design-candidates` skill `.env` from `.env.example` using `CURSOR_API_KEY` in `rosey-agentic-env/.env` (never overwrites an existing skill `.env`).
7. Seeds MCP configs from `.cursor/mcp.json.example`, substituting `GITHUB_TOKEN` and `OBSIDIAN_API_KEY` from `rosey-agentic-env/.env`: `.cursor/mcp.json` (Cursor), `.vscode/mcp.json` (VS Code), `.opencode/mcp.json` (OpenCode, `mcp.servers` with `type: local|remote`), and `.pi/settings.json` (Pi, `mcp.servers` merged into existing settings). The example is tracked; seeded files stay local (gitignored).
8. Installs machine-once host CLIs when missing (macOS, Debian/Ubuntu, Windows WSL): git, make, curl, rsync, jq, rg, gh, uv, gitchangelog, bumpversion, git-flow, Sentrux, and Hindsight. Skips any command already on PATH. Linux/WSL uses apt only (not Homebrew). jq, rg, and gh are GitHub release binaries, not distro packages. In each target git repo: `git flow init -d` when git-flow is not initialized (skipped on live-homes), and local `user.signingkey` from global config or the sole GPG secret key. Prints an inventory of tools it does not install (Docker, GPG, …).
9. Installs the Pi extensions once when the `pi` CLI is present: `pi-subagents` (`pi install npm:pi-subagents`), `pi-mcp-adapter` (`pi install npm:pi-mcp-adapter`), and `pi-ask-user` (`pi install npm:pi-ask-user`). Skipped if `pi` is absent or each extension is already installed. `pi-subagents` enables the `.pi/agents/` tree.

## Updating the environment
To update the rules and skills in a target repository, simply run the install command again. It will overwrite the `.cursor` files with the latest versions from the remote repository.

## Orchestration flags

- `--version`: print the agentic environment version.
- `--check`: verify `.cursor/`, `.opencode/`, `.pi/`, `rosey/agentic-env.json`, and `AGENTS.md` (or `.cursorrules` on agent-home targets) exist in the target.
- `--write-pin` / `--no-write-pin`: enable or disable writing `rosey/agentic-env.json`.
- `--agents` / `--no-agents`: enable or disable writing `AGENTS.md` / `.cursorrules` (default: always overwrite).

## Uninstalling

`uninstall.sh` reverses `install.sh` for a single repository. It is a **dry run by default**:

```bash
./uninstall.sh                 # print the plan, change nothing
./uninstall.sh --apply         # remove repo-local Rosey artifacts
./uninstall.sh --check         # exit 0 if installed, 1 if not
```

It removes the Rosey-owned trees (`.cursor/rules|skills|agents|hooks`, `.github/copilot-instructions.md`, `.github/{instructions,skills,agents,hooks}`, `.opencode/…`, `.pi/…`, `.agents/shared`, `rosey/agentic-env.json`, `rosey/hindsight-pin`) and surgically edits the shared files it touched: only the Rosey task is dropped from `.vscode/tasks.json` and only the seeded `mcp`/plugin entries from `opencode.json`. Per-repo `.gitignore` and the global excludes file are left untouched. `AGENTS.md` / `.cursorrules` are removed only when they still match what the installer wrote; appended user content makes them be kept (with a warning).

Machine-wide tools (`uv`, `bun`, `jq`, `rg`, `gh`, git-flow, Sentrux, uv tools, Pi extensions, `hindsight-embed`), user data under `rosey/` (plans, insights, solutions, …), and `~/.hindsight` are **never touched** — uninstall is repo-local by design. Remaining flags:

- `--targets=cursor,vscode,opencode,pi` — limit to some IDE trees.
- `--purge-git-config` — unset the repo-local `user.signingkey` set by the installer (branches are never deleted; requires `--apply --yes`).
- `--force` — remove generated files even when user-modified.
- `--yes` — confirm repo-local git-config changes.

## Bulk operations (`install.list`)

`install.list` holds one repository path per line (`#` comments and blank lines allowed). `bulk-install.sh` and `bulk-uninstall.sh` loop over it, forwarding every argument to `install.sh` / `uninstall.sh` and skipping entries whose directory is missing (unmounted volume, deleted folder):

```bash
./bulk-install.sh --check
./bulk-install.sh --write-pin --agents
./bulk-uninstall.sh                 # dry run across every repo
./bulk-uninstall.sh --check         # installed / not-installed report
./bulk-uninstall.sh --apply --yes   # bulk --apply refuses to run without --yes
```

Set `INSTALL_LIST` to use a different list file.

## Optional: Hindsight local memory

Rosey can use [Hindsight](https://github.com/hindsight/hindsight) for cross-session memory via the `hindsight-embed` CLI (not MCP). This is optional.

1. Install [uv](https://docs.astral.sh/uv/) if needed.
2. Put the keys listed in `.cursor/hindsight-embed.example` in `rosey-agentic-env/.env` (or the environment). Typical keys: `HINDSIGHT_API_LLM_*`, `HINDSIGHT_EMBED_BANK_ID`, `HINDSIGHT_EMBED_DAEMON_IDLE_TIMEOUT`. Never commit secrets.
3. Run `install.sh` in a target repository. When no `~/.hindsight/embed` exists yet, the installer seeds it from `.cursor/hindsight-embed.example` (every `KEY=` filled from that `.env`), then installs the CLI **once per machine** if `hindsight-embed --help` does not already respond:

   ```bash
   pin="$(tr -d '[:space:]' < .cursor/hindsight-pin)"
   uv tool install "hindsight-embed==${pin}" --with "hindsight-api==${pin}"
   ```

   The first install may take 30–60+ minutes while large dependencies download. Later `install.sh` / `bulk-install.sh` runs skip the tool install when the CLI already responds. Daemon warm-start is left to IDE hooks after the first install.

   Fallback without a key: interactive `uvx "hindsight-embed@${pin}" configure`, then re-run `install.sh`.

   Sentrux, git-flow, bumpversion, gitchangelog, and the other host CLIs are also installed only when their commands do not already respond.

4. Warm-start the daemon when the IDE opens:

   - **Cursor:** `.cursor/hooks/ensure-hindsight-daemon.sh` on `sessionStart` (via `.cursor/hooks.json`)
   - **VS Code:** the same script under `.github/hooks/`, via a `.vscode/tasks.json` task with `"runOn": "folderOpen"` (Copilot has no session-start hooks). Allow automatic tasks once: **Tasks: Manage Automatic Tasks**
   - **OpenCode:** `.opencode/hooks/ensure-hindsight-daemon.sh` on `SessionStart` (via `.opencode/hooks.json` and the `@monks1975/opencode-agent-hooks` plugin in `opencode.json`)
   - **Pi:** `.pi/scripts/ensure-hindsight-daemon.sh` on `session_start` (via `.pi/extensions/rosey-hindsight-daemon.ts`)

Routine agent commands use `hindsight-embed` with `PATH="${HOME}/.local/bin:${PATH}"`. See `.cursor/skills/rosey-hindsight/SKILL.md` for the full contract.