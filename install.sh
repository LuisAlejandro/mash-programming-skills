#!/usr/bin/env bash
set -euo pipefail

# Rosey Agentic Environment — machine-global installer.
# This installer intentionally never writes into the current repository.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="${ROSEY_AGENTIC_ENV:-$SCRIPT_DIR}"
VERSION_FILE="$SOURCE_ROOT/VERSION"
INSTALL_VERSION="0.1.0"
CHECK_ONLY=false
WRITE_PIN=true
WRITE_GUIDANCE=true

# Global destinations are machine-owned. Keep the Rosey state root distinct from
# each IDE's own global directory so OpenCode can consume the same guidance and
# reference contracts without shadowing project AGENTS.md files.
ROSEY_CONFIG_DIR="${HOME}/.config/rosey"
CURSOR_HOME="${HOME}/.cursor"
PI_HOME="${HOME}/.pi/agent"
OPENCODE_HOME="${HOME}/.config/opencode"
PI_SHARED_MCP="${HOME}/.config/mcp/mcp.json"
HINDSIGHT_CLI_INSTALLER_URL="https://hindsight.vectorize.io/get-cli"

if [ -f "$VERSION_FILE" ]; then
    INSTALL_VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"
fi

while [ "$#" -gt 0 ]; do
    case "$1" in
        --version)
            echo "$INSTALL_VERSION"
            exit 0
            ;;
        --check)
            CHECK_ONLY=true
            shift
            ;;
        --write-pin)
            WRITE_PIN=true
            shift
            ;;
        --no-write-pin)
            WRITE_PIN=false
            shift
            ;;
        --agents | --guidance)
            WRITE_GUIDANCE=true
            shift
            ;;
        --no-agents | --no-guidance)
            WRITE_GUIDANCE=false
            shift
            ;;
        -h | --help)
            cat <<'EOF'
Usage: install.sh [--check] [--version] [--write-pin|--no-write-pin]
                  [--agents|--no-agents]

Installs Rosey globally for Cursor, OpenCode, and Pi. It never writes to the
current repository. Repository AGENTS.md, DESIGN.md, IDE trees, .mcp.json, and
rosey/* files are not created by this command.
EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

if [ ! -d "$SOURCE_ROOT/.cursor" ]; then
    echo "Error: Could not find .cursor directory in $SOURCE_ROOT" >&2
    echo "   Run this script from the rosey-agentic-env repository or set ROSEY_AGENTIC_ENV." >&2
    exit 1
fi

# Extract frontmatter fields from Cursor .mdc files.
fm_field() {
    local file="$1" field="$2"
    sed -n "/^${field}:[[:space:]]*/{ s/^${field}:[[:space:]]*//; s/^[\"']//; s/[\"']$//; p; q; }" "$file" 2>/dev/null
}

fm_always_apply() {
    grep -qE '^alwaysApply:[[:space:]]*true' "$1" 2>/dev/null
}

# Read KEY=value from a dotenv-style file (last match). Strips optional quotes.
rosey_dotenv_get() {
    local file="$1" key="$2" line val
    [ -f "$file" ] || return 1
    line="$(grep -E "^[[:space:]]*${key}=" "$file" 2>/dev/null | tail -n1)" || return 1
    [ -n "$line" ] || return 1
    val="${line#*=}"
    val="${val%$'\r'}"
    if [[ "$val" =~ ^\".*\"$ ]]; then
        val="${val:1:${#val}-2}"
    elif [[ "$val" =~ ^\'.*\'$ ]]; then
        val="${val:1:${#val}-2}"
    fi
    printf '%s' "$val"
}

# Resolve KEY: process environment, then the source repository's .env.
# The installer has no repository target, so it never reads a target .env.
rosey_resolve_env_value() {
    local key="$1" val=""
    if [ -n "${!key+x}" ] && [ -n "${!key}" ]; then
        printf '%s' "${!key}"
        return 0
    fi
    val="$(rosey_dotenv_get "$SOURCE_ROOT/.env" "$key" 2>/dev/null || true)"
    printf '%s' "$val"
}

seed_dotenv_from_example() {
    local example="$1" dest="$2" required_key="${3:-}"
    local line key val missing=0

    [ -f "$dest" ] && return 0
    [ -f "$example" ] || return 1

    mkdir -p "$(dirname "$dest")"
    {
        echo "# Seeded by Rosey install.sh from $(basename "$example") at $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
        while IFS= read -r line || [ -n "$line" ]; do
            if [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]]; then
                printf '%s\n' "$line"
                continue
            fi
            if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)= ]]; then
                key="${BASH_REMATCH[1]}"
                val="$(rosey_resolve_env_value "$key")"
                if [ -n "$val" ]; then
                    printf '%s=%s\n' "$key" "$val"
                else
                    # Never emit an active empty assignment. Hindsight reads integer
                    # settings with a bare int(os.getenv(KEY, default)), and the embed
                    # propagates every HINDSIGHT_* profile key into the daemon env, so
                    # `KEY=` (set but empty) raises ValueError at daemon start.
                    printf '# %s=\n' "$key"
                fi
                if [ -n "$required_key" ] && [ "$key" = "$required_key" ] && [ -z "$val" ]; then
                    missing=1
                fi
            else
                printf '%s\n' "$line"
            fi
        done <"$example"
    } >"$dest"
    chmod 600 "$dest"

    if [ "$missing" -eq 1 ]; then
        rm -f "$dest"
        return 1
    fi
}

copy_tree_without_runtime() {
    local src="$1" dest="$2"
    rm -rf "$dest"
    mkdir -p "$dest"
    if command -v rsync >/dev/null 2>&1; then
        rsync -a \
            --exclude 'node_modules/' \
            --exclude '.venv/' \
            --exclude '.env' \
            --exclude '__pycache__/' \
            --exclude '*.pyc' \
            "$src/" "$dest/"
    else
        cp -R "$src/." "$dest/"
        find "$dest" -type d \( -name node_modules -o -name .venv -o -name __pycache__ \) -prune -exec rm -rf {} + 2>/dev/null || true
        find "$dest" -type f \( -name '*.pyc' -o -name '.env' \) -delete 2>/dev/null || true
    fi
}

copy_owned_file() {
    local src="$1" dest="$2"
    mkdir -p "$(dirname "$dest")"
    cp "$src" "$dest"
}

adapt_agent_frontmatter() {
    local src="$1" dest="$2" mode="${3:-}"
    local in_fm=0 line
    mkdir -p "$(dirname "$dest")"
    {
        while IFS= read -r line || [ -n "$line" ]; do
            if [ "$in_fm" -eq 0 ] && [ "$line" = "---" ]; then
                in_fm=1
                printf '%s\n' "$line"
                continue
            fi
            if [ "$in_fm" -eq 1 ] && [ "$line" = "---" ]; then
                in_fm=0
                [ -n "$mode" ] && printf 'mode: %s\n' "$mode"
                printf '%s\n' "$line"
                continue
            fi
            if [ "$in_fm" -eq 1 ]; then
                case "$line" in
                    color:* | tools:* | 'model: inherit' | 'model: inherit'*)
                        continue
                        ;;
                esac
            fi
            printf '%s\n' "$line"
        done <"$src"
    } >"$dest"
}

rosey_agents_guidance() {
    cat >"$1" <<'EOF'
# Rosey Agent Guidance

This machine uses the Rosey Agentic Environment as global tooling.
This file contains universal Rosey workflow guidance only; it does not replace
project-specific instructions in a repository's own AGENTS.md.

## Global Rosey surfaces

- Cursor rules: `~/.cursor/rules/*.mdc`
- Cursor skills: `~/.cursor/skills/`
- Cursor specialist agents: `~/.cursor/agents/`
- OpenCode instructions: `~/.config/opencode/opencode.json` points to this file
- OpenCode skills: `~/.config/opencode/skills/`
- OpenCode agents: `~/.config/opencode/agents/`
- Pi context: `~/.pi/agent/AGENTS.md`
- Pi skills: `~/.pi/agent/skills/`
- Pi specialist agents: `~/.agents/`

Before non-trivial planning, implementation, or review work, follow the
always-on Rosey rules and use the relevant Rosey skill. Do not create or expect
repo-local IDE trees for Rosey distribution.

## Hindsight

Hindsight is optional and machine-global. The version pin is
`~/.config/rosey/hindsight-pin`; the shared contract references are under
`~/.config/rosey/references/`.

When `/rosey-brainstorm`, `/rosey-plan`, `/rosey-work`, or `/rosey-qa` is
active, follow the `rosey-hindsight` skill's gate. If the daemon is unavailable,
continue and record `Hindsight: unavailable`.

## Repository ownership

Rosey never writes a repository's `AGENTS.md`, `DESIGN.md`, IDE trees, MCP
files, or `rosey/*` working directories during installation. Owners may create
and track project-specific `AGENTS.md`/`DESIGN.md`; skills create their own
working directories lazily when invoked.
EOF
}

copy_global_rules() {
    local src dest name
    mkdir -p "$CURSOR_HOME/rules" "$ROSEY_CONFIG_DIR/rules"
    for src in "$SOURCE_ROOT"/.cursor/rules/*.mdc; do
        [ -f "$src" ] || continue
        name="$(basename "$src")"
        cp "$src" "$CURSOR_HOME/rules/$name"
        # Shared rule copies let global OpenCode/Pi skill scripts inspect the
        # same rule contracts even though those IDEs have different transports.
        cp "$src" "$ROSEY_CONFIG_DIR/rules/$name"
    done
}

copy_global_skills() {
    local src sname dest
    for src in "$SOURCE_ROOT"/.cursor/skills/*/; do
        [ -d "$src" ] || continue
        sname="$(basename "$src")"
        copy_tree_without_runtime "$src" "$CURSOR_HOME/skills/$sname"
        copy_tree_without_runtime "$src" "$OPENCODE_HOME/skills/$sname"
        copy_tree_without_runtime "$src" "$PI_HOME/skills/$sname"
        echo "   installed skill: $sname"
    done
}

copy_global_agents() {
    local src name out
    mkdir -p "$CURSOR_HOME/agents" "$OPENCODE_HOME/agents" "$HOME/.agents"
    for src in "$SOURCE_ROOT"/.cursor/agents/*; do
        [ -e "$src" ] || continue
        name="$(basename "$src")"
        copy_owned_file "$src" "$CURSOR_HOME/agents/$name"
        case "$name" in
            *.md)
                out="$OPENCODE_HOME/agents/$name"
                adapt_agent_frontmatter "$src" "$out" subagent
                out="$HOME/.agents/$name"
                adapt_agent_frontmatter "$src" "$out"
                ;;
            *)
                copy_owned_file "$src" "$OPENCODE_HOME/agents/$name"
                copy_owned_file "$src" "$HOME/.agents/$name"
                ;;
        esac
    done
}

copy_global_hooks() {
    local src="$SOURCE_ROOT/.cursor/hooks/ensure-hindsight-daemon.sh"
    [ -f "$src" ] || return 0
    mkdir -p "$CURSOR_HOME/hooks"
    cp "$src" "$CURSOR_HOME/hooks/ensure-hindsight-daemon.sh"
    chmod +x "$CURSOR_HOME/hooks/ensure-hindsight-daemon.sh"

    python3 - "$CURSOR_HOME/hooks.json" "$CURSOR_HOME/hooks/ensure-hindsight-daemon.sh" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
command = sys.argv[2]
try:
    data = json.loads(path.read_text()) if path.exists() else {}
except Exception:
    data = {}
if not isinstance(data, dict):
    data = {}
data.setdefault("version", 1)
hooks = data.setdefault("hooks", {})
if not isinstance(hooks, dict):
    hooks = {}
    data["hooks"] = hooks
entries = hooks.setdefault("sessionStart", [])
if not isinstance(entries, list):
    entries = []
    hooks["sessionStart"] = entries
entries = [entry for entry in entries if not (isinstance(entry, dict) and entry.get("command") == command)]
entries.append({"command": command, "timeout": 60})
hooks["sessionStart"] = entries
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(data, indent=2) + "\n")
PY
}

copy_global_pi_runtime() {
    local hook_src="$SOURCE_ROOT/.cursor/hooks/ensure-hindsight-daemon.sh"
    local ext_src="$SOURCE_ROOT/.cursor/hooks-pi/rosey-hindsight-daemon.ts"
    mkdir -p "$PI_HOME/scripts" "$PI_HOME/extensions"
    if [ -f "$hook_src" ]; then
        cp "$hook_src" "$PI_HOME/scripts/ensure-hindsight-daemon.sh"
        chmod +x "$PI_HOME/scripts/ensure-hindsight-daemon.sh"
    fi
    if [ -f "$ext_src" ]; then
        cp "$ext_src" "$PI_HOME/extensions/rosey-hindsight-daemon.ts"
    fi
}

copy_global_opencode_runtime() {
    local src="$SOURCE_ROOT/.cursor/hooks-opencode/rosey-hindsight-daemon.ts"
    [ -f "$src" ] || return 0
    mkdir -p "$OPENCODE_HOME/plugin"
    cp "$src" "$OPENCODE_HOME/plugin/rosey-hindsight-daemon.ts"
}

write_global_guidance() {
    [ "$WRITE_GUIDANCE" = true ] || return 0
    mkdir -p "$ROSEY_CONFIG_DIR" "$PI_HOME"
    rosey_agents_guidance "$ROSEY_CONFIG_DIR/AGENTS.md"
    cp "$ROSEY_CONFIG_DIR/AGENTS.md" "$PI_HOME/AGENTS.md"
}

write_global_pins() {
    [ "$WRITE_PIN" = true ] || return 0
    mkdir -p "$ROSEY_CONFIG_DIR"
    if [ -f "$SOURCE_ROOT/.cursor/hindsight-pin" ]; then
        cp "$SOURCE_ROOT/.cursor/hindsight-pin" "$ROSEY_CONFIG_DIR/hindsight-pin"
    fi
    python3 - "$ROSEY_CONFIG_DIR/agentic-env.json" "$SOURCE_ROOT" "$INSTALL_VERSION" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
data = {
    "installed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "source": sys.argv[2],
    "version": sys.argv[3],
    "scope": "global",
    "targets": ["cursor", "opencode", "pi"],
}
path.write_text(json.dumps(data, indent=2) + "\n")
PY
}

install_global_references() {
    local source dest
    mkdir -p "$ROSEY_CONFIG_DIR/references"
    for source in \
        "$SOURCE_ROOT/references/model-tiers/model-tiers.md" \
        "$SOURCE_ROOT/references/scoping-synthesis/scoping-synthesis.md" \
        "$SOURCE_ROOT/references/markdown-rendering.md"; do
        [ -f "$source" ] || {
            echo "   ⚠️  Missing contract reference: $source" >&2
            continue
        }
        dest="$ROSEY_CONFIG_DIR/references/$(basename "$source")"
        cp "$source" "$dest"
    done
}

seed_global_skill_env() {
    local example="$SOURCE_ROOT/.cursor/skills/rosey-design-candidates/.env.example"
    local root dest
    [ -f "$example" ] || return 0
    for root in "$CURSOR_HOME/skills" "$OPENCODE_HOME/skills" "$PI_HOME/skills"; do
        dest="$root/rosey-design-candidates/.env"
        [ -d "$(dirname "$dest")" ] || continue
        if [ ! -f "$dest" ]; then
            if seed_dotenv_from_example "$example" "$dest" "CURSOR_API_KEY"; then
                echo "   seeded: $dest"
            else
                echo "   ⚠️  Could not seed $dest (CURSOR_API_KEY missing)"
            fi
        fi
    done
}

merge_global_mcp() {
    local example="$SOURCE_ROOT/.cursor/mcp.json.example"
    [ -f "$example" ] || {
        echo "   ⚠️  No .cursor/mcp.json.example; skipping MCP seed"
        return 0
    }

    local github_token obsidian_key
    github_token="$(rosey_resolve_env_value GITHUB_TOKEN)"
    obsidian_key="$(rosey_resolve_env_value OBSIDIAN_API_KEY)"
    python3 - "$example" "$CURSOR_HOME/mcp.json" "$OPENCODE_HOME/opencode.json" "$PI_SHARED_MCP" "$PI_HOME/settings.json" "$github_token" "$obsidian_key" <<'PY'
import json
import sys
from pathlib import Path

example, cursor_path, opencode_path, pi_shared_path, pi_settings_path, github_token, obsidian_key = sys.argv[1:]
source = json.loads(Path(example).read_text())

def substitute(value):
    if isinstance(value, dict):
        return {k: substitute(v) for k, v in value.items()}
    if isinstance(value, list):
        return [substitute(v) for v in value]
    if isinstance(value, str):
        return value.replace("$GITHUB_TOKEN", github_token).replace("$OBSIDIAN_API_KEY", obsidian_key)
    return value

servers = substitute(source).get("mcpServers", {})
if not isinstance(servers, dict):
    servers = {}

def read_json(path):
    p = Path(path)
    try:
        value = json.loads(p.read_text()) if p.exists() else {}
    except Exception:
        value = {}
    return value if isinstance(value, dict) else {}

def write_json(path, value):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2) + "\n")
    try:
        p.chmod(0o600)
    except OSError:
        pass

# Cursor: Rosey entries overwrite same-name entries by the accepted decision.
cursor = read_json(cursor_path)
current = cursor.get("mcpServers")
if not isinstance(current, dict):
    current = {}
current.update(servers)
cursor["mcpServers"] = current
write_json(cursor_path, cursor)

# OpenCode: adapt Cursor server definitions and merge into its mcp map.
opencode_servers = {}
for name, raw in servers.items():
    srv = dict(raw) if isinstance(raw, dict) else raw
    if isinstance(srv, dict):
        srv.pop("type", None)
        if "command" in srv:
            args = srv.pop("args", [])
            cmd = srv.pop("command")
            srv["command"] = [cmd] + list(args)
            srv["type"] = "local"
        elif "url" in srv:
            srv["type"] = "remote"
    opencode_servers[name] = srv
opencode = read_json(opencode_path)
current = opencode.get("mcp")
if not isinstance(current, dict):
    current = {}
current.update(opencode_servers)
opencode["mcp"] = current
instructions = opencode.get("instructions")
if not isinstance(instructions, list):
    instructions = []
rosey_guidance = str(Path(opencode_path).parent.parent / "rosey" / "AGENTS.md")
# The installer passes the actual path separately below; retain a placeholder
# only if this helper is ever called outside install_global_payload.
if rosey_guidance not in instructions:
    pass
write_json(opencode_path, opencode)

# Standard global Pi MCP config consumed by pi-mcp-adapter.
pi_shared = read_json(pi_shared_path)
current = pi_shared.get("mcpServers")
if not isinstance(current, dict):
    current = {}
current.update(servers)
pi_shared["mcpServers"] = current
write_json(pi_shared_path, pi_shared)

# Keep the Rosey MCP map visible in Pi's machine settings as documented by the
# proposal; pi-mcp-adapter reads the standard shared config above.
pi_settings = read_json(pi_settings_path)
current = pi_settings.get("mcpServers")
if not isinstance(current, dict):
    current = {}
current.update(servers)
pi_settings["mcpServers"] = current
write_json(pi_settings_path, pi_settings)
PY

    # Add the OpenCode instructions entry in a separate pass with the exact path.
    python3 - "$OPENCODE_HOME/opencode.json" "$ROSEY_CONFIG_DIR/AGENTS.md" <<'PY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
guidance = sys.argv[2]
try:
    data = json.loads(path.read_text()) if path.exists() else {}
except Exception:
    data = {}
if not isinstance(data, dict):
    data = {}
instructions = data.get("instructions")
if not isinstance(instructions, list):
    instructions = []
if guidance not in instructions:
    instructions.append(guidance)
data["instructions"] = instructions
path.write_text(json.dumps(data, indent=2) + "\n")
PY
    chmod 600 "$OPENCODE_HOME/opencode.json" "$PI_HOME/settings.json" "$PI_SHARED_MCP" "$CURSOR_HOME/mcp.json" 2>/dev/null || true
    echo "   merged MCP configuration into Cursor, OpenCode, and Pi global files"
}

rosey_global_gitignore_path() {
    local p
    if command -v git >/dev/null 2>&1 && p="$(git config --global --get core.excludesFile 2>/dev/null)" && [ -n "$p" ]; then
        case "$p" in
            /*) ;;
            "~"/*) p="${HOME}${p#\~}" ;;
            *) p="${HOME}/${p#/}" ;;
        esac
        printf '%s\n' "$p"
        return 0
    fi
    printf '%s\n' "${HOME}/.gitignore-global"
}

rosey_global_gitignore_ensure() {
    local gf
    gf="$(rosey_global_gitignore_path)"
    mkdir -p "$(dirname "$gf")"
    python3 - "$gf" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
text = path.read_text() if path.exists() else ""
# Replace the old installer block. It was historically terminal, so retain any
# user text after a new explicit end marker and remove only known old entries.
start = text.find("# Rosey Agentic Environment\n")
if start >= 0:
    end_marker = text.find("# End Rosey Agentic Environment", start)
    if end_marker >= 0:
        end = text.find("\n", end_marker)
        end = len(text) if end < 0 else end + 1
        text = text[:start] + text[end:]
    else:
        old_entries = {
            "rosey/brainstorms/", "rosey/plans/", "rosey/designs/", "rosey/solutions/",
            "rosey/insights/", "rosey/design-system/", "rosey/qa/", "rosey/parallel/",
            "rosey/deepening/", "rosey/loops/", "rosey/ideation/", "rosey/agentic-env.json",
            "rosey/maintainer-manifest.json", "rosey/hindsight-pin", "AGENTS.md", ".cursorrules",
            "DESIGN.md", ".cursor/", ".github/copilot-instructions.md", ".github/instructions/",
            ".github/skills/", ".github/agents/", ".github/hooks/", ".vscode/mcp.json",
            "opencode.json", ".opencode/", ".pi/", ".agents/",
        }
        lines = text.splitlines(keepends=True)
        kept = []
        in_block = False
        for line in lines:
            stripped = line.rstrip("\n")
            if stripped == "# Rosey Agentic Environment":
                in_block = True
                continue
            if in_block and (stripped.startswith("# Added by rosey-agentic-env/install.sh") or stripped in old_entries or stripped == ""):
                continue
            if in_block:
                in_block = False
            kept.append(line)
        text = "".join(kept)

block = """# Rosey Agentic Environment
# Added by rosey-agentic-env/install.sh. Remove this block to stop ignoring.
rosey/brainstorms/
rosey/plans/
rosey/designs/
rosey/solutions/
rosey/insights/
rosey/design-system/
rosey/qa/
rosey/parallel/
rosey/deepening/
rosey/loops/
rosey/ideation/
rosey/maintainer-manifest.json
# End Rosey Agentic Environment
"""
text = text.rstrip() + "\n\n" + block
path.write_text(text)
PY
    echo "-> Updated global gitignore: $gf"
}

write_global_install_markers() {
    mkdir -p "$ROSEY_CONFIG_DIR"
    cat >"$ROSEY_CONFIG_DIR/install-manifest.json" <<EOF
{
  "version": "$INSTALL_VERSION",
  "source": "$SOURCE_ROOT",
  "scope": "global",
  "cursor": "$CURSOR_HOME",
  "opencode": "$OPENCODE_HOME",
  "pi": "$PI_HOME",
  "pi_agents": "$HOME/.agents",
  "rosey": "$ROSEY_CONFIG_DIR"
}
EOF
}

run_global_check() {
    local missing=0 path
    local required=(
        "$CURSOR_HOME/rules"
        "$CURSOR_HOME/skills"
        "$CURSOR_HOME/agents"
        "$CURSOR_HOME/hooks/ensure-hindsight-daemon.sh"
        "$CURSOR_HOME/hooks.json"
        "$CURSOR_HOME/mcp.json"
        "$OPENCODE_HOME/skills"
        "$OPENCODE_HOME/agents"
        "$OPENCODE_HOME/plugin/rosey-hindsight-daemon.ts"
        "$OPENCODE_HOME/opencode.json"
        "$PI_HOME/AGENTS.md"
        "$PI_HOME/skills"
        "$HOME/.agents"
        "$PI_HOME/extensions/rosey-hindsight-daemon.ts"
        "$PI_HOME/scripts/ensure-hindsight-daemon.sh"
        "$PI_SHARED_MCP"
        "$ROSEY_CONFIG_DIR/AGENTS.md"
        "$ROSEY_CONFIG_DIR/rules"
        "$ROSEY_CONFIG_DIR/references/model-tiers.md"
        "$ROSEY_CONFIG_DIR/references/scoping-synthesis.md"
        "$ROSEY_CONFIG_DIR/references/markdown-rendering.md"
        "$ROSEY_CONFIG_DIR/install-manifest.json"
    )
    if [ "$WRITE_PIN" = true ]; then
        required+=("$ROSEY_CONFIG_DIR/agentic-env.json" "$ROSEY_CONFIG_DIR/hindsight-pin")
    fi
    for path in "${required[@]}"; do
        if [ ! -e "$path" ]; then
            echo "missing: $path"
            missing=$((missing + 1))
        fi
    done
    if [ "$missing" -eq 0 ]; then
        echo "Rosey global installation present ($INSTALL_VERSION)"
        return 0
    fi
    echo "Rosey global installation incomplete ($missing missing)"
    return 1
}

install_global_payload() {
    echo "-> Installing global Cursor rules, skills, and agents..."
    copy_global_rules
    copy_global_skills
    copy_global_agents
    copy_global_hooks

    echo "-> Installing global OpenCode skills, agents, and plugin..."
    copy_global_opencode_runtime

    echo "-> Installing global Pi skills, agents, and warm-start..."
    copy_global_pi_runtime

    echo "-> Installing Rosey guidance, pins, and contract references..."
    write_global_guidance
    write_global_pins
    install_global_references
    write_global_install_markers

    echo "-> Updating machine-global Git excludes..."
    rosey_global_gitignore_ensure

    echo "-> Seeding global skill credentials and MCP configuration..."
    seed_global_skill_env
    merge_global_mcp
}

# The rest of this file retains the machine-tool installers and Hindsight setup
# from the previous implementation. All global payload work runs after those
# helper definitions are loaded, and before optional machine checks at EOF.

# --- npm install helpers ---

install_npm_deps() {
    local dir="$1"
    local label="$2"

    if [ ! -f "$dir/package.json" ]; then
        return 0
    fi
    if ! command -v npm >/dev/null 2>&1; then
        echo "   ⚠️  Skipping $label (npm not found on PATH)"
        return 0
    fi

    echo "-> npm install: $label"
    (
        cd "$dir"
        if [ -f pnpm-lock.yaml ] && command -v pnpm >/dev/null 2>&1; then
            pnpm install --frozen-lockfile 2>/dev/null || pnpm install
        elif [ -f yarn.lock ] && command -v yarn >/dev/null 2>&1; then
            yarn install --frozen-lockfile 2>/dev/null || yarn install
        elif [ -f package-lock.json ]; then
            npm ci 2>/dev/null || npm install
        else
            npm install
        fi
    ) || echo "   ⚠️  npm install failed in $label (continuing)"
}

# Global skill dependencies are installed after the global payload is copied.

# --- Machine-once tool installs ---
# Per-user/machine, not per target repo. Probe the CLI; never reinstall if it exists.
# Darwin: Homebrew (not for jq/rg/gh). Linux/WSL: apt only (Debian and derivatives).
# jq, rg, gh: GitHub release binaries into ~/.local/bin. Native Windows is not supported.

host_path() {
    PATH="${HOME}/.local/bin:${HOME}/.bun/bin:${PATH}"
    export PATH
}

host_has() {
    host_path
    command -v "$1" >/dev/null 2>&1
}

ensure_local_bin() {
    mkdir -p "${HOME}/.local/bin"
}

host_os() {
    case "$(uname -s)" in
        Darwin) echo darwin ;;
        Linux) echo linux ;;
        *) echo other ;;
    esac
}

http_get() {
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$1"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- "$1"
    else
        return 1
    fi
}

http_download() {
    local url="$1"
    local dest="$2"
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$url" -o "$dest"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO "$dest" "$url"
    else
        return 1
    fi
}

linux_pkg_install_one() {
    local pkg="$1"

    if [ -z "$pkg" ]; then
        return 1
    fi
    if ! command -v apt-get >/dev/null 2>&1; then
        echo "   ⚠️  apt-get not found. Linux/WSL installs need Debian or a derivative."
        return 1
    fi

    if [ "${ROSEY_APT_UPDATED:-0}" != 1 ]; then
        if command -v sudo >/dev/null 2>&1; then
            sudo apt-get update -qq || true
        else
            apt-get update -qq || true
        fi
        ROSEY_APT_UPDATED=1
    fi
    if command -v sudo >/dev/null 2>&1; then
        sudo apt-get install -y "$pkg"
    else
        apt-get install -y "$pkg"
    fi
}

github_latest_asset() {
    local repo="$1"
    local pattern="$2"
    local url=""

    url="$(http_get "https://api.github.com/repos/${repo}/releases/latest" \
        | grep -o 'https://github.com/[^"]*' \
        | grep -E "$pattern" \
        | grep -v '\.sha256' \
        | grep -v '\.sig' \
        | head -n 1 || true)"
    if [ -z "$url" ]; then
        return 1
    fi
    echo "$url"
}

install_jq_binary() {
    local asset dest
    ensure_local_bin
    dest="${HOME}/.local/bin/jq"
    case "$(host_os)-$(uname -m)" in
        linux-x86_64 | linux-amd64) asset="jq-linux-amd64" ;;
        linux-aarch64 | linux-arm64) asset="jq-linux-arm64" ;;
        darwin-arm64) asset="jq-macos-arm64" ;;
        darwin-x86_64) asset="jq-macos-amd64" ;;
        *) return 1 ;;
    esac
    http_download "https://github.com/jqlang/jq/releases/latest/download/${asset}" "$dest" || return 1
    chmod +x "$dest"
}

install_rg_binary() {
    local pattern url tmp tarball
    ensure_local_bin
    case "$(uname -s)-$(uname -m)" in
        Linux-x86_64 | Linux-amd64) pattern='ripgrep-.*-x86_64-unknown-linux-musl\.tar\.gz$' ;;
        Linux-aarch64 | Linux-arm64) pattern='ripgrep-.*-aarch64-unknown-linux-musl\.tar\.gz$' ;;
        Darwin-arm64) pattern='ripgrep-.*-aarch64-apple-darwin\.tar\.gz$' ;;
        Darwin-x86_64) pattern='ripgrep-.*-x86_64-apple-darwin\.tar\.gz$' ;;
        *) return 1 ;;
    esac
    url="$(github_latest_asset BurntSushi/ripgrep "$pattern")" || return 1
    tmp="$(mktemp -d)"
    tarball="$tmp/rg.tgz"
    http_download "$url" "$tarball" || {
        rm -rf "$tmp"
        return 1
    }
    tar -xzf "$tarball" -C "$tmp" || {
        rm -rf "$tmp"
        return 1
    }
    find "$tmp" -type f -name rg -exec cp {} "${HOME}/.local/bin/rg" \;
    rm -rf "$tmp"
    if [ ! -f "${HOME}/.local/bin/rg" ]; then
        return 1
    fi
    chmod +x "${HOME}/.local/bin/rg"
    host_has rg
}

install_gh_binary() {
    local arch pattern url tmp archive found
    ensure_local_bin
    case "$(uname -m)" in
        x86_64 | amd64) arch="amd64" ;;
        aarch64 | arm64) arch="arm64" ;;
        *) return 1 ;;
    esac
    case "$(host_os)" in
        linux) pattern="gh_.*_linux_${arch}\\.tar\\.gz$" ;;
        darwin) pattern="gh_.*_macOS_${arch}\\.zip$" ;;
        *) return 1 ;;
    esac
    url="$(github_latest_asset cli/cli "$pattern")" || return 1
    tmp="$(mktemp -d)"
    archive="$tmp/gh.archive"
    http_download "$url" "$archive" || {
        rm -rf "$tmp"
        return 1
    }
    case "$(host_os)" in
        linux)
            tar -xzf "$archive" -C "$tmp" || {
                rm -rf "$tmp"
                return 1
            }
            ;;
        darwin)
            if command -v unzip >/dev/null 2>&1; then
                unzip -qo "$archive" -d "$tmp" || {
                    rm -rf "$tmp"
                    return 1
                }
            else
                rm -rf "$tmp"
                return 1
            fi
            ;;
    esac
    found="$(find "$tmp" -type f -name gh | head -n 1)"
    if [ -z "$found" ]; then
        rm -rf "$tmp"
        return 1
    fi
    cp "$found" "${HOME}/.local/bin/gh"
    chmod +x "${HOME}/.local/bin/gh"
    rm -rf "$tmp"
    host_has gh
}

# cmd [brew_formula] [apt_package]
# jq/rg/gh ignore extra args and always use GitHub binaries (not brew/apt).
# brew is Darwin-only. Linux/WSL uses apt only.
ensure_host_cli() {
    local cmd="$1"
    local brew_f="${2-}"
    local apt_p="${3-}"

    if host_has "$cmd"; then
        echo "-> $cmd already on this machine ($(command -v "$cmd")); skipping install"
        return 0
    fi

    echo "-> Installing $cmd once on this machine..."

    case "$cmd" in
        jq)
            install_jq_binary || true
            ;;
        rg)
            install_rg_binary || true
            ;;
        gh)
            install_gh_binary || true
            ;;
        *)
            if [ "$(uname -s)" = Darwin ]; then
                if [ -n "$brew_f" ] && command -v brew >/dev/null 2>&1; then
                    brew install "$brew_f" || true
                elif [ "$cmd" = make ]; then
                    echo "   ⚠️  make missing. Install Xcode Command Line Tools: xcode-select --install"
                    return 1
                fi
            elif [ "$(uname -s)" = Linux ]; then
                if [ -n "$apt_p" ]; then
                    linux_pkg_install_one "$apt_p" || true
                fi
            else
                echo "   ⚠️  Unsupported OS for $cmd (need macOS or Debian/Ubuntu WSL)."
                return 1
            fi
            ;;
    esac

    if host_has "$cmd"; then
        echo "   $cmd installed: $(command -v "$cmd")"
        return 0
    fi
    case "$cmd" in
        jq | rg | gh)
            echo "   ⚠️  $cmd install finished but CLI not on PATH. Add ~/.local/bin to PATH, then re-run."
            ;;
        git)
            if [ "$(uname -s)" = Darwin ]; then
                echo "   ⚠️  git missing. Install with Homebrew or Xcode Command Line Tools."
            else
                echo "   ⚠️  git missing. Install with apt: sudo apt-get install git"
            fi
            ;;
        make)
            if [ "$(uname -s)" = Darwin ]; then
                echo "   ⚠️  make missing. Install Xcode Command Line Tools: xcode-select --install"
            else
                echo "   ⚠️  make missing. Install with apt: sudo apt-get install make"
            fi
            ;;
        *)
            echo "   ⚠️  $cmd missing and install did not put it on PATH."
            ;;
    esac
    return 1
}

install_uv() {
    if host_has uv; then
        echo "-> uv already on this machine ($(command -v uv)); skipping install"
        return 0
    fi

    echo "-> Installing uv once on this machine (Hindsight, bumpversion, gitchangelog)..."
    if ! command -v curl >/dev/null 2>&1; then
        echo "   ⚠️  curl is required to install uv. Install curl, then re-run."
        return 1
    fi
    curl -LsSf https://astral.sh/uv/install.sh | sh || {
        echo "   ⚠️  uv install failed. See https://docs.astral.sh/uv/"
        return 1
    }
    host_path
    if host_has uv; then
        echo "   uv installed: $(command -v uv)"
        return 0
    fi
    echo "   ⚠️  uv install finished but CLI not on PATH. Add ~/.local/bin to PATH, then re-run."
    return 1
}

install_bun() {
    if host_has bun; then
        echo "-> bun already on this machine ($(command -v bun)); skipping install"
        return 0
    fi

    echo "-> Installing bun once on this machine (OpenCode auto-installs npm plugins with bun)..."
    if ! command -v curl >/dev/null 2>&1; then
        echo "   ⚠️  curl is required to install bun. Install curl, then re-run."
        return 1
    fi
    curl -fsSL https://bun.sh/install | bash || {
        echo "   ⚠️  bun install failed. See https://bun.sh/docs/installation"
        return 1
    }
    host_path
    if host_has bun; then
        echo "   bun installed: $(command -v bun)"
        return 0
    fi
    echo "   ⚠️  bun install finished but CLI not on PATH. Add ~/.bun/bin to PATH, then re-run."
    return 1
}

install_gitchangelog() {
    if host_has gitchangelog; then
        echo "-> gitchangelog already on this machine ($(command -v gitchangelog)); skipping install"
        return 0
    fi

    echo "-> Installing gitchangelog once on this machine (release HISTORY)..."
    if host_has uv; then
        uv tool install gitchangelog || {
            echo "   ⚠️  uv tool install gitchangelog failed."
            echo "      Retry: uv tool install gitchangelog"
            return 1
        }
    elif command -v python3 >/dev/null 2>&1; then
        python3 -m pip install --user gitchangelog || {
            echo "   ⚠️  pip install --user gitchangelog failed."
            echo "      Retry: python3 -m pip install --user gitchangelog"
            return 1
        }
    else
        echo "   ⚠️  Need uv or python3 to install gitchangelog."
        return 1
    fi

    if host_has gitchangelog; then
        echo "   gitchangelog installed: $(command -v gitchangelog)"
        return 0
    fi
    echo "   ⚠️  gitchangelog install finished but CLI not on PATH. Add ~/.local/bin to PATH, then re-run."
    return 1
}

if [ "$CHECK_ONLY" = true ]; then
    run_global_check
    exit $?
fi

if [ "${ROSEY_SKIP_MACHINE_TOOLS:-0}" != 1 ]; then
    host_path

    ensure_host_cli git git git || true
    # Homebrew make is keg-only and does not provide `make` on PATH; Darwin uses Xcode CLT.
    ensure_host_cli make "" make || true
    ensure_host_cli curl curl curl || true
    ensure_host_cli rsync rsync rsync || true
    ensure_host_cli jq || true
    ensure_host_cli rg || true
    ensure_host_cli gh || true
    install_uv || true
    install_bun || true
fi

# --- Sentrux ---

sentrux_available() {
    host_path
    command -v sentrux >/dev/null 2>&1 && sentrux --version >/dev/null 2>&1
}

install_sentrux() {
    if sentrux_available; then
        echo "-> Sentrux already on this machine ($(sentrux --version 2>/dev/null || echo ok)); skipping install"
        return 0
    fi

    echo "-> Installing Sentrux CLI once on this machine (required for rosey-plan / rosey-work / rosey-qa)..."
    case "$(uname -s)" in
        Darwin)
            if command -v brew >/dev/null 2>&1; then
                brew install sentrux/tap/sentrux || {
                    echo "   ⚠️  brew install sentrux failed. Try: brew install sentrux/tap/sentrux"
                    return 1
                }
            else
                echo "   ⚠️  Homebrew not found. Install Sentrux manually:"
                echo "      brew install sentrux/tap/sentrux"
                return 1
            fi
            ;;
        Linux)
            curl -fsSL https://sentrux.dev/install.sh | sh || {
                echo "   ⚠️  Sentrux install script failed. See https://sentrux.dev/docs/mcp/"
                return 1
            }
            ;;
        *)
            echo "   ⚠️  Automatic Sentrux install not supported on this OS."
            echo "      Install manually: cargo install sentrux  (see rosey-sentrux skill)"
            return 1
            ;;
    esac

    if sentrux_available; then
        echo "   Sentrux installed: $(sentrux --version 2>/dev/null || true)"
    fi
}

# --- pi-subagents (Pi subagent support) ---
# Pi has no native subagents; the pi-subagents extension adds them. It is a
# machine-once install via the `pi` CLI. Only runs when the `pi` CLI is present;
# otherwise we still scaffold .pi/agents and note the requirement.

pi_subagents_available() {
    host_path
    command -v pi >/dev/null 2>&1 && pi list 2>/dev/null | grep -qi 'pi-subagents'
}

install_pi_subagents() {
    if ! command -v pi >/dev/null 2>&1; then
        echo "   ⚠️  pi CLI not found; skipping pi-subagents install (Pi agents load only after you install it)."
        echo "      Install Pi, then: pi install npm:pi-subagents"
        return 1
    fi

    if pi_subagents_available; then
        echo "-> pi-subagents already installed; skipping"
        return 0
    fi

    echo "-> Installing pi-subagents once on this machine (Pi subagent support)..."
    if pi install npm:pi-subagents; then
        echo "   pi-subagents installed."
        return 0
    fi
    echo "   ⚠️  pi-subagents install failed. Retry: pi install npm:pi-subagents"
    return 1
}

# --- pi-mcp-adapter (nicobailon/pi-mcp-adapter) ---
# Token-efficient MCP adapter for Pi. Installed once on the machine via `pi install`.
# Reads standard MCP files (.mcp.json, ~/.config/mcp/mcp.json, .pi/mcp.json) so the
# seeded .pi/mcp.json is picked up automatically. Fail-open: Pi agents still load
# without it; only MCP tool access is missing.
pi_mcp_adapter_available() {
    host_path
    command -v pi >/dev/null 2>&1 && pi list 2>/dev/null | grep -qi 'pi-mcp-adapter'
}

install_pi_mcp_adapter() {
    if ! command -v pi >/dev/null 2>&1; then
        echo "   ⚠️  pi CLI not found; skipping pi-mcp-adapter install (MCP tools load only after you install it)."
        echo "      Install Pi, then: pi install npm:pi-mcp-adapter"
        return 1
    fi

    if pi_mcp_adapter_available; then
        echo "-> pi-mcp-adapter already installed; skipping"
        return 0
    fi

    echo "-> Installing pi-mcp-adapter once on this machine (token-efficient MCP for Pi)..."
    if pi install npm:pi-mcp-adapter; then
        echo "   pi-mcp-adapter installed."
        return 0
    fi
    echo "   ⚠️  pi-mcp-adapter install failed. Retry: pi install npm:pi-mcp-adapter"
    return 1
}

# --- pi-ask-user (interactive decision gating) ---
# Adds the ask_user tool and bundled ask-user skill for explicit operator
# decisions during ambiguous or high-stakes agent runs.
pi_ask_user_available() {
    host_path
    command -v pi >/dev/null 2>&1 && pi list 2>/dev/null | grep -qi 'pi-ask-user'
}

install_pi_ask_user() {
    if ! command -v pi >/dev/null 2>&1; then
        echo "   ⚠️  pi CLI not found; skipping pi-ask-user install."
        echo "      Install Pi, then: pi install npm:pi-ask-user"
        return 1
    fi

    if pi_ask_user_available; then
        echo "-> pi-ask-user already installed; skipping"
        return 0
    fi

    echo "-> Installing pi-ask-user once on this machine (interactive decision gating)..."
    if pi install npm:pi-ask-user; then
        echo "   pi-ask-user installed."
        return 0
    fi
    echo "   ⚠️  pi-ask-user install failed. Retry: pi install npm:pi-ask-user"
    return 1
}

# --- git-flow (rosey-pr / rosey-work / rosey-debug / rosey-release) ---
# Homebrew git-flow-avh is disabled; git-flow (nvie) is deprecated. git-flow-next
# provides `git flow` and satisfies `git flow version`.

git_flow_available() {
    host_path
    git flow version >/dev/null 2>&1
}

install_git_flow() {
    if git_flow_available; then
        echo "-> git-flow already on this machine ($(git flow version 2>/dev/null | head -1 || echo ok)); skipping install"
        return 0
    fi

    echo "-> Installing git-flow once on this machine (required for rosey-pr / rosey-release)..."
    if [ "$(uname -s)" = Darwin ]; then
        if command -v brew >/dev/null 2>&1; then
            brew install git-flow-next || {
                echo "   ⚠️  brew install git-flow-next failed. Try: brew install git-flow-next"
                return 1
            }
        else
            echo "   ⚠️  Homebrew not found. Install git-flow-next:"
            echo "      brew install git-flow-next"
            return 1
        fi
    elif [ "$(uname -s)" = Linux ]; then
        linux_pkg_install_one git-flow || true
    else
        echo "   ⚠️  Unsupported OS for git-flow (need macOS or Debian/Ubuntu WSL)."
        return 1
    fi

    if git_flow_available; then
        echo "   git-flow installed: $(git flow version 2>/dev/null | head -1 || true)"
    else
        echo "   ⚠️  git-flow install finished but \`git flow version\` still fails. Check PATH."
        return 1
    fi
}

configure_repo_signing_key() {
    local existing global keys count key

    if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "-> Skipping signing key (not a git repository)"
        return 0
    fi

    existing="$(git config --local --get user.signingkey 2>/dev/null || true)"
    if [ -n "$existing" ]; then
        echo "-> user.signingkey already set locally ($existing); skipping"
        return 0
    fi

    global="$(git config --global --get user.signingkey 2>/dev/null || true)"
    if [ -n "$global" ]; then
        git config --local user.signingkey "$global"
        echo "-> Set local user.signingkey from global ($global)"
        return 0
    fi

    if ! host_has gpg; then
        echo "   ⚠️  gpg not found; cannot set user.signingkey. Install gnupg and add a secret key."
        return 1
    fi

    keys="$(gpg --list-secret-keys --with-colons 2>/dev/null | awk -F: '/^sec:/ { want=1; next } want && /^fpr:/ { print $10; want=0 }')"
    count=0
    if [ -n "$keys" ]; then
        count="$(printf '%s\n' "$keys" | grep -c .)"
    fi

    if [ "$count" -eq 0 ]; then
        echo "   ⚠️  No GPG secret keys. Create one, then re-run to set user.signingkey."
        return 1
    fi
    if [ "$count" -gt 1 ]; then
        echo "   ⚠️  Multiple GPG secret keys; not picking one."
        echo "      Set: git config --local user.signingkey <fingerprint>"
        printf '%s\n' "$keys" | sed 's/^/      /'
        return 1
    fi

    key="$keys"
    git config --local user.signingkey "$key"
    echo "-> Set local user.signingkey to $key"
}

# --- bumpversion (rosey-release / scripts/release.sh) ---
# Classic CLI (`bumpversion --dry-run --list`) from bump2version. Do not install
# Homebrew bump-my-version — that binary is a different command.

bumpversion_available() {
    host_has bumpversion
}

install_bumpversion() {
    host_path

    if bumpversion_available; then
        echo "-> bumpversion already on this machine ($(command -v bumpversion)); skipping install"
        return 0
    fi

    echo "-> Installing bumpversion once on this machine (required for rosey-release)..."
    if host_has uv; then
        uv tool install bump2version || {
            echo "   ⚠️  uv tool install bump2version failed."
            echo "      Retry: uv tool install bump2version"
            return 1
        }
    elif command -v python3 >/dev/null 2>&1; then
        python3 -m pip install --user bump2version || {
            echo "   ⚠️  pip install --user bump2version failed."
            echo "      Retry: python3 -m pip install --user bump2version"
            return 1
        }
    else
        echo "   ⚠️  Need uv or python3 to install bumpversion (bump2version)."
        echo "      Install uv: https://docs.astral.sh/uv/"
        echo "      Then: uv tool install bump2version"
        return 1
    fi

    if bumpversion_available; then
        echo "   bumpversion installed: $(command -v bumpversion)"
    else
        echo "   ⚠️  bumpversion install finished but CLI not on PATH."
        echo "      Add ~/.local/bin to PATH, then re-run."
        return 1
    fi
}

# --- Hindsight embed ---

hindsight_embed_configured() {
    [ -f "${HOME}/.hindsight/embed" ] || [ -f "${HOME}/.hindsight/config.env" ]
}

read_hindsight_pin() {
    local pin_file="$ROSEY_CONFIG_DIR/hindsight-pin"
    if [ -f "$pin_file" ]; then
        tr -d '[:space:]' <"$pin_file"
    elif [ -f "$SOURCE_ROOT/.cursor/hindsight-pin" ]; then
        tr -d '[:space:]' <"$SOURCE_ROOT/.cursor/hindsight-pin"
    else
        echo "0.8.2"
    fi
}

hindsight_embed_template_path() {
    if [ -f "$SOURCE_ROOT/.cursor/hindsight-embed.example" ]; then
        echo "$SOURCE_ROOT/.cursor/hindsight-embed.example"
    else
        return 1
    fi
}

# Seed ~/.hindsight/embed from template when missing. Fills every KEY= from SOURCE_ROOT/.env
# (then process env). Never overwrites existing config.
seed_hindsight_embed_if_needed() {
    local template dest provider

    if hindsight_embed_configured; then
        return 0
    fi

    if ! template="$(hindsight_embed_template_path)"; then
        echo "   ⚠️  No hindsight-embed.example template found; cannot seed config."
        return 1
    fi

    provider="$(rosey_resolve_env_value HINDSIGHT_API_LLM_PROVIDER)"
    provider="${provider:-openai}"

    dest="${HOME}/.hindsight/embed"
    case "$provider" in
        ollama | vertexai)
            if ! seed_dotenv_from_example "$template" "$dest" ""; then
                echo "   ⚠️  Failed to seed ~/.hindsight/embed from template."
                return 1
            fi
            ;;
        *)
            if ! seed_dotenv_from_example "$template" "$dest" "HINDSIGHT_API_LLM_API_KEY"; then
                echo "   Hindsight not configured yet (no API key for seed)."
                echo "      Set HINDSIGHT_* keys in $SOURCE_ROOT/.env (see .cursor/hindsight-embed.example),"
                echo "      then re-run install.sh to seed ~/.hindsight/embed."
                echo "      Or run interactive setup: uvx hindsight-embed@$(read_hindsight_pin) configure"
                return 1
            fi
            ;;
    esac

    echo "   Seeded ~/.hindsight/embed from template (provider=${provider})."
    return 0
}

hindsight_path() {
    PATH="${HOME}/.local/bin:${PATH}"
    export PATH
}

hindsight_cli() {
    hindsight_path
    hindsight-embed "$@"
}

# The standalone `hindsight` CLI binary the embed forwards memory commands to.
hindsight_cli_version() {
    hindsight_path
    command -v hindsight >/dev/null 2>&1 || return 1
    hindsight --version 2>/dev/null | awk '{print $NF}'
}

# Port of the default profile's daemon. Mirrors profile_manager._resolve_ports:
# an explicit HINDSIGHT_API_PORT in the profile file wins, else 8888.
hindsight_daemon_port() {
    local cfg port=""
    for cfg in "${HOME}/.hindsight/embed" "${HOME}/.hindsight/config.env"; do
        [ -f "$cfg" ] || continue
        port="$(sed -n 's/^HINDSIGHT_API_PORT=\([0-9][0-9]*\).*/\1/p' "$cfg" | tail -1)"
        [ -n "$port" ] && break
    done
    printf '%s' "${port:-8888}"
}

# `hindsight-embed daemon status` is a bare `GET /health == 200`, so any service
# squatting on the daemon port is mistaken for Hindsight. Require a Hindsight
# fingerprint (/version, present since 0.7.1) instead. Falls back to the CLI
# check when curl is unavailable.
hindsight_daemon_healthy() {
    local port
    if ! command -v curl >/dev/null 2>&1; then
        hindsight_cli daemon status >/dev/null 2>&1
        return $?
    fi
    port="$(hindsight_daemon_port)"
    curl -fsS -m 2 "http://127.0.0.1:${port}/version" 2>/dev/null | grep -q '"api_version"'
}

# The embed installs the `hindsight` CLI binary from a vendor installer outside
# the uv pin, and only when the binary is missing. A stale binary therefore never
# upgrades on its own, leaving the client behind the pinned daemon.
ensure_hindsight_cli() {
    local pin="$1" current
    current="$(hindsight_cli_version || true)"
    if [ "$current" = "$pin" ]; then
        echo "   hindsight CLI already at the pinned ${pin}."
        return 0
    fi

    echo "   hindsight CLI is ${current:-not installed}; installing pinned ${pin}..."
    if HINDSIGHT_CLI_VERSION="$pin" bash -c "curl -fsSL ${HINDSIGHT_CLI_INSTALLER_URL} | bash" >/dev/null 2>&1 \
        && [ "$(hindsight_cli_version || true)" = "$pin" ]; then
        echo "   hindsight CLI installed at ${pin}."
        return 0
    fi

    echo "   ⚠️  hindsight CLI install failed (memory commands still work, but the client version may drift)."
    echo "      Retry: HINDSIGHT_CLI_VERSION=${pin} curl -fsSL ${HINDSIGHT_CLI_INSTALLER_URL} | bash"
    return 1
}

# True when hindsight-embed is on PATH and responds (installed on this machine).
hindsight_cli_available() {
    hindsight_path
    command -v hindsight-embed >/dev/null 2>&1 && hindsight-embed --help >/dev/null 2>&1
}

# Install Hindsight CLI once per machine (skip when CLI already responds).
# Sets HINDSIGHT_TOOL_ACTION=installed|skipped for callers.
install_hindsight_tool() {
    local pin="$1"
    HINDSIGHT_TOOL_ACTION="skipped"

    if hindsight_cli_available; then
        echo "   Hindsight tool already on this machine; skipping install"
        return 0
    fi

    echo "   Installing Hindsight embed + api once on this machine (pinned ${pin})..."
    echo "   First install may take 30–60+ minutes while large dependencies download."
    if ! uv tool install "hindsight-embed==${pin}" --with "hindsight-api==${pin}"; then
        return 1
    fi

    if ! hindsight_cli_available; then
        return 1
    fi

    HINDSIGHT_TOOL_ACTION="installed"
    return 0
}

check_hindsight_embed() {
    local pin
    pin="$(read_hindsight_pin)"
    HINDSIGHT_TOOL_ACTION="skipped"

    echo "-> Checking optional Hindsight embed CLI..."

    if ! host_has uv; then
        echo "   ⚠️  Hindsight embed requires uv for local memory."
        echo "      Install uv: https://docs.astral.sh/uv/"
        if hindsight_embed_configured; then
            echo "      After installing uv, re-run this install script."
        else
            echo "      Set HINDSIGHT_API_LLM_API_KEY or OPENAI_API_KEY, then re-run install.sh to seed config."
            echo "      Or: uvx hindsight-embed@${pin} configure"
        fi
        return 0
    fi

    # Seed once from template when possible; interactive configure remains a fallback.
    if ! hindsight_embed_configured; then
        seed_hindsight_embed_if_needed || return 0
    fi

    if ! hindsight_embed_configured; then
        return 0
    fi

    if ! install_hindsight_tool "$pin"; then
        echo "   ⚠️  Hindsight tool install failed."
        echo "      Retry: uv tool install hindsight-embed==${pin} --with hindsight-api==${pin}"
        return 0
    fi

    ensure_hindsight_cli "$pin" || true

    # Daemon start only on fresh tool install; later repo installs rely on IDE hooks.
    if [ "${HINDSIGHT_TOOL_ACTION}" = "skipped" ]; then
        if hindsight_daemon_healthy; then
            echo "   Hindsight embed daemon is running."
        else
            echo "   Hindsight tool present; daemon start left to IDE session hooks."
        fi
        return 0
    fi

    if hindsight_daemon_healthy; then
        echo "   Hindsight embed daemon is running."
        return 0
    fi

    echo "   Hindsight embed is configured but daemon is stopped; starting..."
    if HINDSIGHT_EMBED_DAEMON_STARTUP_TIMEOUT="${HINDSIGHT_EMBED_DAEMON_STARTUP_TIMEOUT:-600}" \
        hindsight_cli daemon start >/dev/null 2>&1 \
        && hindsight_daemon_healthy; then
        echo "   Hindsight embed daemon started."
    else
        echo "   ⚠️  Hindsight daemon failed to start (cold boot can take several minutes)."
        echo "      Retry: HINDSIGHT_EMBED_DAEMON_STARTUP_TIMEOUT=600 hindsight-embed daemon start"
        echo "      If port $(hindsight_daemon_port) is held by another service, set HINDSIGHT_API_PORT to a free port."
        echo "      Logs: hindsight-embed daemon logs -n 50"
        echo "      Hook log: ~/.hindsight/hook-last-run.log"
    fi
}

install_global_payload

# Install dependencies only after the global skill trees exist. This never
# enters or modifies a repository workspace. Set ROSEY_SKIP_SKILL_DEPS=1 for a
# filesystem-only install/test.
if [ "${ROSEY_SKIP_SKILL_DEPS:-0}" != 1 ]; then
    for skills_root in "$CURSOR_HOME/skills" "$OPENCODE_HOME/skills" "$PI_HOME/skills"; do
        if [ -d "$skills_root" ]; then
            while IFS= read -r -d '' pkg; do
                skill_dir="$(dirname "$pkg")"
                install_npm_deps "$skill_dir" "global skill $(basename "$skill_dir")"
            done < <(find "$skills_root" -name package.json -not -path '*/node_modules/*' -print0 2>/dev/null)
        fi
    done
fi

if [ "${ROSEY_SKIP_MACHINE_TOOLS:-0}" != 1 ]; then
    install_bumpversion || true
    install_gitchangelog || true
    install_git_flow || true
    install_sentrux || true
    install_pi_subagents || true
    install_pi_mcp_adapter || true
    install_pi_ask_user || true
    check_hindsight_embed || true
fi

# --- Inventory of host tools this script does not install ---

inventory_cli() {
    local label="$1"
    local bin="$2"
    PATH="${HOME}/.local/bin:${PATH}"
    if command -v "$bin" >/dev/null 2>&1; then
        echo "   present  $label"
    else
        echo "   missing  $label"
    fi
}

echo ""
echo "-> Host tools this script does not install:"
inventory_cli "docker (Engine; daemon must be running for release)" docker
inventory_cli "gpg (needed to set user.signingkey when no global key is set)" gpg
echo "   not packages: gh auth login, GPG secret keys (not generated), Docker daemon up"

echo ""
echo "Rosey global environment installed successfully!"
echo "   Cursor: ~/.cursor/rules, ~/.cursor/skills, ~/.cursor/agents, and global hooks."
echo "   OpenCode: ~/.config/opencode/skills, agents, instructions, and native Hindsight plugin."
echo "   Pi: ~/.pi/agent/skills plus ~/.agents agents and global Hindsight extension."
echo "   Rosey state: ~/.config/rosey (guidance, pins, contract references, manifest)."
echo "   No repository files or IDE trees were written. Skills create repo files/directories lazily when invoked."
echo "   Machine-once CLIs skipped if already on PATH: git, make, curl, rsync, jq, rg, gh, uv, bun, gitchangelog, bumpversion, git-flow, sentrux, hindsight-embed."
echo "   Pi extensions installed once when the pi CLI is present: pi-subagents, pi-mcp-adapter, pi-ask-user."
