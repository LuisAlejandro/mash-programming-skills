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

# Agent-home / OpenClaw / Hermes installs use .cursorrules instead of AGENTS.md.
uses_cursorrules_instead_of_agents() {
    case "$INSTALL_ROOT_BASENAME" in
        .hermes | .openclaw | rosey-hermes | rosey-openclaw | winston-openclaw)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
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
    if [ "$CREATE_AGENTS" = true ]; then
        if uses_cursorrules_instead_of_agents; then
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
        *)
            return 0
            ;;
    esac
}

# True when a skill should be installed for the given IDE tree (cursor|vscode).
# Default: both. VS Code-only skills skip the Cursor tree.
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

# --- Shared pin ---

echo "-> Writing shared rosey/hindsight-pin..."
mkdir -p rosey
[ -f "$SOURCE_ROOT/.cursor/hindsight-pin" ] && cp "$SOURCE_ROOT/.cursor/hindsight-pin" rosey/hindsight-pin

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
        done
    fi
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

install_cursor_tree
install_vscode_tree

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
        local dest="$1" vscode_shape="$2"
        # Source checkout: never overwrite an existing local mcp.json.
        if [ "$dest" = "$SOURCE_ROOT/.cursor/mcp.json" ] && [ -f "$dest" ]; then
            return 0
        fi
        python3 - "$example" "$dest" "$vscode_shape" "$github_token" "$obsidian_key" <<'PY'
import json
import sys
from pathlib import Path

example, dest, vscode_shape, github_token, obsidian_key = sys.argv[1:6]
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
if vscode_shape == "1" and isinstance(data, dict) and "mcpServers" in data and "servers" not in data:
    data["servers"] = data.pop("mcpServers")

Path(dest).parent.mkdir(parents=True, exist_ok=True)
Path(dest).write_text(json.dumps(data, indent=2) + "\n")
PY
        chmod 600 "$dest" 2>/dev/null || true
        echo "-> Seeded $dest"
    }

    _seed_one_mcp_json "$SOURCE_ROOT/.cursor/mcp.json" "0"
    # Target trees were wiped; always write fresh seeded MCP configs when .cursor/ exists.
    if [ -d .cursor ]; then
        _seed_one_mcp_json ".cursor/mcp.json" "0"
    fi
    if [ -d .vscode ]; then
        _seed_one_mcp_json ".vscode/mcp.json" "1"
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
        ".github/skills/rosey-design-candidates/.env"; do
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

# --- .gitignore ---

echo "-> Updating .gitignore..."
touch .gitignore

rosey_gitignore_ensure_header() {
    if ! grep -q "^# Rosey Agentic Environment" .gitignore 2>/dev/null; then
        echo -e "\n# Rosey Agentic Environment" >> .gitignore
    fi
}

append_gitignore_if_missing() {
    local line="$1"
    if ! grep -qxF "$line" .gitignore 2>/dev/null; then
        rosey_gitignore_ensure_header
        echo "$line" >> .gitignore
    fi
}

# Shared rosey/ artifacts (both targets)
append_gitignore_if_missing "rosey/brainstorms/"
append_gitignore_if_missing "rosey/plans/"
append_gitignore_if_missing "rosey/designs/"
append_gitignore_if_missing "rosey/solutions/"
append_gitignore_if_missing "rosey/insights/"
append_gitignore_if_missing "rosey/design-system/"
append_gitignore_if_missing "rosey/qa/"
append_gitignore_if_missing "rosey/deepening/"
append_gitignore_if_missing "rosey/agentic-env.json"
append_gitignore_if_missing "rosey/maintainer-manifest.json"
append_gitignore_if_missing "rosey/hindsight-pin"
if uses_cursorrules_instead_of_agents; then
    append_gitignore_if_missing ".cursorrules"
else
    append_gitignore_if_missing "AGENTS.md"
fi
append_gitignore_if_missing "DESIGN.md"

# Cursor target
append_gitignore_if_missing ".cursor/"

# VS Code target — gitignore the specific Rosey-managed paths under .github/ and .vscode/mcp.json.
# Note: this ignores ALL of .github/instructions, .github/skills, .github/agents, .github/hooks.
# If you commit other team content under those folders, review before pushing.
append_gitignore_if_missing ".github/copilot-instructions.md"
append_gitignore_if_missing ".github/instructions/"
append_gitignore_if_missing ".github/skills/"
append_gitignore_if_missing ".github/agents/"
append_gitignore_if_missing ".github/hooks/"
append_gitignore_if_missing ".vscode/mcp.json"

# --- AGENTS.md / .cursorrules ---

write_agents_file() {
    if [ "$CREATE_AGENTS" != true ]; then
        return 0
    fi

    if uses_cursorrules_instead_of_agents; then
        echo "-> Writing .cursorrules (agent-home target; skipping AGENTS.md)..."
        cat > .cursorrules <<'EOF'
# Rosey Agent Guidance

This workspace uses the Rosey Agentic Environment.
This file intentionally does not store user preferences inline.

Before non-trivial planning, implementation, or review work, follow the installed
Rosey rules and skills:

- `.cursor/rules/caveman.mdc`
- `.cursor/rules/rosey-workflow-gates.mdc`
- `.cursor/rules/hindsight-memory.mdc`
- `.cursor/rules/karpathy-guidelines.mdc`
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

**Consult Hindsight memory** (before plan / work / QA):

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
        return 0
    fi

    echo "-> Writing AGENTS.md..."
    cat > AGENTS.md <<'EOF'
# Rosey Agent Guidance

This repository uses the Rosey Agentic Environment.
This file intentionally does not store user preferences inline.

Detect which IDE you are running in, then follow **only** that IDE's paths below.
Do not follow Cursor paths when running in VS Code / Copilot, and do not follow
VS Code paths when running in Cursor.

## If Cursor

Before non-trivial planning, implementation, or review work, follow the installed
Rosey rules and skills:

- `.cursor/rules/caveman.mdc`
- `.cursor/rules/rosey-workflow-gates.mdc`
- `.cursor/rules/hindsight-memory.mdc`
- `.cursor/rules/karpathy-guidelines.mdc`
- `.cursor/rules/docker-via-make.mdc`
- `.cursor/rules/gitchangelog-commits.mdc`

Use `.cursor/skills/` for Rosey workflows and `.cursor/agents/` for specialist
reviews. Full Hindsight CLI contract: `.cursor/skills/rosey-hindsight/SKILL.md`.

## If VS Code / GitHub Copilot

Before non-trivial planning, implementation, or review work, follow the installed
Rosey guidelines and skills:

- Always-on guidelines: `.github/copilot-instructions.md`
  (includes workflow gates, Hindsight, Karpathy, and save-insights)
- On-demand rules: `.github/instructions/`
- Skills: `.github/skills/`
- Agents: `.github/agents/`

Do not open or follow `.cursor/rules/`, `.cursor/skills/`, or `.cursor/agents/`
from VS Code — those paths are Cursor-only.

Full Hindsight CLI contract: `.github/skills/rosey-hindsight/SKILL.md`.

## Preferences, insights, and memory

User preferences and durable project context live **outside** this file:

| Store | Path / tool | What it holds |
| ----- | ----------- | ------------- |
| Curated insights | `rosey/insights/*.md` | Durable repo lessons (architecture rules, workflow gotchas, “do not do this”) |
| Curated solutions | `rosey/solutions/` | Institutional how-tos / past fixes |
| Cross-session memory | Hindsight (`hindsight-embed`) | Preferences, procedure outcomes, task discoveries |

**Consult insights:** read `rosey/insights/` (and use `rosey-learnings-researcher` when available) before non-trivial planning or implementation in a documented area.

**Consult Hindsight memory** (before plan / work / QA):

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
  "targets": ["cursor","vscode"]
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
# Scan both .cursor/skills and .github/skills for package.json (whichever exist).
for skills_root in .cursor/skills .github/skills; do
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

# --- Machine-once tool installs (Sentrux + Hindsight) ---
# Per-user/machine, not per target repo. Detect by probing the CLI; skip install if it responds.

# --- Sentrux ---

sentrux_available() {
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

install_sentrux || true

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

    if ! command -v uv >/dev/null 2>&1; then
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

check_hindsight_embed || true

echo ""
echo "Rosey Environment installed successfully!"
echo "   Trees: .cursor/ (rules, skills, agents, hooks, mcp.json) and .github/ + .vscode/ equivalents."
echo "   Version pin: rosey/agentic-env.json; Hindsight pin: rosey/hindsight-pin."
echo "   Seeded from agentic-env .env (when keys present):"
echo "     - .cursor/mcp.json and .vscode/mcp.json (GITHUB_TOKEN, OBSIDIAN_API_KEY)"
echo "     - rosey-design-candidates skill .env (CURSOR_API_KEY)"
echo "     - ~/.hindsight/embed once (HINDSIGHT_*); CLI install skipped if hindsight-embed already responds"
echo "   Sentrux install skipped if sentrux --version already responds."
echo "   VS Code: allow automatic tasks once (Tasks: Manage Automatic Tasks) for Hindsight folderOpen warm-start."
