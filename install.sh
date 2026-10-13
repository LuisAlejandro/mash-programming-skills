#!/usr/bin/env bash
set -euo pipefail

# Mash Programming Skills — machine-global installer.
# This installer intentionally never writes into the current repository.
# A checkout uses that checkout. Any other run downloads the master tarball
# and re-runs the installer inside it:
#   curl -fsSL https://raw.githubusercontent.com/LuisAlejandro/mash-programming-skills/master/install.sh | bash

MASH_GITHUB_REPO="LuisAlejandro/mash-programming-skills"
MASH_GITHUB_REF="master"

if [ -n "${MASH_INSTALL_TMP:-}" ]; then
    trap 'rm -rf "$MASH_INSTALL_TMP"' EXIT
fi

fetch_master_tarball() {
    local tmp url token extracted=() dir
    tmp="$(mktemp -d)"
    token="${GITHUB_TOKEN:-${GH_TOKEN:-}}"
    if [ -n "$token" ]; then
        url="https://api.github.com/repos/${MASH_GITHUB_REPO}/tarball/${MASH_GITHUB_REF}"
    else
        url="https://github.com/${MASH_GITHUB_REPO}/archive/refs/heads/${MASH_GITHUB_REF}.tar.gz"
    fi
    echo "-> Downloading ${MASH_GITHUB_REPO}@${MASH_GITHUB_REF}"
    if [ -n "$token" ]; then
        curl -fsSL -H "Authorization: Bearer ${token}" -H "Accept: application/vnd.github+json" "$url" | tar -xz -C "$tmp"
    else
        curl -fsSL "$url" | tar -xz -C "$tmp"
    fi || {
        rm -rf "$tmp"
        echo "Error: could not download ${MASH_GITHUB_REPO}@${MASH_GITHUB_REF}." >&2
        echo "   ${url}" >&2
        echo "   Until the repository is public, set GITHUB_TOKEN to a token that can read it." >&2
        exit 1
    }
    for dir in "$tmp"/*/; do
        [ -d "$dir" ] || continue
        extracted+=("$dir")
    done
    if [ "${#extracted[@]}" -ne 1 ] || [ ! -d "${extracted[0]}/src" ] || [ ! -f "${extracted[0]}/install.sh" ]; then
        rm -rf "$tmp"
        echo "Error: tarball did not contain a Mash Programming Skills tree." >&2
        exit 1
    fi
    export MASH_INSTALL_TMP="$tmp"
    chmod +x "${extracted[0]}/install.sh"
    exec "${extracted[0]}/install.sh" "$@"
}

script_tree=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    script_tree="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
if [ -n "${MASH_PROGRAMMING_SKILLS:-}" ]; then
    SOURCE_ROOT="$MASH_PROGRAMMING_SKILLS"
elif [ -n "$script_tree" ] && [ -d "$script_tree/src" ]; then
    SOURCE_ROOT="$script_tree"
else
    fetch_master_tarball "$@"
fi
VERSION_FILE="$SOURCE_ROOT/VERSION"
INSTALL_VERSION="0.1.0"
CHECK_ONLY=false
WRITE_PIN=true
WRITE_GUIDANCE=true

# Global destinations are machine-owned. Keep the Mash Programming Skills state root distinct from
# each IDE's own global directory so OpenCode can consume the same guidance and
# reference contracts without shadowing project AGENTS.md files.
MASH_CONFIG_DIR="${HOME}/.config/mash"
CURSOR_HOME="${HOME}/.cursor"
PI_HOME="${HOME}/.pi/agent"
OPENCODE_HOME="${HOME}/.config/opencode"
PI_SHARED_MCP="${HOME}/.config/mcp/mcp.json"
MANAGED_ARTIFACTS="$SOURCE_ROOT/scripts/managed_artifacts.py"
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

Installs Mash Programming Skills globally for Cursor, OpenCode, and Pi. It never writes to the
current repository. Repository AGENTS.md, DESIGN.md, IDE trees, .mcp.json, and
.mash/* files are not created by this command.

A checkout installs from that checkout. Otherwise the master tarball is downloaded:

  curl -fsSL https://raw.githubusercontent.com/LuisAlejandro/mash-programming-skills/master/install.sh | bash
EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

if [ ! -d "$SOURCE_ROOT/src" ]; then
    echo "Error: Could not find src directory in $SOURCE_ROOT" >&2
    echo "   MASH_PROGRAMMING_SKILLS must point at a Mash Programming Skills checkout." >&2
    exit 1
fi

# Read KEY=value from a dotenv-style file (last match). Strips optional quotes.
mash_dotenv_get() {
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
mash_resolve_env_value() {
    local key="$1" val=""
    if [ -n "${!key+x}" ] && [ -n "${!key}" ]; then
        printf '%s' "${!key}"
        return 0
    fi
    val="$(mash_dotenv_get "$SOURCE_ROOT/.env" "$key" 2>/dev/null || true)"
    printf '%s' "$val"
}

seed_dotenv_from_example() {
    local example="$1" dest="$2" required_key="${3:-}"
    local line key val missing=0

    [ -f "$dest" ] && return 0
    [ -f "$example" ] || return 1

    mkdir -p "$(dirname "$dest")"
    {
        echo "# Seeded by Mash Programming Skills install.sh at $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
        while IFS= read -r line || [ -n "$line" ]; do
            if [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]]; then
                printf '%s\n' "$line"
                continue
            fi
            if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)= ]]; then
                key="${BASH_REMATCH[1]}"
                if [ "${MASH_HINDSIGHT_PROMPTED:-}" = yes ]; then
                    case "$key" in
                        HINDSIGHT_API_LLM_PROVIDER | HINDSIGHT_API_LLM_MODEL | HINDSIGHT_API_LLM_API_KEY | HINDSIGHT_API_LLM_BASE_URL)
                            if [ -n "${!key+x}" ] && [ -n "${!key}" ]; then
                                val="${!key}"
                            else
                                val=""
                            fi
                            ;;
                        *)
                            val="$(mash_resolve_env_value "$key")"
                            ;;
                    esac
                else
                    val="$(mash_resolve_env_value "$key")"
                fi
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

mash_agents_guidance() {
    cat >"$1" <<'EOF'
# Mash Programming Skills Agent Guidance

This machine uses the Mash Programming Skills as global tooling.
This file contains universal Mash Programming Skills workflow guidance only; it does not replace
project-specific instructions in a repository's own AGENTS.md.

## Global Mash Programming Skills surfaces

- Always-on rules: `~/.config/mash/always-on-rules.md`
- Cursor rules (native): `~/.cursor/rules/*.mdc`
- Cursor skills: `~/.cursor/skills/`
- Cursor specialist agents: `~/.cursor/agents/`
- OpenCode instructions: `~/.config/opencode/opencode.json` points to this file
- OpenCode skills: `~/.config/opencode/skills/`
- OpenCode agents: `~/.config/opencode/agents/`
- Pi context: `~/.pi/agent/AGENTS.md`
- Pi skills: `~/.pi/agent/skills/`
- Pi specialist agents: `~/.agents/`

Before non-trivial planning, implementation, or review work, follow the
always-on Mash Programming Skills rules and use the relevant skill. Do not create or expect
repo-local IDE trees for Mash Programming Skills distribution.

## Hindsight

Hindsight is optional and machine-global. The version pin is
`~/.config/mash/hindsight-pin`; the shared contract references are under
`~/.config/mash/references/`.

When a Hindsight-gated skill is active, follow the hindsight-memory rule and
the `mash-hindsight` skill. If the daemon is unavailable, continue and record
`Hindsight: unavailable`.

## Repository ownership

Mash Programming Skills never writes a repository's `AGENTS.md`, `DESIGN.md`, IDE trees, MCP
files, or `.mash/*` working directories during installation. Owners may create
and track project-specific `AGENTS.md`/`DESIGN.md`; skills create their own
working directories lazily when invoked.
EOF
}

copy_global_rules() {
    local src name
    mkdir -p "$CURSOR_HOME/rules"
    rm -rf "$MASH_CONFIG_DIR/rules"
    for src in "$SOURCE_ROOT"/src/rules/*.mdc; do
        [ -f "$src" ] || continue
        name="$(basename "$src")"
        cp "$src" "$CURSOR_HOME/rules/$name"
    done
    write_global_always_on_rules
}

# Cursor applies .mdc rules natively through alwaysApply. OpenCode and Pi have no
# rule frontmatter, so the always-on subset is also emitted as one plain
# Markdown bundle: OpenCode injects it via instructions[], Pi via APPEND_SYSTEM.md.
write_global_always_on_rules() {
    local bundle="$MASH_CONFIG_DIR/always-on-rules.md"
    local mdc name description
    mkdir -p "$MASH_CONFIG_DIR" "$PI_HOME"
    {
        echo "# Mash Programming Skills — always-on rules"
        echo
        echo "Auto-generated from src/rules/*.mdc with alwaysApply: true."
        echo "Do not edit by hand; re-run install.sh to refresh."
    } >"$bundle"
    for mdc in "$SOURCE_ROOT"/src/rules/*.mdc; do
        [ -f "$mdc" ] || continue
        grep -qE '^alwaysApply:[[:space:]]*true' "$mdc" || continue
        name="$(basename "$mdc" .mdc)"
        description="$(awk '
            NR == 1 && /^---$/ { frontmatter = 1; next }
            frontmatter && /^---$/ { exit }
            frontmatter && /^description:[[:space:]]*/ {
                sub(/^description:[[:space:]]*/, "")
                if ($0 ~ /^".*"$/) {
                    sub(/^"/, "")
                    sub(/"$/, "")
                }
                print
                exit
            }
        ' "$mdc")"
        [ -n "$description" ] || description="$name"
        {
            echo
            echo "---"
            echo
            # Preserve rule descriptions as headings; Cursor reads frontmatter natively,
            # while OpenCode and Pi receive only this plain Markdown bundle.
            echo "## $description"
            echo
            awk 'NR == 1 && /^---$/ { fm = 1; next } fm && /^---$/ { fm = 0; next } !fm' "$mdc"
        } >>"$bundle"
    done
    cp "$bundle" "$PI_HOME/APPEND_SYSTEM.md"
}

copy_global_skills() {
    local src sname dest
    for src in "$SOURCE_ROOT"/src/skills/*/; do
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
    for src in "$SOURCE_ROOT"/src/agents/*; do
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
    local src="$SOURCE_ROOT/src/hooks/ensure-hindsight-daemon.sh"
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
    local hook_src="$SOURCE_ROOT/src/hooks/ensure-hindsight-daemon.sh"
    local ext_src="$SOURCE_ROOT/src/hooks-pi/mash-hindsight-daemon.ts"
    mkdir -p "$PI_HOME/scripts" "$PI_HOME/extensions"
    if [ -f "$hook_src" ]; then
        cp "$hook_src" "$PI_HOME/scripts/ensure-hindsight-daemon.sh"
        chmod +x "$PI_HOME/scripts/ensure-hindsight-daemon.sh"
    fi
    if [ -f "$ext_src" ]; then
        cp "$ext_src" "$PI_HOME/extensions/mash-hindsight-daemon.ts"
    fi
}

copy_global_opencode_runtime() {
    local src="$SOURCE_ROOT/src/hooks-opencode/mash-hindsight-daemon.ts"
    [ -f "$src" ] || return 0
    mkdir -p "$OPENCODE_HOME/plugin"
    cp "$src" "$OPENCODE_HOME/plugin/mash-hindsight-daemon.ts"
}

write_global_guidance() {
    [ "$WRITE_GUIDANCE" = true ] || return 0
    mkdir -p "$MASH_CONFIG_DIR" "$PI_HOME"
    mash_agents_guidance "$MASH_CONFIG_DIR/AGENTS.md"
    cp "$MASH_CONFIG_DIR/AGENTS.md" "$PI_HOME/AGENTS.md"
}

# Written to ~/.config/mash/hindsight-pin. The profile template and MCP catalog below are generated from here.
HINDSIGHT_PIN_VALUE="0.8.3"

mash_hindsight_embed_template() {
    cat <<'MASH_HINDSIGHT_EMBED_TEMPLATE'
# Hindsight Embed Configuration
# Generated by hindsight-embed configure

HINDSIGHT_EMBED_BANK_ID=
HINDSIGHT_EMBED_DAEMON_IDLE_TIMEOUT=
HINDSIGHT_EMBED_API_DATABASE_URL=pg0://hindsight-embed-default:15432

# LLM used for memory extraction. Any OpenAI-compatible gateway works: keep
# HINDSIGHT_API_LLM_PROVIDER=openai and point HINDSIGHT_API_LLM_BASE_URL at the
# gateway root. For OmniRoute that is https://assistant.fundere.app/v1 with the
# purpose-built omniroute-hindsight combo.
# Native providers (gemini, anthropic, groq, deepseek, ...) leave BASE_URL empty.
HINDSIGHT_API_LLM_PROVIDER=
HINDSIGHT_API_LLM_MODEL=
HINDSIGHT_API_LLM_API_KEY=
HINDSIGHT_API_LLM_BASE_URL=

# Daemon API port for the default profile. Leave empty for the default 8888.
# Set it when another service already owns 8888 (for example a Stream Deck
# install). The control center UI uses this port + 10000.
HINDSIGHT_API_PORT=
MASH_HINDSIGHT_EMBED_TEMPLATE
}

mash_mcp_catalog_json() {
    cat <<'MASH_MCP_CATALOG'
{
  "mcpServers": {
    "github": {
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer $GITHUB_TOKEN"
      }
    },
    "context7": {
      "type": "http",
      "url": "https://mcp.context7.com/mcp"
    },
    "sentrux": {
      "command": "sentrux",
      "args": [
        "mcp"
      ]
    },
    "cua-driver": {
      "command": "cua-driver",
      "args": [
        "mcp"
      ]
    },
    "agent-browser": {
      "command": "agent-browser",
      "args": [
        "mcp",
        "--tools",
        "core,network,debug"
      ]
    },
    "chrome-devtools": {
      "command": "npx",
      "args": [
        "-y",
        "chrome-devtools-mcp@1.10.1",
        "--categoryInput=false",
        "--categoryEmulation=false",
        "--categoryNetwork=false",
        "--categoryPerformance=false",
        "--memoryDebugging=true",
        "--isolated=true"
      ]
    }
  }
}
MASH_MCP_CATALOG
}

write_global_pins() {
    [ "$WRITE_PIN" = true ] || return 0
    mkdir -p "$MASH_CONFIG_DIR"
    printf '%s\n' "$HINDSIGHT_PIN_VALUE" >"$MASH_CONFIG_DIR/hindsight-pin"
    python3 - "$MASH_CONFIG_DIR/agentic-env.json" "$SOURCE_ROOT" "$INSTALL_VERSION" <<'PY'
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
    mkdir -p "$MASH_CONFIG_DIR/references"
    for source in \
        "$SOURCE_ROOT/references/model-tiers/model-tiers.md" \
        "$SOURCE_ROOT/references/markdown-rendering.md"; do
        [ -f "$source" ] || {
            echo "   ⚠️  Missing contract reference: $source" >&2
            continue
        }
        dest="$MASH_CONFIG_DIR/references/$(basename "$source")"
        cp "$source" "$dest"
    done
    rm -f "$MASH_CONFIG_DIR/references/scoping-synthesis.md"
}

merge_global_mcp() {
    local example github_token obsidian_key selected
    example="$(mktemp)"
    mash_mcp_catalog_json >"$example"

    # Set by the MCP prompt when the installer has a terminal; otherwise the
    # environment. An unattended run merges every example server.
    github_token="${MASH_GITHUB_TOKEN-$(mash_resolve_env_value GITHUB_TOKEN)}"
    obsidian_key="$(mash_resolve_env_value OBSIDIAN_API_KEY)"
    if [ "${MASH_PROMPTS:-no}" = yes ]; then
        selected="$MASH_MCP_SELECTED"
    else
        selected="*"
    fi
    if [ -z "$github_token" ] && [ "${MASH_PROMPTS:-no}" != yes ]; then
        echo "   no GitHub token; leaving the github MCP server unconfigured"
    fi
    python3 - "$MANAGED_ARTIFACTS" "$example" "$CURSOR_HOME/mcp.json" "$OPENCODE_HOME/opencode.json" "$PI_SHARED_MCP" "$PI_HOME/settings.json" "$github_token" "$obsidian_key" "$selected" <<'PY'
import importlib.util
import json
import sys
from pathlib import Path

managed_path, example, cursor_path, opencode_path, pi_shared_path, pi_settings_path, github_token, obsidian_key, selected_raw = sys.argv[1:10]
spec = importlib.util.spec_from_file_location("managed_artifacts", managed_path)
managed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(managed)
source = json.loads(Path(example).read_text())
owned = managed.mcp_owned_names(example)

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

# An unauthenticated github entry fails every call, so omit the server entirely
# when no token was supplied. Any server whose config still carries an
# unsubstituted placeholder is dropped for the same reason.
if not github_token:
    servers.pop("github", None)
servers = {
    name: srv
    for name, srv in servers.items()
    if "$GITHUB_TOKEN" not in json.dumps(srv) and "$OBSIDIAN_API_KEY" not in json.dumps(srv)
}
selected = None if selected_raw == "*" else selected_raw.split()
servers = managed.select_mcp_servers(servers, selected)

def merge(existing, adapted=None):
    """Apply this run's servers and drop owned names that are absent."""
    configured = servers if adapted is None else adapted
    return managed.merge_mcp_servers(existing, owned, configured)

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

# Cursor: Mash Programming Skills entries overwrite same-name entries by the accepted decision.
cursor = read_json(cursor_path)
cursor["mcpServers"] = merge(cursor.get("mcpServers"))
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
opencode["mcp"] = merge(opencode.get("mcp"), opencode_servers)
write_json(opencode_path, opencode)

# Standard global Pi MCP config consumed by pi-mcp-adapter.
pi_shared = read_json(pi_shared_path)
pi_shared["mcpServers"] = merge(pi_shared.get("mcpServers"))
write_json(pi_shared_path, pi_shared)

# Keep the Mash Programming Skills MCP map visible in Pi's machine settings as documented by the
# proposal; pi-mcp-adapter reads the standard shared config above.
pi_settings = read_json(pi_settings_path)
pi_settings["mcpServers"] = merge(pi_settings.get("mcpServers"))
write_json(pi_settings_path, pi_settings)
PY
    rm -f "$example"

    # Add the OpenCode instruction paths in a separate pass with exact paths.
    python3 - "$OPENCODE_HOME/opencode.json" "$MASH_CONFIG_DIR/AGENTS.md" "$MASH_CONFIG_DIR/always-on-rules.md" <<'PY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
try:
    data = json.loads(path.read_text()) if path.exists() else {}
except Exception:
    data = {}
if not isinstance(data, dict):
    data = {}
instructions = data.get("instructions")
if not isinstance(instructions, list):
    instructions = []
for entry in sys.argv[2:]:
    if entry not in instructions:
        instructions.append(entry)
data["instructions"] = instructions
path.write_text(json.dumps(data, indent=2) + "\n")
PY
    chmod 600 "$OPENCODE_HOME/opencode.json" "$PI_HOME/settings.json" "$PI_SHARED_MCP" "$CURSOR_HOME/mcp.json" 2>/dev/null || true
    echo "   merged MCP configuration into Cursor, OpenCode, and Pi global files"
}

mash_global_gitignore_path() {
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

# Point core.excludesFile at the file we just wrote when it is unset. Git does
# not read ~/.gitignore-global by default (its built-in default is
# $XDG_CONFIG_HOME/git/ignore), so without this the block would be written to an
# inert file and every Mash Programming Skills working-directory ignore would silently not apply.
mash_global_gitignore_bind() {
    local gf="$1" configured
    command -v git >/dev/null 2>&1 || {
        echo "   ⚠️  git not found; cannot bind core.excludesFile. Set it manually:"
        echo "      git config --global core.excludesFile $gf"
        return 0
    }
    configured="$(git config --global --get core.excludesFile 2>/dev/null || true)"
    if [ -n "$configured" ]; then
        return 0
    fi
    if git config --global core.excludesFile "$gf"; then
        echo "   core.excludesFile was unset; set it to $gf so the block takes effect."
    else
        echo "   ⚠️  Could not set core.excludesFile. Git will not read $gf until you run:"
        echo "      git config --global core.excludesFile $gf"
    fi
}

mash_global_gitignore_ensure() {
    local gf
    gf="$(mash_global_gitignore_path)"
    mkdir -p "$(dirname "$gf")"
    mash_global_gitignore_bind "$gf"
    python3 - "$gf" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text() if path.exists() else ""
start = text.find("# Mash Programming Skills\n")
if start >= 0:
    end_marker = text.find("# End Mash Programming Skills", start)
    if end_marker >= 0:
        end = text.find("\n", end_marker)
        end = len(text) if end < 0 else end + 1
        text = text[:start] + text[end:]

block = """# Mash Programming Skills
# Added by mash-programming-skills/install.sh. Remove this block to stop ignoring.
.mash/brainstorms/
.mash/plans/
.mash/designs/
.mash/design-system/
.mash/solutions/
.mash/insights/
.mash/qa/
.mash/parallel/
.mash/deepening/
.mash/loops/
.mash/ideation/
.mash/maintainer-manifest.json
# End Mash Programming Skills
"""
text = text.rstrip() + "\n\n" + block
path.write_text(text)
PY
    echo "-> Updated global gitignore: $gf"
}

write_global_install_markers() {
    mkdir -p "$MASH_CONFIG_DIR"
    cp "$SOURCE_ROOT/uninstall.sh" "$MASH_CONFIG_DIR/uninstall.sh"
    chmod +x "$MASH_CONFIG_DIR/uninstall.sh"
    local example
    example="$(mktemp)"
    mash_mcp_catalog_json >"$example"
    python3 "$MANAGED_ARTIFACTS" write \
        "$MASH_CONFIG_DIR/install-manifest.json" \
        "$INSTALL_VERSION" \
        "$SOURCE_ROOT" \
        "$CURSOR_HOME" \
        "$OPENCODE_HOME" \
        "$PI_HOME" \
        "$HOME/.agents" \
        "$MASH_CONFIG_DIR" \
        "$example"
    rm -f "$example"
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
        "$OPENCODE_HOME/plugin/mash-hindsight-daemon.ts"
        "$OPENCODE_HOME/opencode.json"
        "$PI_HOME/AGENTS.md"
        "$PI_HOME/skills"
        "$HOME/.agents"
        "$PI_HOME/extensions/mash-hindsight-daemon.ts"
        "$PI_HOME/scripts/ensure-hindsight-daemon.sh"
        "$PI_SHARED_MCP"
        "$MASH_CONFIG_DIR/AGENTS.md"
        "$MASH_CONFIG_DIR/always-on-rules.md"
        "$PI_HOME/APPEND_SYSTEM.md"
        "$MASH_CONFIG_DIR/references/model-tiers.md"
        "$MASH_CONFIG_DIR/references/markdown-rendering.md"
        "$MASH_CONFIG_DIR/install-manifest.json"
        "$MASH_CONFIG_DIR/uninstall.sh"
    )
    if [ "$WRITE_PIN" = true ]; then
        required+=("$MASH_CONFIG_DIR/agentic-env.json" "$MASH_CONFIG_DIR/hindsight-pin")
    fi
    if [ "${MASH_SKIP_SKILL_DEPS:-0}" != 1 ]; then
        local dep_src dep_name
        for dep_src in "$SOURCE_ROOT"/src/skills/*/; do
            [ -d "$dep_src" ] || continue
            dep_name="$(basename "$dep_src")"
            if [ -f "$dep_src/package.json" ]; then
                required+=("$MASH_CONFIG_DIR/node_modules/$dep_name/node_modules")
            fi
            if [ -f "$dep_src/requirements.txt" ]; then
                required+=("$MASH_CONFIG_DIR/venvs/$dep_name/bin/python")
            fi
        done
    fi
    for path in "${required[@]}"; do
        if [ ! -e "$path" ]; then
            echo "missing: $path"
            missing=$((missing + 1))
        fi
    done
    if ! python3 "$MANAGED_ARTIFACTS" check "$MASH_CONFIG_DIR/install-manifest.json" "$SOURCE_ROOT"; then
        echo "missing: current managed-artifact inventory in install-manifest.json"
        missing=$((missing + 1))
    fi
    report_automation_tools || true
    if [ "$missing" -eq 0 ]; then
        echo "Mash Programming Skills global installation present ($INSTALL_VERSION)"
        return 0
    fi
    echo "Mash Programming Skills global installation incomplete ($missing missing)"
    return 1
}

install_global_payload() {
    echo "-> Pruning artifacts removed from the Mash Programming Skills source tree..."
    python3 "$MANAGED_ARTIFACTS" prune \
        "$MASH_CONFIG_DIR/install-manifest.json" \
        "$SOURCE_ROOT" \
        "$CURSOR_HOME" \
        "$OPENCODE_HOME" \
        "$PI_HOME" \
        "$HOME/.agents" \
        "$MASH_CONFIG_DIR"

    echo "-> Installing global Cursor rules, skills, and agents..."
    copy_global_rules
    copy_global_skills
    copy_global_agents
    copy_global_hooks

    echo "-> Installing global OpenCode skills, agents, and plugin..."
    copy_global_opencode_runtime

    echo "-> Installing global Pi skills, agents, and warm-start..."
    copy_global_pi_runtime

    echo "-> Installing Mash Programming Skills guidance, pins, and contract references..."
    write_global_guidance
    write_global_pins
    install_global_references
    write_global_install_markers

    echo "-> Updating machine-global Git excludes..."
    mash_global_gitignore_ensure

    echo "-> Merging global MCP configuration..."
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

# Global skill dependencies are installed once under ~/.config/mash and symlinked
# into each IDE's copy, so a skill's deps are not triplicated across three homes.

link_shared_skill_dep() {
    local target="$1" link="$2"
    [ -e "$target" ] || return 0
    mkdir -p "$(dirname "$link")"
    # Replace a previous real directory or stale symlink. `rm -rf` on a symlink
    # removes the link itself, never the shared target.
    if [ -e "$link" ] || [ -L "$link" ]; then
        rm -rf -- "$link"
    fi
    ln -s "$target" "$link"
}

install_global_skill_deps() {
    local src sname store venv ide_root link

    for src in "$SOURCE_ROOT"/src/skills/*/; do
        [ -d "$src" ] || continue
        sname="$(basename "$src")"

        # npm: one install per skill, shared by all three IDE copies.
        if [ -f "$src/package.json" ]; then
            store="$MASH_CONFIG_DIR/node_modules/$sname"
            mkdir -p "$store"
            cp "$src/package.json" "$store/package.json"
            if [ -f "$src/package-lock.json" ]; then
                cp "$src/package-lock.json" "$store/package-lock.json"
            fi
            install_npm_deps "$store" "global skill $sname"
            for ide_root in "$CURSOR_HOME/skills" "$OPENCODE_HOME/skills" "$PI_HOME/skills"; do
                [ -d "$ide_root/$sname" ] || continue
                link_shared_skill_dep "$store/node_modules" "$ide_root/$sname/node_modules"
            done
        fi

        # Python: one venv per skill, shared by all three IDE copies.
        if [ -f "$src/requirements.txt" ]; then
            venv="$MASH_CONFIG_DIR/venvs/$sname"
            if [ ! -x "$venv/bin/python" ]; then
                mkdir -p "$MASH_CONFIG_DIR/venvs"
                if command -v uv >/dev/null 2>&1; then
                    uv venv "$venv" >/dev/null 2>&1 || true
                fi
                if [ ! -x "$venv/bin/python" ]; then
                    python3 -m venv "$venv" || {
                        echo "   ⚠️  could not create a virtualenv for $sname (continuing)"
                        continue
                    }
                fi
            fi
            echo "-> pip install: global skill $sname"
            if command -v uv >/dev/null 2>&1; then
                uv pip install --python "$venv/bin/python" -q -r "$src/requirements.txt" ||
                    echo "   ⚠️  pip install failed for $sname (continuing)"
            else
                "$venv/bin/python" -m pip install -q -r "$src/requirements.txt" ||
                    echo "   ⚠️  pip install failed for $sname (continuing)"
            fi
            # Convention: a skill that pulls in Playwright gets the Chromium build
            # it needs. Playwright caches browsers machine-wide, so this downloads
            # once regardless of how many skills use it.
            if [ -x "$venv/bin/playwright" ]; then
                "$venv/bin/playwright" install chromium >/dev/null 2>&1 ||
                    echo "   ⚠️  playwright chromium install failed for $sname (continuing)"
            fi
            for ide_root in "$CURSOR_HOME/skills" "$OPENCODE_HOME/skills" "$PI_HOME/skills"; do
                [ -d "$ide_root/$sname" ] || continue
                link_shared_skill_dep "$venv" "$ide_root/$sname/.venv"
            done
        fi
    done
}

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

    if [ "${MASH_APT_UPDATED:-0}" != 1 ]; then
        if command -v sudo >/dev/null 2>&1; then
            sudo apt-get update -qq || true
        else
            apt-get update -qq || true
        fi
        MASH_APT_UPDATED=1
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

# Agent harnesses that can run Mash Programming Skills and act as mash-parallel workers.
# Mash Programming Skills does not install these: each has its own installer, auth, and licence.
# Installation continues without one, but Mash Programming Skills have nothing to run in.
MASH_HARNESSES="pi opencode cursor-agent codex claude"

check_agent_harness() {
    local found="" missing="" harness
    for harness in $MASH_HARNESSES; do
        if command -v "$harness" >/dev/null 2>&1; then
            found="$found $harness"
        else
            missing="$missing $harness"
        fi
    done

    if [ -n "$found" ]; then
        echo "   agent harnesses present:$found"
        [ -n "$missing" ] && echo "   not installed (optional):$missing"
        return 0
    fi

    echo "   ⚠️  No agent harness found on PATH (looked for:$MASH_HARNESSES)."
    echo "      Mash Programming Skills installs skills and rules, not harnesses. Without one, nothing loads them,"
    echo "      and 'mash-parallel' has no worker to delegate tasks to."
    echo "      Install at least one, then re-run this script to finish harness-dependent setup"
    echo "      (Pi extensions install only when the 'pi' CLI is present)."
    return 0
}

# Providers accepted by Hindsight 0.8, including none (no LLM).
HINDSIGHT_LLM_PROVIDERS=(
    openai
    openai-responses
    openai-codex
    claude-code
    cursor
    github-copilot
    anthropic
    gemini
    groq
    minimax
    deepseek
    zai
    opencode-go
    meta
    nous
    xai-oauth
    fireworks
    ollama
    ollama-cloud
    lmstudio
    llamacpp
    vertexai
    bedrock
    litellm
    litellmrouter
    volcano
    openrouter
    requesty
    atlas
    none
)

# Piped stdin is the script, so prompts use /dev/tty. A device node can still
# fail to open when this process has no controlling terminal; that keeps the
# unattended path: Hindsight from the environment, every example MCP server.
prompts_available() {
    { : </dev/tty; } >/dev/null 2>&1
}

tty_read() {
    local reply=""
    IFS= read -r reply </dev/tty || return 1
    printf '%s' "$reply"
}

prompt_yes() {
    local reply
    printf '%s' "$1" >/dev/tty
    reply="$(tty_read)" || return 1
    reply="$(printf '%s' "$reply" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
    case "$reply" in
        y | yes) return 0 ;;
        *) return 1 ;;
    esac
}

mcp_select() {
    case " ${MASH_MCP_SELECTED} " in
        *" $1 "*) ;;
        *) MASH_MCP_SELECTED="${MASH_MCP_SELECTED:+$MASH_MCP_SELECTED }$1" ;;
    esac
}

mcp_was_selected() {
    case " ${MASH_MCP_SELECTED} " in
        *" $1 "*) return 0 ;;
        *) return 1 ;;
    esac
}

hindsight_prompt_abort() {
    unset HINDSIGHT_API_LLM_PROVIDER HINDSIGHT_API_LLM_MODEL HINDSIGHT_API_LLM_API_KEY HINDSIGHT_API_LLM_BASE_URL
    unset MASH_HINDSIGHT_PROMPTED
}

prompt_hindsight_llm() {
    local i choice provider model key base count
    if [ -f "${HOME}/.hindsight/embed" ] || [ -f "${HOME}/.hindsight/config.env" ]; then
        echo "-> Hindsight is already configured; leaving it in place."
        return 0
    fi

    count="${#HINDSIGHT_LLM_PROVIDERS[@]}"
    while true; do
        printf '\n-> Hindsight LLM provider\n' >/dev/tty
        printf '   none stores memories without an LLM.\n' >/dev/tty
        i=1
        for provider in "${HINDSIGHT_LLM_PROVIDERS[@]}"; do
            printf '   %2d) %s\n' "$i" "$provider" >/dev/tty
            i=$((i + 1))
        done
        printf '   Provider number: ' >/dev/tty
        choice="$(tty_read)" || {
            hindsight_prompt_abort
            return 0
        }
        choice="$(printf '%s' "$choice" | tr -d '[:space:]')"
        case "$choice" in
            '' | *[!0-9]*)
                printf '   Enter a number from the list.\n' >/dev/tty
                continue
                ;;
        esac
        if [ "$((10#$choice))" -ge 1 ] && [ "$((10#$choice))" -le "$count" ]; then
            break
        fi
        printf '   Enter a number from the list.\n' >/dev/tty
    done

    provider="${HINDSIGHT_LLM_PROVIDERS[$((10#$choice - 1))]}"
    unset HINDSIGHT_API_LLM_MODEL HINDSIGHT_API_LLM_API_KEY HINDSIGHT_API_LLM_BASE_URL
    export HINDSIGHT_API_LLM_PROVIDER="$provider"
    if [ "$provider" = none ]; then
        MASH_HINDSIGHT_PROMPTED=yes
        echo "   Hindsight provider: none."
        return 0
    fi

    printf '   Model (Enter for the provider default): ' >/dev/tty
    model="$(tty_read)" || {
        hindsight_prompt_abort
        return 0
    }
    if [ -n "$model" ]; then
        export HINDSIGHT_API_LLM_MODEL="$model"
    fi

    case "$provider" in
        ollama | lmstudio | llamacpp | vertexai) ;;
        *)
            while true; do
                printf '   API key: ' >/dev/tty
                key="$(tty_read)" || {
                    hindsight_prompt_abort
                    return 0
                }
                key="$(printf '%s' "$key" | tr -d '[:space:]')"
                if [ -n "$key" ]; then
                    export HINDSIGHT_API_LLM_API_KEY="$key"
                    break
                fi
                printf '   An API key is required for %s.\n' "$provider" >/dev/tty
            done
            ;;
    esac

    printf '   Base URL (Enter to leave empty): ' >/dev/tty
    base="$(tty_read)" || {
        hindsight_prompt_abort
        return 0
    }
    base="$(printf '%s' "$base" | tr -d '[:space:]')"
    if [ -n "$base" ]; then
        export HINDSIGHT_API_LLM_BASE_URL="$base"
    fi
    MASH_HINDSIGHT_PROMPTED=yes
    echo "   Hindsight provider: ${provider}."
}

prompt_mcp_github() {
    local token pasted
    prompt_yes "   Include github? [y/N] " || return 0
    token="$(mash_resolve_env_value GITHUB_TOKEN)"
    if [ -n "$token" ]; then
        printf '   Use the GITHUB_TOKEN already set? [Y/n] ' >/dev/tty
        pasted="$(tty_read)" || return 0
        pasted="$(printf '%s' "$pasted" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
        case "$pasted" in
            '' | y | yes)
                MASH_GITHUB_TOKEN="$token"
                mcp_select github
                echo "   GitHub MCP server will use the token from the environment."
                return 0
                ;;
        esac
    else
        printf '   Create a fine-grained token: https://github.com/settings/personal-access-tokens/new\n' >/dev/tty
        printf '   Scopes: Contents read, Pull requests read (write to post updates), Issues write to file issues.\n' >/dev/tty
        printf '   A classic token with the repo scope also works.\n' >/dev/tty
    fi
    printf '   GitHub token (Enter to skip github): ' >/dev/tty
    pasted="$(tty_read)" || return 0
    pasted="$(printf '%s' "$pasted" | tr -d '[:space:]')"
    if [ -z "$pasted" ]; then
        echo "   Skipped github."
        return 0
    fi
    MASH_GITHUB_TOKEN="$pasted"
    mcp_select github
    echo "   GitHub MCP server will be configured."
}

prompt_mcp_installable() {
    local name="$1" bin="$2" flag="$3" pin reported decision
    prompt_yes "   Include ${name}? [y/N] " || return 0
    if [ "$bin" = sentrux ]; then
        host_path
        if command -v sentrux >/dev/null 2>&1 && sentrux --version >/dev/null 2>&1; then
            mcp_select "$name"
            return 0
        fi
    else
        reported="$("$bin" --version 2>/dev/null || true)"
        decision="$(python3 "$MANAGED_ARTIFACTS" install-needed "$bin" "$reported")"
        if [ "$decision" != yes ]; then
            mcp_select "$name"
            return 0
        fi
        pin="$(python3 "$MANAGED_ARTIFACTS" pin "$bin")"
    fi
    if [ -n "${pin:-}" ]; then
        prompt_yes "   Install ${bin} ${pin}? [y/N] " || {
            echo "   Skipped ${name}."
            return 0
        }
    else
        prompt_yes "   Install ${bin}? [y/N] " || {
            echo "   Skipped ${name}."
            return 0
        }
    fi
    case "$flag" in
        sentrux) MASH_INSTALL_SENTRUX=yes ;;
        cua-driver) MASH_INSTALL_CUA_DRIVER=yes ;;
        agent-browser) MASH_INSTALL_AGENT_BROWSER=yes ;;
    esac
    mcp_select "$name"
}

prompt_mcp_chrome() {
    prompt_yes "   Include chrome-devtools? [y/N] " || return 0
    if ! command -v npx >/dev/null 2>&1; then
        echo "   npx is absent. chrome-devtools will be written and will fail until Node is installed."
    fi
    mcp_select chrome-devtools
}

prompt_mcp_servers() {
    local name names
    names="$(mash_mcp_catalog_json | python3 -c 'import json,sys
for name in json.load(sys.stdin)["mcpServers"]:
    print(name)')"
    printf '\n-> MCP servers\n' >/dev/tty
    while IFS= read -r name; do
        [ -n "$name" ] || continue
        case "$name" in
            github) prompt_mcp_github ;;
            context7)
                if prompt_yes "   Include context7? [y/N] "; then
                    mcp_select context7
                fi
                ;;
            sentrux) prompt_mcp_installable sentrux sentrux sentrux ;;
            cua-driver) prompt_mcp_installable cua-driver cua-driver cua-driver ;;
            agent-browser) prompt_mcp_installable agent-browser agent-browser agent-browser ;;
            chrome-devtools) prompt_mcp_chrome ;;
            *)
                if prompt_yes "   Include ${name}? [y/N] "; then
                    mcp_select "$name"
                fi
                ;;
        esac
    done <<<"$names"
    return 0
}

prompt_install_choices() {
    MASH_PROMPTS=no
    MASH_MCP_SELECTED=""
    MASH_INSTALL_SENTRUX=no
    MASH_INSTALL_CUA_DRIVER=no
    MASH_INSTALL_AGENT_BROWSER=no
    if ! prompts_available; then
        echo "   No terminal for install prompts; keeping unattended Hindsight and MCP setup."
        return 0
    fi
    MASH_PROMPTS=yes
    prompt_hindsight_llm
    prompt_mcp_servers
}

report_automation_tools() {
    PATH="${HOME}/.local/bin:${PATH}"
    local name pin reported decision
    for name in cua-driver agent-browser; do
        pin="$(python3 "$MANAGED_ARTIFACTS" pin "$name")"
        reported="$("$name" --version 2>/dev/null || true)"
        decision="$(python3 "$MANAGED_ARTIFACTS" install-needed "$name" "$reported")"
        if [ "$decision" = yes ]; then
            echo "automation: $name wants $pin (reported: ${reported:-missing})"
        else
            echo "automation: $name $pin present"
        fi
    done
    pin="$(python3 "$MANAGED_ARTIFACTS" pin chrome-devtools-mcp)"
    if command -v npx >/dev/null 2>&1; then
        echo "automation: chrome-devtools-mcp@$pin uses npx; no binary install"
    else
        echo "automation: npx absent; chrome-devtools-mcp@$pin unresolved"
    fi
}

if [ "$CHECK_ONLY" = true ]; then
    run_global_check
    exit $?
fi

echo "-> Checking for an agent harness..."
check_agent_harness
prompt_install_choices

if [ "${MASH_SKIP_MACHINE_TOOLS:-0}" != 1 ]; then
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

    echo "-> Installing Sentrux CLI once on this machine (required for mash-plan / mash-work / mash-qa)..."
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
            echo "      Install manually: cargo install sentrux  (see mash-sentrux skill)"
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

# --- git-flow (mash-pr / mash-work / mash-debug / mash-release) ---
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

    echo "-> Installing git-flow once on this machine (required for mash-pr / mash-release)..."
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

# --- bumpversion (mash-release / scripts/release.sh) ---
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

    echo "-> Installing bumpversion once on this machine (required for mash-release)..."
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
    local pin_file="$MASH_CONFIG_DIR/hindsight-pin"
    if [ -f "$pin_file" ]; then
        tr -d '[:space:]' <"$pin_file"
    else
        printf '%s' "$HINDSIGHT_PIN_VALUE"
    fi
}

# Seed ~/.hindsight/embed from the installer template when missing. Fills every
# KEY= from SOURCE_ROOT/.env (then process env). Never overwrites existing config.
seed_hindsight_embed_if_needed() {
    local template dest provider status=0

    if hindsight_embed_configured; then
        return 0
    fi

    template="$(mktemp)"
    mash_hindsight_embed_template >"$template"

    if [ "${MASH_HINDSIGHT_PROMPTED:-}" = yes ]; then
        provider="${HINDSIGHT_API_LLM_PROVIDER:-}"
        if [ -z "$provider" ]; then
            echo "   ⚠️  Hindsight provider was not chosen."
            rm -f "$template"
            return 1
        fi
    else
        provider="$(mash_resolve_env_value HINDSIGHT_API_LLM_PROVIDER)"
        provider="${provider:-openai}"
    fi

    dest="${HOME}/.hindsight/embed"
    case "$provider" in
        none | ollama | lmstudio | llamacpp | vertexai)
            if ! seed_dotenv_from_example "$template" "$dest" ""; then
                echo "   ⚠️  Failed to seed ~/.hindsight/embed."
                status=1
            fi
            ;;
        *)
            if ! seed_dotenv_from_example "$template" "$dest" "HINDSIGHT_API_LLM_API_KEY"; then
                echo "   Hindsight not configured yet (no API key for seed)."
                echo "      Set HINDSIGHT_* keys in $SOURCE_ROOT/.env or answer the installer prompts,"
                echo "      then re-run install.sh to seed ~/.hindsight/embed."
                echo "      Or run interactive setup: uvx hindsight-embed@$(read_hindsight_pin) configure"
                status=1
            fi
            ;;
    esac

    rm -f "$template"
    if [ "$status" -ne 0 ]; then
        return 1
    fi
    echo "   Seeded ~/.hindsight/embed (provider=${provider})."
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
# enters or modifies a repository workspace. Set MASH_SKIP_SKILL_DEPS=1 for a
# filesystem-only install/test.
if [ "${MASH_SKIP_SKILL_DEPS:-0}" != 1 ]; then
    install_global_skill_deps
fi

if [ "${MASH_SKIP_MACHINE_TOOLS:-0}" != 1 ]; then
    install_bumpversion || true
    install_gitchangelog || true
    install_git_flow || true
    if [ "${MASH_PROMPTS:-no}" != yes ] || [ "${MASH_INSTALL_SENTRUX:-no}" = yes ]; then
        install_sentrux || true
    fi
    install_pi_subagents || true
    install_pi_mcp_adapter || true
    install_pi_ask_user || true
    check_hindsight_embed || true
fi

# --- Automation tools (CUA Driver, agent-browser, Chrome DevTools MCP) ---
# Pins live in scripts/managed_artifacts.py. A failed install warns and still
# returns success so skill copy and MCP merge are not rolled back.
# report_automation_tools is defined above the --check exit.

install_automation_tools() {
    host_path
    local cua_pin agent_pin chrome_pin reported decision
    cua_pin="$(python3 "$MANAGED_ARTIFACTS" pin cua-driver)"
    agent_pin="$(python3 "$MANAGED_ARTIFACTS" pin agent-browser)"
    chrome_pin="$(python3 "$MANAGED_ARTIFACTS" pin chrome-devtools-mcp)"

    if [ "${MASH_PROMPTS:-no}" != yes ] || [ "${MASH_INSTALL_CUA_DRIVER:-no}" = yes ]; then
        reported="$(cua-driver --version 2>/dev/null || true)"
        decision="$(python3 "$MANAGED_ARTIFACTS" install-needed cua-driver "$reported")"
        if [ "$decision" = yes ]; then
            echo "-> Installing CUA Driver ${cua_pin}..."
            if ! CUA_DRIVER_RS_VERSION="$cua_pin" /bin/bash -c "$(curl -fsSL https://cua.ai/driver/install.sh)"; then
                echo "   ⚠️  CUA Driver ${cua_pin} install failed."
                echo "      Retry with CUA_DRIVER_RS_VERSION=${cua_pin} and https://cua.ai/driver/install.sh"
            fi
        else
            echo "-> CUA Driver ${cua_pin} already present; skipping install"
        fi
    fi

    if [ "${MASH_PROMPTS:-no}" != yes ] || [ "${MASH_INSTALL_AGENT_BROWSER:-no}" = yes ]; then
        reported="$(agent-browser --version 2>/dev/null || true)"
        decision="$(python3 "$MANAGED_ARTIFACTS" install-needed agent-browser "$reported")"
        if [ "$decision" = yes ]; then
            echo "-> Installing agent-browser ${agent_pin}..."
            if ! command -v npm >/dev/null 2>&1; then
                echo "   ⚠️  npm is absent. Retry: npm install -g agent-browser@${agent_pin}"
            elif ! npm install -g "agent-browser@${agent_pin}"; then
                echo "   ⚠️  agent-browser@${agent_pin} install failed. Retry: npm install -g agent-browser@${agent_pin}"
            elif ! agent-browser install; then
                echo "   ⚠️  agent-browser browser install failed. Retry: agent-browser install"
            fi
        else
            echo "-> agent-browser ${agent_pin} already present; skipping install"
        fi
    fi

    if [ "${MASH_PROMPTS:-no}" != yes ] || mcp_was_selected chrome-devtools; then
        if ! command -v npx >/dev/null 2>&1; then
            echo "   ⚠️  npx is absent. chrome-devtools-mcp@${chrome_pin} stays unresolved."
        elif ! npm view "chrome-devtools-mcp@${chrome_pin}" version >/dev/null 2>&1; then
            echo "   ⚠️  Cannot resolve chrome-devtools-mcp@${chrome_pin}."
        else
            echo "-> chrome-devtools-mcp@${chrome_pin} resolves through npx; no binary install"
        fi
    fi

    if [ "${MASH_PROMPTS:-no}" != yes ] || mcp_was_selected cua-driver; then
        echo "   On macOS, a person must grant Accessibility and Screen Recording on CuaDriver.app, then relaunch that app."
    fi
    return 0
}

if [ "${MASH_SKIP_MACHINE_TOOLS:-0}" != 1 ]; then
    install_automation_tools || true
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
inventory_cli "gpg (only needed if you sign commits yourself)" gpg
echo "   not packages: gh auth login, GPG secret keys (not generated), Docker daemon up"

echo ""
echo "Mash Programming Skills global environment installed successfully!"
echo "   Cursor: ~/.cursor/rules, ~/.cursor/skills, ~/.cursor/agents, and global hooks."
echo "   OpenCode: ~/.config/opencode/skills, agents, instructions, and native Hindsight plugin."
echo "   Pi: ~/.pi/agent/skills plus ~/.agents agents and global Hindsight extension."
echo "   Mash Programming Skills state: ~/.config/mash (guidance, pins, contract references, manifest)."
echo "   No repository files or IDE trees were written. Skills create repo files/directories lazily when invoked."
echo "   Machine-once CLIs skipped if already on PATH: git, make, curl, rsync, jq, rg, gh, uv, bun, gitchangelog, bumpversion, git-flow, sentrux, hindsight-embed."
echo "   Pi extensions installed once when the pi CLI is present: pi-subagents, pi-mcp-adapter, pi-ask-user."
