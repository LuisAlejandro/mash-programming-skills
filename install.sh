#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="$(pwd)"
INSTALL_ROOT_BASENAME="$(basename "$INSTALL_ROOT")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="${ROSEY_AGENTIC_ENV:-$SCRIPT_DIR}"
VERSION_FILE="$SOURCE_ROOT/VERSION"
INSTALL_VERSION="0.1.0"
CHECK_ONLY=false
WRITE_PIN=true
CREATE_AGENTS=true

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
        --agents)
            CREATE_AGENTS=true
            shift
            ;;
        --no-agents)
            CREATE_AGENTS=false
            shift
            ;;
        -h | --help)
            echo "Usage: install.sh [--check] [--version] [--write-pin|--no-write-pin] [--agents|--no-agents]"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Live-homes: sole-user agent homes that are also live working directories.
# Nothing may change branches or merge state, so they write .cursorrules instead
# of AGENTS.md, skip docker-via-make / rosey-pr / rosey-parallel /
# rosey-epic-decompose, and get live-home skill + rule overlays.
is_livehome_install() {
    case "$INSTALL_ROOT_BASENAME" in
        .hermes | .openclaw | rudi-hermes | winston-openclaw | \
        rosey-maintainer-tools | tetra-actions-runner)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

apply_livehome_skill_overlay() {
    local dest="$1"
    local sname="$2"
    local overlay
    is_livehome_install || return 0
    overlay="$SOURCE_ROOT/.cursor/skills-livehome/$sname"
    [ -d "$overlay" ] || return 0
    mkdir -p "$dest/references"
    # Full forks. Overlay replaces dest SKILL.md in place.
    if [ -f "$SOURCE_ROOT/.cursor/skills-livehome/LIVEHOME.md" ]; then
        cp "$SOURCE_ROOT/.cursor/skills-livehome/LIVEHOME.md" "$dest/references/livehome.md"
    fi
    cp -R "$overlay/." "$dest/"
    echo "   Live-home skill overlay: $sname"
}

apply_livehome_rules() {
    is_livehome_install || return 0
    rm -f .cursor/rules/docker-via-make.mdc
    if [ -f "$SOURCE_ROOT/.cursor/rules-livehome/rosey-workflow-gates.mdc" ]; then
        mkdir -p .cursor/rules
        cp "$SOURCE_ROOT/.cursor/rules-livehome/rosey-workflow-gates.mdc" .cursor/rules/rosey-workflow-gates.mdc
        echo "   Live-home rule overlay: rosey-workflow-gates (docker-via-make skipped)"
    fi
}

# Write the always-apply Cursor rules into a per-IDE destination, rewriting Cursor
# paths to that IDE's native paths. Used by OpenCode (.opencode/rules/*.mdc) and Pi
# (.pi/APPEND_SYSTEM.md). The rewrite function is passed as $2.
write_always_apply_rules() {
    local dest_dir="$1"
    local rewrite_fn="$2"
    [ -d "$SOURCE_ROOT/.cursor/rules" ] || return 0
    mkdir -p "$dest_dir"
    local mdc
    for mdc in "$SOURCE_ROOT"/.cursor/rules/*.mdc; do
        [ -f "$mdc" ] || continue
        local rname
        rname="$(basename "$mdc" .mdc)"
        if is_livehome_install && [ "$rname" = "docker-via-make" ]; then
            continue
        fi
        if is_livehome_install && [ -f "$SOURCE_ROOT/.cursor/rules-livehome/${rname}.mdc" ]; then
            mdc="$SOURCE_ROOT/.cursor/rules-livehome/${rname}.mdc"
        fi
        if fm_always_apply "$mdc"; then
            cp "$mdc" "$dest_dir/$rname.mdc"
            "$rewrite_fn" "$dest_dir/$rname.mdc"
        fi
    done
}

# Write the always-apply Cursor rules into a single destination file (e.g.
# .pi/APPEND_SYSTEM.md), rewriting Cursor paths via the given rewrite function.
write_always_apply_rules_to_file() {
    local dest="$1" rewrite_fn="$2"
    [ -d "$SOURCE_ROOT/.cursor/rules" ] || return 0
    : > "$dest"
    {
        echo "# Rosey Agentic Environment — always-on rules"
        echo
        echo "Auto-generated from .cursor/rules/*.mdc with alwaysApply: true."
        echo "Do not edit by hand; re-run install.sh to refresh."
        echo
    } >> "$dest"
    local mdc
    for mdc in "$SOURCE_ROOT"/.cursor/rules/*.mdc; do
        [ -f "$mdc" ] || continue
        local rname
        rname="$(basename "$mdc" .mdc)"
        if is_livehome_install && [ "$rname" = "docker-via-make" ]; then
            continue
        fi
        if is_livehome_install && [ -f "$SOURCE_ROOT/.cursor/rules-livehome/${rname}.mdc" ]; then
            mdc="$SOURCE_ROOT/.cursor/rules-livehome/${rname}.mdc"
        fi
        if fm_always_apply "$mdc"; then
            local rdesc rbody
            rdesc="$(fm_field "$mdc" description)"
            rbody="$(fm_body "$mdc")"
            {
                echo "---"
                echo "# $rname"
                echo "## $rdesc"
                echo
                printf '%s\n' "$rbody"
                echo
            } >> "$dest"
        fi
    done
    "$rewrite_fn" "$dest"
}

echo "Installing Rosey Agentic Environment..."
echo "-> Installing from $SOURCE_ROOT into $INSTALL_ROOT..."

if [ "$INSTALL_ROOT" = "$SOURCE_ROOT" ] && [ "$CHECK_ONLY" = false ]; then
    echo "Error: Cannot install the Rosey Agentic Environment into its own source repository." >&2
    echo "   You are currently in the rosey-agentic-env source directory ($SOURCE_ROOT)." >&2
    echo "   To install Rosey in a target project, run this script from the target project directory:" >&2
    echo "   /path/to/rosey-agentic-env/install.sh" >&2
    exit 1
fi

if [ ! -d "$SOURCE_ROOT/.cursor" ]; then
    echo "Error: Could not find .cursor directory in $SOURCE_ROOT"
    echo "   Run this script from the rosey-agentic-env repository (install.sh must live beside .cursor/)."
    exit 1
fi

# --- Check mode ---

if [ "$CHECK_ONLY" = true ]; then
    missing=0
    for path in .cursor/rules .cursor/skills .cursor/agents .cursor/mcp.json \
                .github/copilot-instructions.md .github/instructions .github/skills \
                .github/agents .github/hooks/ensure-hindsight-daemon.sh \
                .vscode/mcp.json .vscode/tasks.json rosey/agentic-env.json; do
        if [ ! -e "$path" ]; then echo "missing: $path"; missing=$((missing + 1)); fi
    done
    for path in .opencode/skills .opencode/agents .opencode/rules \
                .opencode/hooks/ensure-hindsight-daemon.sh .opencode/hooks.json opencode.json \
                .pi/skills .pi/agents .pi/APPEND_SYSTEM.md \
                .pi/scripts/ensure-hindsight-daemon.sh .pi/extensions/rosey-hindsight-daemon.ts; do
        if [ ! -e "$path" ]; then echo "missing: $path"; missing=$((missing + 1)); fi
    done
    if [ "$CREATE_AGENTS" = true ]; then
        if is_livehome_install; then
            if [ ! -f .cursorrules ]; then
                echo "missing: .cursorrules (re-run install.sh to write it)"
                missing=$((missing + 1))
            fi
        elif [ ! -f AGENTS.md ]; then
            echo "missing: AGENTS.md (re-run install.sh to write it)"
            missing=$((missing + 1))
        fi
    fi
    if [ "$missing" -eq 0 ]; then
        echo "Rosey Agentic Environment installed ($INSTALL_VERSION)"
        exit 0
    fi
    exit 1
fi

# --- Helpers ---

# Extract frontmatter field value from an .mdc file (handles quoted/unquoted, single/double quotes).
fm_field() {
    local file="$1" field="$2"
    sed -n "/^${field}:[[:space:]]*/{ s/^${field}:[[:space:]]*//; s/^[\"']//; s/[\"']$//; p; q; }" "$file" 2>/dev/null
}

# True if an .mdc rule has alwaysApply: true
fm_always_apply() {
    grep -qE '^alwaysApply:[[:space:]]*true' "$1" 2>/dev/null
}

# Print the body of an .mdc file (everything after the closing --- of frontmatter).
fm_body() {
    awk 'NR==1 && /^---$/ { fm=1; next } fm && /^---$/ { fm=0; body=1; next } body { print }' "$1"
}

# True when a skill should be installed into the current INSTALL_ROOT.
# Project-specific skills declare which root folder basename they require.
skill_should_install() {
    local skill_name="$1"
    case "$skill_name" in
        rosey-dockershelf-maintainer)
            [ "$INSTALL_ROOT_BASENAME" = "dockershelf" ]
            ;;
        add-debian-suite | add-go-version | add-node-version | add-python-version | discover-new-versions | retire-version)
            [ "$INSTALL_ROOT_BASENAME" = "dockershelf-pipeline" ]
            ;;
        rosey-design-catalog | rosey-design-system | rosey-implement-design | rosey-design-candidates | rosey-design-pipeline | rosey-token-resolution)
            case "$INSTALL_ROOT_BASENAME" in
                morphile | wholmaster | luisalejandro.org | landing-template | helpmarket | \
                wholmaster-website | losa | nuncia | whol | collagelabs.org | luisalejandro.github.io | \
                dockershelf-website | saas-template)
                    return 0
                    ;;
                *)
                    return 1
                    ;;
            esac
            ;;
        rosey-maintainer-add | rosey-maintainer-sync | rosey-maintainer-automations)
            [ "$INSTALL_ROOT_BASENAME" = "rosey-maintainer-tools" ]
            ;;
        tailor-cv)
            [ "$INSTALL_ROOT_BASENAME" = "curriculum-vitae" ]
            ;;
        rosey-pr | rosey-parallel | rosey-epic-decompose | rosey-epic-frame | rosey-dogfood)
            ! is_livehome_install
            ;;
        *)
            return 0
            ;;
    esac
}

# True when a skill should be installed for the given IDE tree (cursor|vscode|opencode|pi).
# Default: all. VS Code-only skills skip the Cursor/OpenCode/Pi trees.
skill_install_for_ide() {
    local skill_name="$1"
    local ide="$2"
    case "$skill_name" in
        rosey-design-candidates | rosey-design-pipeline)
            [ "$ide" = "vscode" ]
            ;;
        *)
            return 0
            ;;
    esac
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

# Resolve KEY: process environment, then SOURCE_ROOT/.env, then INSTALL_ROOT/.env.
rosey_resolve_env_value() {
    local key="$1" val=""
    if [ -n "${!key+x}" ] && [ -n "${!key}" ]; then
        printf '%s' "${!key}"
        return 0
    fi
    val="$(rosey_dotenv_get "$SOURCE_ROOT/.env" "$key" 2>/dev/null || true)"
    if [ -z "$val" ]; then
        val="$(rosey_dotenv_get "$INSTALL_ROOT/.env" "$key" 2>/dev/null || true)"
    fi
    printf '%s' "$val"
}

# Seed dest from example: copy comments/blank lines; fill each KEY= from rosey_resolve_env_value.
# Never overwrites an existing dest. Returns 1 if example missing or a required key is empty.
seed_dotenv_from_example() {
    local example="$1" dest="$2" required_key="${3:-}"
    local line key val missing=0

    if [ -f "$dest" ]; then
        return 0
    fi
    if [ ! -f "$example" ]; then
        return 1
    fi

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
                printf '%s=%s\n' "$key" "$val"
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
    return 0
}

# Rewrite .cursor/* path references to their VS Code equivalents in a file.
rewrite_cursor_refs() {
    local file="$1"
    sed -i.bak -E \
        -e 's|\.cursor/rules/([A-Za-z0-9._-]+)\.mdc|.github/instructions/\1.instructions.md|g' \
        -e 's|\.cursor/skills/([A-Za-z0-9._-]+)/SKILL\.md|.github/skills/\1/SKILL.md|g' \
        -e 's|\.cursor/agents/([A-Za-z0-9._-]+)\.md|.github/agents/\1.agent.md|g' \
        -e 's|\.cursor/hooks/([A-Za-z0-9._-]+)\.sh|.github/hooks/\1.sh|g' \
        -e 's|\.cursor/rules/|.github/instructions/|g' \
        -e 's|\.cursor/skills/|.github/skills/|g' \
        -e 's|\.cursor/agents/|.github/agents/|g' \
        -e 's|\.cursor/hooks/|.github/hooks/|g' \
        -e 's|\.cursor/mcp\.json|.vscode/mcp.json|g' \
        -e 's|\.cursor/hindsight-pin|rosey/hindsight-pin|g' \
        -e 's|\.cursor/hooks\.json|.vscode/tasks.json|g' \
        "$file"
    rm -f "${file}.bak"
}

# Rewrite .cursor/* path references to their OpenCode equivalents in a file.
rewrite_cursor_refs_opencode() {
    local file="$1"
    sed -i.bak -E \
        -e 's|\.cursor/skills/([A-Za-z0-9._-]+)/SKILL\.md|.opencode/skills/\1/SKILL.md|g' \
        -e 's|\.cursor/agents/([A-Za-z0-9._-]+)\.md|.opencode/agents/\1.md|g' \
        -e 's|\.cursor/rules/|.opencode/rules/|g' \
        -e 's|\.cursor/skills/|.opencode/skills/|g' \
        -e 's|\.cursor/agents/|.opencode/agents/|g' \
        -e 's|\.cursor/hooks/|.opencode/hooks/|g' \
        -e 's|\.cursor/mcp\.json|opencode.json|g' \
        -e 's|\.cursor/hooks\.json|.opencode/hooks.json|g' \
        -e 's|\.cursor/hindsight-pin|rosey/hindsight-pin|g' \
        "$file"
    rm -f "${file}.bak"
}

# Rewrite .cursor/* path references to their Pi equivalents in a file.
rewrite_cursor_refs_pi() {
    local file="$1"
    sed -i.bak -E \
        -e 's|\.cursor/skills/([A-Za-z0-9._-]+)/SKILL\.md|.pi/skills/\1/SKILL.md|g' \
        -e 's|\.cursor/agents/([A-Za-z0-9._-]+)\.md|.pi/agents/\1.md|g' \
        -e 's|\.cursor/rules/|.pi/rules/|g' \
        -e 's|\.cursor/skills/|.pi/skills/|g' \
        -e 's|\.cursor/agents/|.pi/agents/|g' \
        -e 's|\.cursor/hooks/|.pi/scripts/|g' \
        -e 's|\.cursor/mcp\.json|.pi/mcp.json|g' \
        -e 's|\.cursor/hooks\.json|.pi/hooks.json|g' \
        -e 's|\.cursor/hindsight-pin|rosey/hindsight-pin|g' \
        "$file"
    rm -f "${file}.bak"
}

# Rewrite .cursor/* path references for the Pi APPEND_SYSTEM.md file. Rules are
# concatenated into this single file, so sibling .cursor/rules/*.mdc references
# point back to .pi/APPEND_SYSTEM.md rather than a .pi/rules/ directory.
rewrite_pi_append_refs() {
    local file="$1"
    sed -i.bak -E \
        -e 's|\.cursor/rules/([A-Za-z0-9._-]+)\.mdc|.pi/APPEND_SYSTEM.md|g' \
        -e 's|\.cursor/skills/([A-Za-z0-9._-]+)/SKILL\.md|.pi/skills/\1/SKILL.md|g' \
        -e 's|\.cursor/agents/([A-Za-z0-9._-]+)\.md|.pi/agents/\1.md|g' \
        -e 's|\.cursor/skills/|.pi/skills/|g' \
        -e 's|\.cursor/agents/|.pi/agents/|g' \
        -e 's|\.cursor/hooks/|.pi/scripts/|g' \
        -e 's|\.cursor/mcp\.json|.pi/mcp.json|g' \
        -e 's|\.cursor/hooks\.json|.pi/hooks.json|g' \
        -e 's|\.cursor/hindsight-pin|rosey/hindsight-pin|g' \
        "$file"
    rm -f "${file}.bak"
}

# Upsert Rosey Hindsight folderOpen task into .vscode/tasks.json (merge-safe).
# Copilot Chat has no Cursor-style sessionStart hooks; folder open is the VS Code stand-in.
upsert_vscode_hindsight_task() {
    local tasks_file=".vscode/tasks.json"
    local label="Rosey: ensure Hindsight daemon"
    mkdir -p .vscode
    python3 - "$tasks_file" "$label" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
label = sys.argv[2]
rosey_task = {
    "label": label,
    "type": "shell",
    "command": "${workspaceFolder}/.github/hooks/ensure-hindsight-daemon.sh",
    "problemMatcher": [],
    "presentation": {
        "reveal": "silent",
        "panel": "dedicated",
        "showReuseMessage": False,
        "close": True,
    },
    "runOptions": {"runOn": "folderOpen"},
}

if path.is_file():
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        data = {"version": "2.0.0", "tasks": []}
else:
    data = {"version": "2.0.0", "tasks": []}

if not isinstance(data, dict):
    data = {"version": "2.0.0", "tasks": []}
data.setdefault("version", "2.0.0")
tasks = data.get("tasks")
if not isinstance(tasks, list):
    tasks = []
tasks = [t for t in tasks if not (isinstance(t, dict) and t.get("label") == label)]
tasks.append(rosey_task)
data["tasks"] = tasks
path.write_text(json.dumps(data, indent=2) + "\n")
PY
}

# Rewrite hindsight-pin path in a copied ensure-hindsight-daemon.sh hook script.
patch_hindsight_hook_script() {
    local script="$1"
    [ -f "$script" ] || return 0
    sed -i.bak -E \
        's|local pin_file="\.cursor/hindsight-pin"|local pin_file="rosey/hindsight-pin"|; s|pin_file="\.cursor/hindsight-pin"|pin_file="rosey/hindsight-pin"|' \
        "$script"
    rm -f "${script}.bak"
}

# OpenCode: Claude-format hooks.json + opencode-agent-hooks plugin in opencode.json.
install_opencode_hindsight_warmstart() {
    local hook_src="$SOURCE_ROOT/.cursor/hooks/ensure-hindsight-daemon.sh"
    [ -f "$hook_src" ] || return 0

    mkdir -p .opencode/hooks
    cp "$hook_src" .opencode/hooks/ensure-hindsight-daemon.sh
    chmod +x .opencode/hooks/ensure-hindsight-daemon.sh
    patch_hindsight_hook_script .opencode/hooks/ensure-hindsight-daemon.sh

    cat > .opencode/hooks.json <<'EOF'
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": ".opencode/hooks/ensure-hindsight-daemon.sh",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
EOF

    upsert_opencode_hindsight_config
}

upsert_opencode_hindsight_config() {
    local config_file="opencode.json"
    local plugin="@monks1975/opencode-agent-hooks@1.0.1"
    python3 - "$config_file" "$plugin" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
plugin = sys.argv[2]

if path.is_file():
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        data = {}
else:
    data = {}

if not isinstance(data, dict):
    data = {}

data.setdefault("$schema", "https://opencode.ai/config.json")
plugins = data.get("plugin")
if not isinstance(plugins, list):
    plugins = []
if plugin not in plugins:
    plugins.append(plugin)
data["plugin"] = plugins
path.write_text(json.dumps(data, indent=2) + "\n")
PY
}

# Pi: shell script + session_start extension under .pi/extensions/.
install_pi_hindsight_warmstart() {
    local hook_src="$SOURCE_ROOT/.cursor/hooks/ensure-hindsight-daemon.sh"
    local ext_src="$SOURCE_ROOT/.cursor/hooks-pi/rosey-hindsight-daemon.ts"
    [ -f "$hook_src" ] || return 0

    mkdir -p .pi/scripts .pi/extensions
    cp "$hook_src" .pi/scripts/ensure-hindsight-daemon.sh
    chmod +x .pi/scripts/ensure-hindsight-daemon.sh
    patch_hindsight_hook_script .pi/scripts/ensure-hindsight-daemon.sh

    if [ -f "$ext_src" ]; then
        cp "$ext_src" .pi/extensions/rosey-hindsight-daemon.ts
    fi
}

# --- Shared pin ---

echo "-> Writing shared rosey/hindsight-pin..."
mkdir -p rosey
[ -f "$SOURCE_ROOT/.cursor/hindsight-pin" ] && cp "$SOURCE_ROOT/.cursor/hindsight-pin" rosey/hindsight-pin

# Install the root-relative shared reference tree (.agents/shared/references) once at
# the install root. It is IDE-agnostic: skills reference it as a single root-relative
# path (.agents/shared/references/...) that resolves identically in every tree.
install_shared_refs() {
    [ -d "$SOURCE_ROOT/.agents/shared/references" ] || return 0
    rm -rf .agents/shared
    mkdir -p .agents/shared
    cp -R "$SOURCE_ROOT/.agents/shared/references/." .agents/shared/references/
}

# --- Cursor target ---

install_cursor_tree() {
    echo "-> Cleaning old .cursor files..."
    rm -rf .cursor/rules .cursor/skills .cursor/agents .cursor/hooks .cursor/mcp.json .cursor/hooks.json

    echo "-> Scaffolding .cursor folder..."
    mkdir -p .cursor

    [ -d "$SOURCE_ROOT/.cursor/rules" ] && cp -R "$SOURCE_ROOT/.cursor/rules" .cursor/
    if [ -d "$SOURCE_ROOT/.cursor/skills" ]; then
        mkdir -p .cursor/skills
        local skill_dir sname
        for skill_dir in "$SOURCE_ROOT"/.cursor/skills/*/; do
            [ -d "$skill_dir" ] || continue
            sname="$(basename "$skill_dir")"
            if ! skill_should_install "$sname"; then
                echo "   Skipping skill $sname (not for root folder $INSTALL_ROOT_BASENAME)"
                continue
            fi
            if ! skill_install_for_ide "$sname" cursor; then
                echo "   Skipping skill $sname (Cursor tree; VS Code only)"
                continue
            fi
            cp -R "$skill_dir" ".cursor/skills/$sname"
            apply_livehome_skill_overlay ".cursor/skills/$sname" "$sname"
        done
    fi
    apply_livehome_rules
    [ -d "$SOURCE_ROOT/.cursor/agents" ] && cp -R "$SOURCE_ROOT/.cursor/agents" .cursor/
    # mcp.json is seeded from mcp.json.example + SOURCE_ROOT/.env (see seed_mcp_json_configs).
    [ -f "$SOURCE_ROOT/.cursor/hooks.json" ] && cp "$SOURCE_ROOT/.cursor/hooks.json" .cursor/
    if [ -d "$SOURCE_ROOT/.cursor/hooks" ]; then
        mkdir -p .cursor/hooks
        cp -R "$SOURCE_ROOT/.cursor/hooks/." .cursor/hooks/
        chmod +x .cursor/hooks/*.sh 2>/dev/null || true
    fi
    # Cursor hook script: prefer shared rosey/hindsight-pin, fall back to .cursor/hindsight-pin.
    if [ -f .cursor/hooks/ensure-hindsight-daemon.sh ]; then
        sed -i.bak -E 's|local pin_file="\.cursor/hindsight-pin"|local pin_file="rosey/hindsight-pin"|; s|pin_file="\.cursor/hindsight-pin"|pin_file="rosey/hindsight-pin"|' .cursor/hooks/ensure-hindsight-daemon.sh
        rm -f .cursor/hooks/ensure-hindsight-daemon.sh.bak
    fi
}

# --- VS Code target ---

install_vscode_tree() {
    echo "-> Cleaning old VS Code/Copilot files..."
    rm -rf .github/instructions .github/skills .github/agents .github/hooks .github/copilot-instructions.md .vscode/mcp.json

    echo "-> Scaffolding .github and .vscode folders..."
    mkdir -p .github/instructions .github/skills .github/agents .github/hooks .vscode

    # .vscode/mcp.json is seeded from mcp.json.example + SOURCE_ROOT/.env (see seed_mcp_json_configs).

    # Rules: alwaysApply -> concatenated copilot-instructions.md; others -> .instructions.md
    local copilot_instructions=".github/copilot-instructions.md"
    : > "$copilot_instructions"
    {
        echo "# Rosey Agentic Environment"
        echo
        echo "This repository uses the Rosey Agentic Environment."
        echo "This file intentionally does not store user preferences."
        echo
        echo "Before non-trivial planning, implementation, or review work, follow the"
        echo "always-on guidelines below, then use the on-demand Rosey resources:"
        echo
        echo "- \`.github/instructions/\` (on-demand rules)"
        echo "- \`.github/skills/\` for Rosey workflows"
        echo "- \`.github/agents/\` for specialist reviews"
        echo "- Hindsight pin is shared at \`rosey/hindsight-pin\`"
        echo
        echo "---"
        echo
        echo "## Always-on guidelines"
        echo
        echo "Auto-generated from .cursor/rules/*.mdc with alwaysApply: true."
        echo "Do not edit by hand; re-run install.sh to refresh."
        echo
    } >> "$copilot_instructions"

    local mdc
    for mdc in "$SOURCE_ROOT"/.cursor/rules/*.mdc; do
        [ -f "$mdc" ] || continue
        local name desc body
        name="$(basename "$mdc" .mdc)"
        if is_livehome_install && [ "$name" = "docker-via-make" ]; then
            echo "   Skipping rule $name (live-home host tooling)"
            continue
        fi
        if is_livehome_install && [ -f "$SOURCE_ROOT/.cursor/rules-livehome/${name}.mdc" ]; then
            mdc="$SOURCE_ROOT/.cursor/rules-livehome/${name}.mdc"
        fi
        desc="$(fm_field "$mdc" description)"
        body="$(fm_body "$mdc")"
        if fm_always_apply "$mdc"; then
            {
                echo "---"
                echo "# $name"
                echo "## $desc"
                echo
                printf '%s\n' "$body"
                echo
            } >> "$copilot_instructions"
        else
            local out=".github/instructions/${name}.instructions.md"
            {
                echo "---"
                printf 'description: %s\n' "$desc"
                echo "---"
                echo
                printf '%s\n' "$body"
            } > "$out"
            rewrite_cursor_refs "$out"
        fi
    done

    # Rewrite Cursor paths in the concatenated always-on guidelines to .github/ paths.
    rewrite_cursor_refs "$copilot_instructions"

    # Skills: copy tree, rewrite refs in .md files
    local skill_dir
    for skill_dir in "$SOURCE_ROOT"/.cursor/skills/*/; do
        [ -d "$skill_dir" ] || continue
        local sname
        sname="$(basename "$skill_dir")"
        if ! skill_should_install "$sname"; then
            echo "   Skipping skill $sname (not for root folder $INSTALL_ROOT_BASENAME)"
            continue
        fi
        if ! skill_install_for_ide "$sname" vscode; then
            echo "   Skipping skill $sname (VS Code tree; Cursor only)"
            continue
        fi
        mkdir -p ".github/skills/$sname"
        cp -R "$skill_dir/." ".github/skills/$sname/"
        apply_livehome_skill_overlay ".github/skills/$sname" "$sname"
        # Rewrite .cursor refs in all markdown files of the skill
        find ".github/skills/$sname" -name '*.md' -type f -print0 2>/dev/null | while IFS= read -r -d '' f; do
            rewrite_cursor_refs "$f"
        done
    done

    # Agents: copy .md -> .agent.md, strip color, rewrite refs. Copy .schema.json as-is.
    local agent_file
    for agent_file in "$SOURCE_ROOT"/.cursor/agents/*; do
        [ -e "$agent_file" ] || continue
        local abase
        abase="$(basename "$agent_file")"
        case "$abase" in
            *.md)
                local aname
                aname="${abase%.md}"
                local out=".github/agents/${aname}.agent.md"
                # Strip the `color:` frontmatter line, keep the rest.
                grep -v '^color:' "$agent_file" > "$out"
                rewrite_cursor_refs "$out"
                ;;
            *)
                cp "$agent_file" ".github/agents/$abase"
                ;;
        esac
    done

    # Hindsight warm-start for VS Code: Copilot has no sessionStart hooks.
    # Install the shared script under .github/hooks/ and register a folderOpen task.
    if [ -f "$SOURCE_ROOT/.cursor/hooks/ensure-hindsight-daemon.sh" ]; then
        mkdir -p .github/hooks
        cp "$SOURCE_ROOT/.cursor/hooks/ensure-hindsight-daemon.sh" .github/hooks/ensure-hindsight-daemon.sh
        chmod +x .github/hooks/ensure-hindsight-daemon.sh
        # Rewrite pin path to shared rosey/hindsight-pin
        sed -i.bak -E 's|local pin_file="\.cursor/hindsight-pin"|local pin_file="rosey/hindsight-pin"|; s|pin_file="\.cursor/hindsight-pin"|pin_file="rosey/hindsight-pin"|' .github/hooks/ensure-hindsight-daemon.sh
        rm -f .github/hooks/ensure-hindsight-daemon.sh.bak
        rewrite_cursor_refs .github/hooks/ensure-hindsight-daemon.sh
        upsert_vscode_hindsight_task
    fi
}

# --- OpenCode target ---

install_opencode_tree() {
    echo "-> Cleaning old OpenCode files..."
    rm -rf .opencode/skills .opencode/agents .opencode/rules .opencode/hooks
    rm -f .opencode/hooks.json
    echo "-> Scaffolding .opencode folder..."
    mkdir -p .opencode/skills .opencode/agents .opencode/rules

    # Rules: alwaysApply -> .opencode/rules/*.mdc (opencode-cursor-rules plugin),
    # with Cursor paths rewritten to .opencode/ paths.
    write_always_apply_rules .opencode/rules rewrite_cursor_refs_opencode

    # Skills: copy tree, rewrite refs in .md files
    local skill_dir
    for skill_dir in "$SOURCE_ROOT"/.cursor/skills/*/; do
        [ -d "$skill_dir" ] || continue
        local sname
        sname="$(basename "$skill_dir")"
        if ! skill_should_install "$sname"; then
            echo "   Skipping skill $sname (not for root folder $INSTALL_ROOT_BASENAME)"
            continue
        fi
        if ! skill_install_for_ide "$sname" opencode; then
            echo "   Skipping skill $sname (OpenCode tree; VS Code only)"
            continue
        fi
        mkdir -p ".opencode/skills/$sname"
        cp -R "$skill_dir/." ".opencode/skills/$sname/"
        apply_livehome_skill_overlay ".opencode/skills/$sname" "$sname"
        find ".opencode/skills/$sname" -name '*.md' -type f -print0 2>/dev/null | while IFS= read -r -d '' f; do
            rewrite_cursor_refs_opencode "$f"
        done
    done

    # Agents: copy .md -> .md with frontmatter adapt; copy non-.md assets as-is.
    local agent_file
    for agent_file in "$SOURCE_ROOT"/.cursor/agents/*; do
        [ -e "$agent_file" ] || continue
        local abase
        abase="$(basename "$agent_file")"
        case "$abase" in
            *.md)
                local aname
                aname="${abase%.md}"
                local out=".opencode/agents/${aname}.md"
                # Adapt frontmatter: keep description + body, set mode: subagent,
                # strip Cursor-only lines (color:, tools:, model: inherit).
                {
                    local in_fm=0
                    while IFS= read -r line || [ -n "$line" ]; do
                        if [ "$in_fm" -eq 0 ] && [ "$line" = "---" ]; then
                            in_fm=1
                            printf '%s\n' "$line"
                            continue
                        fi
                        if [ "$in_fm" -eq 1 ] && [ "$line" = "---" ]; then
                            in_fm=0
                            printf 'mode: subagent\n'
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
                    done < "$agent_file"
                } > "$out"
                rewrite_cursor_refs_opencode "$out"
                ;;
            *)
                cp "$agent_file" ".opencode/agents/$abase"
                ;;
        esac
    done

    install_opencode_hindsight_warmstart
}

# --- Pi target ---

install_pi_tree() {
    echo "-> Cleaning old Pi files..."
    rm -rf .pi/skills .pi/agents .pi/APPEND_SYSTEM.md .pi/scripts .pi/extensions
    echo "-> Scaffolding .pi folder..."
    mkdir -p .pi/skills .pi/agents

    # Rules: alwaysApply -> .pi/APPEND_SYSTEM.md (project-local, takes precedence
    # over ~/.pi/agent/APPEND_SYSTEM.md), with Cursor paths rewritten to .pi/ paths.
    write_always_apply_rules_to_file .pi/APPEND_SYSTEM.md rewrite_pi_append_refs

    # Skills: copy tree, rewrite refs in .md files
    local skill_dir
    for skill_dir in "$SOURCE_ROOT"/.cursor/skills/*/; do
        [ -d "$skill_dir" ] || continue
        local sname
        sname="$(basename "$skill_dir")"
        if ! skill_should_install "$sname"; then
            echo "   Skipping skill $sname (not for root folder $INSTALL_ROOT_BASENAME)"
            continue
        fi
        if ! skill_install_for_ide "$sname" pi; then
            echo "   Skipping skill $sname (Pi tree; VS Code only)"
            continue
        fi
        mkdir -p ".pi/skills/$sname"
        cp -R "$skill_dir/." ".pi/skills/$sname/"
        apply_livehome_skill_overlay ".pi/skills/$sname" "$sname"
        find ".pi/skills/$sname" -name '*.md' -type f -print0 2>/dev/null | while IFS= read -r -d '' f; do
            rewrite_cursor_refs_pi "$f"
        done
    done

    # Agents: copy .md -> .md, keep name/description, strip color/tools/model.
    local agent_file
    for agent_file in "$SOURCE_ROOT"/.cursor/agents/*; do
        [ -e "$agent_file" ] || continue
        local abase
        abase="$(basename "$agent_file")"
        case "$abase" in
            *.md)
                local aname
                aname="${abase%.md}"
                local out=".pi/agents/${aname}.md"
                {
                    local in_fm=0
                    while IFS= read -r line || [ -n "$line" ]; do
                        if [ "$in_fm" -eq 0 ] && [ "$line" = "---" ]; then
                            in_fm=1
                            printf '%s\n' "$line"
                            continue
                        fi
                        if [ "$in_fm" -eq 1 ] && [ "$line" = "---" ]; then
                            in_fm=0
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
                    done < "$agent_file"
                } > "$out"
                rewrite_cursor_refs_pi "$out"
                ;;
            *)
                cp "$agent_file" ".pi/agents/$abase"
                ;;
        esac
    done

    install_pi_hindsight_warmstart
}

install_cursor_tree
install_vscode_tree
install_opencode_tree
install_pi_tree

# Shared reference tree is root-relative (.agents/shared/references) and IDE-agnostic.
install_shared_refs

# Seed MCP configs from .cursor/mcp.json.example + GITHUB_TOKEN / OBSIDIAN_API_KEY in SOURCE_ROOT/.env.
seed_mcp_json_configs() {
    local example="$SOURCE_ROOT/.cursor/mcp.json.example"
    local github_token obsidian_key

    if [ ! -f "$example" ]; then
        echo "   ⚠️  No .cursor/mcp.json.example; skipping MCP seed"
        return 0
    fi

    github_token="$(rosey_resolve_env_value GITHUB_TOKEN)"
    obsidian_key="$(rosey_resolve_env_value OBSIDIAN_API_KEY)"

    if [ -z "$github_token" ] && [ -z "$obsidian_key" ]; then
        echo "   ⚠️  GITHUB_TOKEN and OBSIDIAN_API_KEY missing; MCP seed will leave placeholders"
    fi

    _seed_one_mcp_json() {
        local dest="$1" shape="$2"
        # Source checkout: never overwrite an existing local mcp.json.
        if [ "$dest" = "$SOURCE_ROOT/.cursor/mcp.json" ] && [ -f "$dest" ]; then
            return 0
        fi
        python3 - "$example" "$dest" "$shape" "$github_token" "$obsidian_key" <<'PY'
import json
import sys
from pathlib import Path

example, dest, shape, github_token, obsidian_key = sys.argv[1:6]
data = json.loads(Path(example).read_text())

def walk(obj):
    if isinstance(obj, dict):
        return {k: walk(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [walk(v) for v in obj]
    if isinstance(obj, str):
        return (
            obj.replace("$GITHUB_TOKEN", github_token).replace("$OBSIDIAN_API_KEY", obsidian_key)
        )
    return obj

data = walk(data)

if shape == "vscode" and isinstance(data, dict) and "mcpServers" in data and "servers" not in data:
    data["servers"] = data.pop("mcpServers")

if shape in ("opencode", "pi"):
    servers = data.get("mcpServers", {}) if isinstance(data, dict) else {}
    out_servers = {}
    for name, srv in servers.items():
        srv = dict(srv)
        srv.pop("type", None)  # drop Cursor's type: http
        if "command" in srv:
            if shape == "opencode":
                args = srv.pop("args", [])
                cmd = srv.pop("command")
                srv["command"] = [cmd] + list(args)
                srv["type"] = "local"
        elif "url" in srv and shape == "opencode":
            srv["type"] = "remote"
        out_servers[name] = srv
    if shape == "opencode":
        # OpenCode MCPs live in the config file (opencode.json) as a flat
        # "mcp" map, merged in while preserving $schema/plugin/other keys.
        existing = {}
        if Path(dest).exists():
            try:
                existing = json.loads(Path(dest).read_text())
            except Exception:
                existing = {}
        if not isinstance(existing, dict):
            existing = {}
        existing["mcp"] = out_servers
        data = existing
    else:  # pi: write .pi/mcp.json with the standard mcpServers map
        data = {"mcpServers": out_servers}

Path(dest).parent.mkdir(parents=True, exist_ok=True)
Path(dest).write_text(json.dumps(data, indent=2) + "\n")
PY
        chmod 600 "$dest" 2>/dev/null || true
        echo "-> Seeded $dest"
    }

    _seed_one_mcp_json "$SOURCE_ROOT/.cursor/mcp.json" "cursor"
    # Target trees were wiped; always write fresh seeded MCP configs when the tree exists.
    if [ -d .cursor ]; then
        _seed_one_mcp_json ".cursor/mcp.json" "cursor"
    fi
    if [ -d .vscode ]; then
        _seed_one_mcp_json ".vscode/mcp.json" "vscode"
    fi
    if [ -d .opencode ]; then
        _seed_one_mcp_json "opencode.json" "opencode"
    fi
    if [ -d .pi ]; then
        _seed_one_mcp_json ".pi/mcp.json" "pi"
    fi
}

seed_mcp_json_configs

# Seed skill-local .env files from *.env.example + SOURCE_ROOT/.env (never overwrite existing).
seed_design_candidates_env_if_needed() {
    local example="$SOURCE_ROOT/.cursor/skills/rosey-design-candidates/.env.example"
    local dest

    if [ ! -f "$example" ]; then
        return 0
    fi

    # Source checkout (agentic-env) so the skill can run locally without install-into-self.
    dest="$SOURCE_ROOT/.cursor/skills/rosey-design-candidates/.env"
    if [ ! -f "$dest" ]; then
        if seed_dotenv_from_example "$example" "$dest" "CURSOR_API_KEY"; then
            echo "-> Seeded rosey-design-candidates .env (source skill)"
        else
            echo "   ⚠️  Could not seed source rosey-design-candidates .env (CURSOR_API_KEY missing in $SOURCE_ROOT/.env)"
        fi
    fi

    for dest in \
        ".cursor/skills/rosey-design-candidates/.env" \
        ".github/skills/rosey-design-candidates/.env" \
        ".opencode/skills/rosey-design-candidates/.env" \
        ".pi/skills/rosey-design-candidates/.env"; do
        [ -d "$(dirname "$dest")" ] || continue
        if [ -f "$dest" ]; then
            continue
        fi
        if seed_dotenv_from_example "$example" "$dest" "CURSOR_API_KEY"; then
            echo "-> Seeded $dest"
        else
            echo "   ⚠️  Could not seed $dest (CURSOR_API_KEY missing in env / $SOURCE_ROOT/.env)"
        fi
    done
}

seed_design_candidates_env_if_needed

# --- Global gitignore (machine-once) ---

# Rosey artifacts are gitignored once, machine-wide, via the user's global
# excludes file instead of per-repository .gitignore files. This keeps
# downstream repos free of Rosey-specific ignore lines. Uninstall never
# touches this file.

rosey_global_gitignore_path() {
    local p
    if command -v git >/dev/null 2>&1; then
        if p="$(git config --global --get core.excludesFile 2>/dev/null)" && [ -n "$p" ]; then
            case "$p" in
                /*) ;;                                 # absolute: keep as-is
                "~"/*) p="${HOME}${p#\~}" ;;           # ~/... -> $HOME/...
                *)                                    # relative: git would resolve it
                    echo "   ⚠️  core.excludesFile is relative ($p); treating it as \$HOME-relative." >&2
                    p="${HOME}/${p#/}" ;;              # against the current directory; normalize to $HOME
            esac
            printf '%s\n' "$p"
            return 0
        fi
    fi
    if [ -n "${XDG_CONFIG_HOME:-}" ]; then
        printf '%s\n' "$XDG_CONFIG_HOME/git/ignore"
    else
        printf '%s\n' "${HOME}/.config/git/ignore"
    fi
}

rosey_global_gitignore_ensure() {
    local gf
    gf="$(rosey_global_gitignore_path)"
    if ! mkdir -p "$(dirname "$gf")" 2>/dev/null; then
        echo "   ⚠️  Could not create $(dirname "$gf"); skipping global gitignore block." >&2
        return 0
    fi
    if grep -q '^# Rosey Agentic Environment' "$gf" 2>/dev/null; then
        echo "-> Global gitignore already has the Rosey block ($gf)"
        return 0
    fi
    if [ -s "$gf" ]; then
        printf '\n' >> "$gf" 2>/dev/null || true
    fi
    if ! cat >> "$gf" <<'EOF' 2>/dev/null
# Rosey Agentic Environment
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
rosey/agentic-env.json
rosey/maintainer-manifest.json
rosey/hindsight-pin
AGENTS.md
.cursorrules
DESIGN.md
.cursor/
.github/copilot-instructions.md
.github/instructions/
.github/skills/
.github/agents/
.github/hooks/
.vscode/mcp.json
opencode.json
.opencode/
.pi/
.agents/
EOF
    then
        echo "   ⚠️  Could not write the global gitignore block to $gf; Rosey files may appear untracked." >&2
        return 0
    fi
    echo "-> Added Rosey block to global gitignore ($gf)"
}

rosey_global_gitignore_ensure

# --- AGENTS.md / .cursorrules ---

write_agents_file() {
    if [ "$CREATE_AGENTS" != true ]; then
        return 0
    fi

    if is_livehome_install; then
        echo "-> Writing .cursorrules (agent-home target; skipping AGENTS.md)..."
        cat > .cursorrules <<'EOF'
# Rosey Agent Guidance

This workspace uses the Rosey Agentic Environment.
This file intentionally does not store user preferences inline.

Before non-trivial planning, implementation, or review work, follow the installed
Rosey rules and skills:

- `.cursor/rules/caveman.mdc`
- `.cursor/rules/ponytail.mdc`
- `.cursor/rules/rosey-workflow-gates.mdc`
- `.cursor/rules/hindsight-memory.mdc`
- `.cursor/rules/docker-via-make.mdc`
- `.cursor/rules/gitchangelog-commits.mdc`

Use `.cursor/skills/` for Rosey workflows and `.cursor/agents/` for specialist
reviews. Full Hindsight CLI contract: `.cursor/skills/rosey-hindsight/SKILL.md`.

## Preferences, insights, and memory

User preferences and durable project context live **outside** this file:

| Store | Path / tool | What it holds |
| ----- | ----------- | ------------- |
| Curated insights | `rosey/insights/*.md` | Durable repo lessons (architecture rules, workflow gotchas, “do not do this”) |
| Curated solutions | `rosey/solutions/` | Institutional how-tos / past fixes |
| Cross-session memory | Hindsight (`hindsight-embed`) | Preferences, procedure outcomes, task discoveries |

**Consult insights:** read `rosey/insights/` (and use `rosey-learnings-researcher` when available) before non-trivial planning or implementation in a documented area.

**Consult Hindsight memory** (only when `/rosey-brainstorm`, `/rosey-plan`, `/rosey-work`, or `/rosey-qa` is active — not for generic planning, implementation, or diff review):

```bash
export PATH="${HOME}/.local/bin:${PATH}"
hindsight-embed daemon status
bank="${HINDSIGHT_EMBED_BANK_ID:-$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9][^a-z0-9]*/-/g; s/^-//; s/-$//')}"
hindsight-embed memory recall "$bank" "Task summary, modules, preferences, and risks"
```

If the daemon is unavailable, continue the workflow and record `Hindsight: unavailable`.
Do not store secrets in Hindsight or insight files.

## Shared

Hindsight version pin: `rosey/hindsight-pin`.
EOF
        if is_livehome_install; then
            grep -v 'docker-via-make' .cursorrules > .cursorrules.tmp && mv .cursorrules.tmp .cursorrules
            cat >> .cursorrules <<'EOF'

## Live-home git

This workspace is a live-home. Work on master (or main). No PRs, no stashes. Git is backup and sync between two machines. Slash skills `rosey-brainstorm`, `rosey-plan`, `rosey-work`, `rosey-qa`, and `rosey-lint` use the live-home overlays. Host tooling is allowed; Docker-via-Make does not apply.
EOF
        fi
        return 0
    fi

    echo "-> Writing AGENTS.md..."
    cat > AGENTS.md <<'EOF'
# Rosey Agent Guidance

This repository uses the Rosey Agentic Environment.
This file intentionally does not store user preferences inline.

Detect which IDE you are running in, then follow **only** that IDE's paths below.
Do not follow Cursor paths when running in VS Code / Copilot, and do not follow
VS Code paths when running in Cursor. Do not cross IDE trees — each IDE reads
only its own `.cursor/`, `.github/`, `.opencode/`, or `.pi/` paths.

## If Cursor

Before non-trivial planning, implementation, or review work, follow the installed
Rosey rules and skills:

- `.cursor/rules/caveman.mdc`
- `.cursor/rules/ponytail.mdc`
- `.cursor/rules/rosey-workflow-gates.mdc`
- `.cursor/rules/hindsight-memory.mdc`
- `.cursor/rules/docker-via-make.mdc`
- `.cursor/rules/gitchangelog-commits.mdc`

Use `.cursor/skills/` for Rosey workflows and `.cursor/agents/` for specialist
reviews. Full Hindsight CLI contract: `.cursor/skills/rosey-hindsight/SKILL.md`.

## If VS Code / GitHub Copilot

Before non-trivial planning, implementation, or review work, follow the installed
Rosey guidelines and skills:

- Always-on guidelines: `.github/copilot-instructions.md`
  (includes workflow gates, Hindsight, and save-insights)
- On-demand rules: `.github/instructions/`
- Skills: `.github/skills/`
- Agents: `.github/agents/`

Do not open or follow `.cursor/rules/`, `.cursor/skills/`, or `.cursor/agents/`
from VS Code — those paths are Cursor-only.

Full Hindsight CLI contract: `.github/skills/rosey-hindsight/SKILL.md`.

## If OpenCode

Before non-trivial planning, implementation, or review work, follow the installed
Rosey rules and skills:

- Rules: `.opencode/rules/` (via the `opencode-cursor-rules` plugin)
- Skills: `.opencode/skills/`
- Agents: `.opencode/agents/`

Do not open or follow `.cursor/rules/`, `.cursor/skills/`, or `.cursor/agents/`
from OpenCode — those paths are Cursor-only.

Full Hindsight CLI contract: `.opencode/skills/rosey-hindsight/SKILL.md`.

Hindsight warm-start: `.opencode/hooks/ensure-hindsight-daemon.sh` (`.opencode/hooks.json` + `opencode.json` plugin `@monks1975/opencode-agent-hooks`).

## If Pi

Before non-trivial planning, implementation, or review work, follow the installed
Rosey rules and skills:

- Rules: `.pi/APPEND_SYSTEM.md`
- Skills: `.pi/skills/`
- Agents: `.pi/agents/` (enabled by the `pi-subagents` extension, installed once by `install.sh` when the `pi` CLI is present)

Do not open or follow `.cursor/rules/`, `.cursor/skills/`, or `.cursor/agents/`
from Pi — those paths are Cursor-only.

Full Hindsight CLI contract: `.pi/skills/rosey-hindsight/SKILL.md`.

Hindsight warm-start: `.pi/scripts/ensure-hindsight-daemon.sh` via `.pi/extensions/rosey-hindsight-daemon.ts` on `session_start`.

## Preferences, insights, and memory

User preferences and durable project context live **outside** this file:

| Store | Path / tool | What it holds |
| ----- | ----------- | ------------- |
| Curated insights | `rosey/insights/*.md` | Durable repo lessons (architecture rules, workflow gotchas, “do not do this”) |
| Curated solutions | `rosey/solutions/` | Institutional how-tos / past fixes |
| Cross-session memory | Hindsight (`hindsight-embed`) | Preferences, procedure outcomes, task discoveries |

**Consult insights:** read `rosey/insights/` (and use `rosey-learnings-researcher` when available) before non-trivial planning or implementation in a documented area.

**Consult Hindsight memory** (only when `/rosey-brainstorm`, `/rosey-plan`, `/rosey-work`, or `/rosey-qa` is active — not for generic planning, implementation, or diff review):

```bash
export PATH="${HOME}/.local/bin:${PATH}"
hindsight-embed daemon status
bank="${HINDSIGHT_EMBED_BANK_ID:-$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9][^a-z0-9]*/-/g; s/^-//; s/-$//')}"
hindsight-embed memory recall "$bank" "Task summary, modules, preferences, and risks"
```

If the daemon is unavailable, continue the workflow and record `Hindsight: unavailable`.
Do not store secrets in Hindsight or insight files.

## Shared

Hindsight version pin: `rosey/hindsight-pin`.
EOF
}

# --- agentic-env.json pin ---

write_agentic_pin() {
    if [ "$WRITE_PIN" != true ]; then
        return 0
    fi

    echo "-> Writing rosey/agentic-env.json..."
    mkdir -p rosey
    local installed_at
    installed_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    cat > rosey/agentic-env.json <<EOF
{
  "installed_at": "$installed_at",
  "source": "$SOURCE_ROOT",
  "version": "$INSTALL_VERSION",
  "targets": ["cursor","vscode","opencode","pi"]
}
EOF
}

write_agents_file
write_agentic_pin

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

echo "-> Installing skill dependencies (OpenDesign, etc.)..."
# Scan .cursor/skills, .github/skills, .opencode/skills, and .pi/skills for package.json (whichever exist).
for skills_root in .cursor/skills .github/skills .opencode/skills .pi/skills; do
    if [ -d "$skills_root" ]; then
        while IFS= read -r -d '' pkg; do
            skill_dir="$(dirname "$pkg")"
            install_npm_deps "$skill_dir" "skill $(basename "$skill_dir")"
        done < <(find "$skills_root" -name package.json -not -path '*/node_modules/*' -print0 2>/dev/null)
    fi
done

echo "-> Installing app dependencies..."
if [ -f "$INSTALL_ROOT/package.json" ]; then
    install_npm_deps "$INSTALL_ROOT" "workspace root"
fi

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

init_repo_git_flow() {
    if is_livehome_install; then
        echo "-> Skipping git flow init (live-home does not use git-flow)"
        return 0
    fi
    if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "-> Skipping git flow init (not a git repository)"
        return 0
    fi
    if git config --get gitflow.branch.master >/dev/null 2>&1; then
        echo "-> git flow already initialized in this repo; skipping"
        return 0
    fi
    if ! git_flow_available; then
        echo "   ⚠️  git-flow not available; cannot run git flow init -d"
        return 1
    fi

    echo "-> Initializing git flow in this repo (git flow init -d)..."
    git flow init -d || {
        echo "   ⚠️  git flow init -d failed"
        return 1
    }
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
    # Prefer shared rosey/hindsight-pin, fall back to source .cursor/hindsight-pin.
    local pin_file="rosey/hindsight-pin"
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
# (then process env / INSTALL_ROOT/.env). Never overwrites existing config.
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

    # Daemon start only on fresh tool install; later repo installs rely on IDE hooks.
    if [ "${HINDSIGHT_TOOL_ACTION}" = "skipped" ]; then
        if hindsight_cli daemon status >/dev/null 2>&1; then
            echo "   Hindsight embed daemon is running."
        else
            echo "   Hindsight tool present; daemon start left to IDE session hooks."
        fi
        return 0
    fi

    if hindsight_cli daemon status >/dev/null 2>&1; then
        echo "   Hindsight embed daemon is running."
        return 0
    fi

    echo "   Hindsight embed is configured but daemon is stopped; starting..."
    if HINDSIGHT_EMBED_DAEMON_STARTUP_TIMEOUT="${HINDSIGHT_EMBED_DAEMON_STARTUP_TIMEOUT:-600}" \
        hindsight_cli daemon start >/dev/null 2>&1 \
        && hindsight_cli daemon status >/dev/null 2>&1; then
        echo "   Hindsight embed daemon started."
    else
        echo "   ⚠️  Hindsight daemon failed to start (cold boot can take several minutes)."
        echo "      Retry: HINDSIGHT_EMBED_DAEMON_STARTUP_TIMEOUT=600 hindsight-embed daemon start"
        echo "      Logs: hindsight-embed daemon logs -n 50"
        echo "      Hook log: ~/.hindsight/hook-last-run.log"
    fi
}

install_bumpversion || true
install_gitchangelog || true
install_git_flow || true
init_repo_git_flow || true
configure_repo_signing_key || true
install_sentrux || true
install_pi_subagents || true
install_pi_mcp_adapter || true
install_pi_ask_user || true

check_hindsight_embed || true

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
echo "Rosey Environment installed successfully!"
echo "   Trees: .cursor/ (rules, skills, agents, hooks, mcp.json) and .github/ + .vscode/ equivalents."
echo "   Version pin: rosey/agentic-env.json; Hindsight pin: rosey/hindsight-pin."
echo "   Seeded from agentic-env .env (when keys present):"
echo "     - .cursor/mcp.json and .vscode/mcp.json (GITHUB_TOKEN, OBSIDIAN_API_KEY)"
echo "     - rosey-design-candidates skill .env (CURSOR_API_KEY)"
echo "     - ~/.hindsight/embed once (HINDSIGHT_*); CLI install skipped if hindsight-embed already responds"
echo "   Machine-once CLIs skipped if already on PATH: git, make, curl, rsync, jq, rg, gh, uv, bun, gitchangelog, bumpversion, git-flow, sentrux, hindsight-embed."
echo "   Pi: pi-subagents, pi-mcp-adapter, and pi-ask-user installed once when the pi CLI is present."
echo "   VS Code: allow automatic tasks once (Tasks: Manage Automatic Tasks) for Hindsight folderOpen warm-start."
echo "   OpenCode: SessionStart hook + opencode-agent-hooks plugin in opencode.json for Hindsight warm-start."
echo "   Pi: session_start extension (.pi/extensions/rosey-hindsight-daemon.ts) for Hindsight warm-start."
