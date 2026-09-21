#!/usr/bin/env bash
# Rosey Agentic Environment — machine-global uninstaller.
#
# This script never changes the current repository. It removes only the global
# Rosey payload installed under the user's Cursor, OpenCode, Pi, .agents, and
# ~/.config/rosey directories. Machine tools, Hindsight memory, and user-owned
# project files are left alone.
#
# Usage:
#   ./uninstall.sh                 # dry run
#   ./uninstall.sh --check         # report global installation state
#   ./uninstall.sh --apply         # remove global Rosey payload
#   ./uninstall.sh --apply --force # also remove edited Rosey guidance files

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="${ROSEY_AGENTIC_ENV:-$SCRIPT_DIR}"
VERSION_FILE="$SOURCE_ROOT/VERSION"
UNINSTALL_VERSION="0.1.0"
if [ -f "$VERSION_FILE" ]; then
    UNINSTALL_VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"
fi

CHECK_ONLY=false
APPLY=false
FORCE=false

ROSEY_CONFIG_DIR="${HOME}/.config/rosey"
CURSOR_HOME="${HOME}/.cursor"
PI_HOME="${HOME}/.pi/agent"
OPENCODE_HOME="${HOME}/.config/opencode"
PI_SHARED_MCP="${HOME}/.config/mcp/mcp.json"

while [ "$#" -gt 0 ]; do
    case "$1" in
        --version)
            echo "$UNINSTALL_VERSION"
            exit 0
            ;;
        --check)
            CHECK_ONLY=true
            shift
            ;;
        --apply)
            APPLY=true
            shift
            ;;
        --yes)
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --targets=*)
            echo "warning: --targets is obsolete; global uninstall covers Cursor, OpenCode, and Pi" >&2
            shift
            ;;
        --purge-git-config)
            echo "warning: --purge-git-config is obsolete; global Git excludes are handled by this uninstall" >&2
            shift
            ;;
        -h | --help)
            sed -n '2,15p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

note() { printf '%s\n' "$*"; }
warn() { printf '   ! %s\n' "$*"; }

path_exists() { [ -e "$1" ] || [ -L "$1" ]; }

remove_path() {
    local path="$1" label="${2:-$1}"
    path_exists "$path" || return 0
    if [ "$APPLY" = true ]; then
        rm -rf -- "$path"
        note "   removed       $label"
    else
        note "   would remove  $label"
    fi
}

remove_marked_file() {
    local path="$1" marker="$2" label="${3:-$1}"
    [ -f "$path" ] || return 0
    if [ "$FORCE" = true ]; then
        remove_path "$path" "$label (forced)"
        return 0
    fi
    if ! grep -qF -- "$marker" "$path" 2>/dev/null; then
        warn "$label looks user-owned; keeping it (use --force to remove)"
        return 0
    fi
    remove_path "$path" "$label"
}

remove_empty_dir() {
    local path="$1"
    [ -d "$path" ] || return 0
    [ -z "$(ls -A "$path" 2>/dev/null)" ] || return 0
    if [ "$APPLY" = true ]; then
        rmdir "$path" 2>/dev/null || true
    fi
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

remove_global_gitignore_block() {
    local gf
    gf="$(rosey_global_gitignore_path)"
    [ -f "$gf" ] || return 0
    if ! grep -q '^# Rosey Agentic Environment$' "$gf"; then
        return 0
    fi
    if [ "$APPLY" = false ]; then
        note "   would edit     $gf (remove Rosey ignore block)"
        return 0
    fi
    python3 - "$gf" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
start = text.find("# Rosey Agentic Environment\n")
if start < 0:
    raise SystemExit(0)
end_marker = text.find("# End Rosey Agentic Environment", start)
if end_marker >= 0:
    end = text.find("\n", end_marker)
    end = len(text) if end < 0 else end + 1
    text = text[:start] + text[end:]
else:
    # Legacy block was terminal. Remove only its known lines and marker.
    old = {
        "# Rosey Agentic Environment",
        "# Added by rosey-agentic-env/install.sh. Remove this block to stop ignoring.",
        "rosey/brainstorms/", "rosey/plans/", "rosey/designs/", "rosey/solutions/",
        "rosey/insights/", "rosey/design-system/", "rosey/qa/", "rosey/parallel/",
        "rosey/deepening/", "rosey/loops/", "rosey/ideation/", "rosey/maintainer-manifest.json",
        "rosey/agentic-env.json", "rosey/hindsight-pin", "AGENTS.md", ".cursorrules",
        "DESIGN.md", ".cursor/", ".github/copilot-instructions.md", ".github/instructions/",
        ".github/skills/", ".github/agents/", ".github/hooks/", ".vscode/mcp.json",
        "opencode.json", ".opencode/", ".pi/", ".agents/",
    }
    lines = []
    for line in text.splitlines(keepends=True):
        if line.rstrip("\n") in old:
            continue
        lines.append(line)
    text = "".join(lines)
path.write_text(text.rstrip() + "\n")
PY
    note "   edited        $gf (removed Rosey ignore block)"
}

has_global_install() {
    [ -f "$ROSEY_CONFIG_DIR/install-manifest.json" ] || \
        [ -f "$ROSEY_CONFIG_DIR/agentic-env.json" ] || \
        [ -f "$CURSOR_HOME/hooks/ensure-hindsight-daemon.sh" ] || \
        [ -f "$PI_HOME/extensions/rosey-hindsight-daemon.ts" ] || \
        [ -f "$OPENCODE_HOME/plugin/rosey-hindsight-daemon.ts" ]
}

if [ "$CHECK_ONLY" = true ]; then
    if has_global_install; then
        note "Rosey global environment is installed"
        [ -f "$ROSEY_CONFIG_DIR/install-manifest.json" ] && cat "$ROSEY_CONFIG_DIR/install-manifest.json"
        exit 0
    fi
    note "Rosey global environment is not installed"
    exit 1
fi

if ! has_global_install; then
    note "Nothing to uninstall: no Rosey global artifacts found"
    exit 0
fi

if [ "$APPLY" = false ]; then
    note "Rosey global environment — DRY RUN (pass --apply to make changes)"
else
    note "Rosey global environment — uninstalling"
fi
note "-> Version $UNINSTALL_VERSION"
note ""

# Remove the Rosey skill names currently present in the source tree. These are
# Rosey-owned global copies; unrelated user skills remain untouched.
if [ -d "$SOURCE_ROOT/.cursor/skills" ]; then
    for src in "$SOURCE_ROOT"/.cursor/skills/*/; do
        [ -d "$src" ] || continue
        name="$(basename "$src")"
        remove_path "$CURSOR_HOME/skills/$name" "Cursor skill $name"
        remove_path "$OPENCODE_HOME/skills/$name" "OpenCode skill $name"
        remove_path "$PI_HOME/skills/$name" "Pi skill $name"
    done
fi

if [ -d "$SOURCE_ROOT/.cursor/rules" ]; then
    for src in "$SOURCE_ROOT"/.cursor/rules/*.mdc; do
        [ -f "$src" ] || continue
        name="$(basename "$src")"
        remove_path "$CURSOR_HOME/rules/$name" "Cursor rule $name"
        remove_path "$ROSEY_CONFIG_DIR/rules/$name" "Rosey shared rule $name"
    done
fi

if [ -d "$SOURCE_ROOT/.cursor/agents" ]; then
    for src in "$SOURCE_ROOT"/.cursor/agents/*; do
        [ -e "$src" ] || continue
        name="$(basename "$src")"
        remove_path "$CURSOR_HOME/agents/$name" "Cursor agent $name"
        remove_path "$OPENCODE_HOME/agents/$name" "OpenCode agent $name"
        remove_path "$HOME/.agents/$name" "Pi agent $name"
    done
fi

remove_path "$CURSOR_HOME/hooks/ensure-hindsight-daemon.sh" "Cursor Hindsight hook"
remove_path "$OPENCODE_HOME/plugin/rosey-hindsight-daemon.ts" "OpenCode Hindsight plugin"
remove_path "$PI_HOME/scripts/ensure-hindsight-daemon.sh" "Pi Hindsight script"
remove_path "$PI_HOME/extensions/rosey-hindsight-daemon.ts" "Pi Hindsight extension"

remove_marked_file "$ROSEY_CONFIG_DIR/AGENTS.md" "Rosey Agent Guidance" "Rosey global guidance"
remove_marked_file "$PI_HOME/AGENTS.md" "Rosey Agent Guidance" "Pi global guidance"
remove_path "$ROSEY_CONFIG_DIR/references/model-tiers.md" "Rosey model-tiers contract"
remove_path "$ROSEY_CONFIG_DIR/references/scoping-synthesis.md" "Rosey scoping-synthesis contract"
remove_path "$ROSEY_CONFIG_DIR/references/markdown-rendering.md" "Rosey markdown-rendering contract"
remove_path "$ROSEY_CONFIG_DIR/agentic-env.json" "Rosey agentic-env pin"
remove_path "$ROSEY_CONFIG_DIR/hindsight-pin" "Rosey Hindsight pin"
remove_path "$ROSEY_CONFIG_DIR/install-manifest.json" "Rosey install manifest"

# Remove only Rosey's known MCP entries and instruction path; preserve all other
# machine-owned configuration. Rosey entries win on install by owner decision.
python3 - "$APPLY" "$FORCE" "$CURSOR_HOME/mcp.json" "$OPENCODE_HOME/opencode.json" "$PI_SHARED_MCP" "$PI_HOME/settings.json" "$CURSOR_HOME/hooks.json" "$ROSEY_CONFIG_DIR/AGENTS.md" <<'PY'
import json
import sys
from pathlib import Path

apply = sys.argv[1] == "true"
force = sys.argv[2] == "true"
paths = [Path(p) for p in sys.argv[3:]]
mcp_names = {"github", "context7", "sentrux"}
pi_guidance = paths[-1]


def load(path):
    try:
        value = json.loads(path.read_text()) if path.exists() else None
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def save(path, data):
    if not apply:
        print(f"   would edit     {path}")
        return
    path.write_text(json.dumps(data, indent=2) + "\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    print(f"   edited        {path}")

# Cursor mcpServers, OpenCode mcp, and Pi configs.
for index, key in ((0, "mcpServers"), (1, "mcp"), (2, "mcpServers"), (3, "mcpServers")):
    path = paths[index]
    data = load(path)
    if data is None or not isinstance(data.get(key), dict):
        continue
    changed = False
    for name in list(data[key]):
        if name in mcp_names:
            del data[key][name]
            changed = True
    if changed:
        if not data[key]:
            data.pop(key, None)
        save(path, data)

# OpenCode instructions.
opencode = load(paths[1])
if opencode is not None and isinstance(opencode.get("instructions"), list):
    instructions = [item for item in opencode["instructions"] if item != str(pi_guidance)]
    if instructions != opencode["instructions"]:
        if instructions:
            opencode["instructions"] = instructions
        else:
            opencode.pop("instructions", None)
        save(paths[1], opencode)

# Cursor user hook registration.
hooks_path = paths[4]
hooks = load(hooks_path)
if hooks is not None and isinstance(hooks.get("hooks"), dict):
    entries = hooks["hooks"].get("sessionStart")
    if isinstance(entries, list):
        command = str(Path.home() / ".cursor" / "hooks" / "ensure-hindsight-daemon.sh")
        kept = [entry for entry in entries if not (isinstance(entry, dict) and entry.get("command") == command)]
        if kept != entries:
            if kept:
                hooks["hooks"]["sessionStart"] = kept
            else:
                hooks["hooks"].pop("sessionStart", None)
            save(hooks_path, hooks)
PY

remove_empty_dir "$CURSOR_HOME/hooks"
remove_empty_dir "$CURSOR_HOME/rules"
remove_empty_dir "$CURSOR_HOME/agents"
remove_empty_dir "$OPENCODE_HOME/plugin"
remove_empty_dir "$OPENCODE_HOME/agents"
remove_empty_dir "$PI_HOME/scripts"
remove_empty_dir "$PI_HOME/extensions"
remove_empty_dir "$ROSEY_CONFIG_DIR/references"
remove_empty_dir "$ROSEY_CONFIG_DIR/rules"
remove_empty_dir "$ROSEY_CONFIG_DIR"
remove_global_gitignore_block

note ""
if [ "$APPLY" = true ]; then
    note "Rosey global environment removed. Machine tools, Hindsight memory, and repositories were not changed."
else
    note "Dry run complete. No files changed."
fi
