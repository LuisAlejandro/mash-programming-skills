#!/usr/bin/env bash
# Mash Programming Skills — machine-global uninstaller.
#
# Removes the global Mash Programming Skills payload recorded in
# ~/.config/mash/install-manifest.json. Does not need the source checkout.
# Machine tools, Hindsight memory, and repositories are left alone.
#
# Usage (repo copy or ~/.config/mash/uninstall.sh):
#   uninstall.sh                 # dry run
#   uninstall.sh --check         # report global installation state
#   uninstall.sh --apply         # remove the global payload
#   uninstall.sh --apply --force # also remove edited guidance files
#
# Install copies this file to ~/.config/mash/uninstall.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CHECK_ONLY=false
APPLY=false
FORCE=false

MASH_CONFIG_DIR="${HOME}/.config/mash"
CURSOR_HOME="${HOME}/.cursor"
PI_HOME="${HOME}/.pi/agent"
OPENCODE_HOME="${HOME}/.config/opencode"
PI_SHARED_MCP="${HOME}/.config/mcp/mcp.json"
MANIFEST="$MASH_CONFIG_DIR/install-manifest.json"
INVENTORY_DIR=""

cleanup() {
    if [ -n "$INVENTORY_DIR" ]; then
        rm -rf "$INVENTORY_DIR"
    fi
}
trap cleanup EXIT

read_manifest_version() {
    python3 - "$MANIFEST" <<'PY'
import json
import sys
from pathlib import Path

try:
    data = json.loads(Path(sys.argv[1]).read_text())
except (OSError, json.JSONDecodeError):
    raise SystemExit(0)
version = data.get("version") if isinstance(data, dict) else None
if isinstance(version, str) and version.strip():
    print(version.strip())
PY
}

UNINSTALL_VERSION="$(read_manifest_version || true)"
if [ -z "$UNINSTALL_VERSION" ] && [ -f "$SCRIPT_DIR/VERSION" ]; then
    UNINSTALL_VERSION="$(tr -d '[:space:]' < "$SCRIPT_DIR/VERSION")"
fi
if [ -z "$UNINSTALL_VERSION" ]; then
    UNINSTALL_VERSION="unknown"
fi

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
        --force)
            FORCE=true
            shift
            ;;
        -h | --help)
            sed -n '2,13p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
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

remove_global_gitignore_block() {
    local gf
    gf="$(mash_global_gitignore_path)"
    [ -f "$gf" ] || return 0
    if ! grep -q '^# Mash Programming Skills$' "$gf"; then
        return 0
    fi
    if [ "$APPLY" = false ]; then
        note "   would edit     $gf (remove Mash Programming Skills ignore block)"
        return 0
    fi
    python3 - "$gf" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
start = text.find("# Mash Programming Skills\n")
if start < 0:
    raise SystemExit(0)
end_marker = text.find("# End Mash Programming Skills", start)
if end_marker >= 0:
    end = text.find("\n", end_marker)
    end = len(text) if end < 0 else end + 1
    text = text[:start] + text[end:]
path.write_text(text.rstrip() + "\n")
PY
    note "   edited        $gf (removed Mash Programming Skills ignore block)"
}

has_global_install() {
    [ -f "$MANIFEST" ] || \
        [ -f "$CURSOR_HOME/hooks/ensure-hindsight-daemon.sh" ] || \
        [ -f "$PI_HOME/extensions/mash-hindsight-daemon.ts" ] || \
        [ -f "$OPENCODE_HOME/plugin/mash-hindsight-daemon.ts" ]
}

load_manifest_inventory() {
    INVENTORY_DIR="$(mktemp -d)"
    python3 - "$MANIFEST" "$INVENTORY_DIR" <<'PY'
import json
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
out = Path(sys.argv[2])

def safe(names):
    if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
        return None
    cleaned = []
    for name in names:
        if name in {"", ".", ".."} or "/" in name or "\\" in name or name != Path(name).name:
            continue
        cleaned.append(name)
    return sorted(set(cleaned))

def write_list(filename, names):
    (out / filename).write_text("".join(f"{name}\n" for name in names))

try:
    data = json.loads(manifest_path.read_text()) if manifest_path.is_file() else None
except json.JSONDecodeError:
    data = None

if not isinstance(data, dict):
    (out / "no-manifest").write_text("")
    raise SystemExit(0)

managed = data.get("managed")
lists = {}
if isinstance(managed, dict):
    for kind in ("skills", "rules", "agents"):
        names = safe(managed.get(kind))
        if names is None:
            lists = None
            break
        lists[kind] = names
else:
    lists = None

if lists is None:
    (out / "missing-managed").write_text("")
else:
    for kind, names in lists.items():
        write_list(kind, names)

if "mcp_servers" not in data:
    (out / "missing-mcp").write_text("")
else:
    names = safe(data.get("mcp_servers"))
    if names is None:
        (out / "missing-mcp").write_text("")
    else:
        write_list("mcp", names)
PY
}

each_name() {
    local file="$1"
    [ -f "$INVENTORY_DIR/$file" ] || return 0
    while IFS= read -r name || [ -n "$name" ]; do
        [ -n "$name" ] || continue
        printf '%s\n' "$name"
    done < "$INVENTORY_DIR/$file"
    return 0
}

if [ "$CHECK_ONLY" = true ]; then
    if has_global_install; then
        note "Mash Programming Skills global environment is installed"
        [ -f "$MANIFEST" ] && cat "$MANIFEST"
        exit 0
    fi
    note "Mash Programming Skills global environment is not installed"
    exit 1
fi

if ! has_global_install; then
    note "Nothing to uninstall: no Mash Programming Skills global artifacts found"
    exit 0
fi

if [ "$APPLY" = false ]; then
    note "Mash Programming Skills global environment — DRY RUN (pass --apply to make changes)"
else
    note "Mash Programming Skills global environment — uninstalling"
fi
note "-> Version $UNINSTALL_VERSION"
note ""

load_manifest_inventory
if [ -f "$INVENTORY_DIR/no-manifest" ]; then
    warn "no install manifest; leaving skills, agents, rules, and MCP entries in place"
else
    if [ -f "$INVENTORY_DIR/missing-managed" ]; then
        warn "install manifest has no managed inventory; leaving skills, agents, and rules in place"
    fi
    if [ -f "$INVENTORY_DIR/missing-mcp" ]; then
        warn "install manifest has no mcp_servers list; leaving MCP entries in place"
    fi
fi

while IFS= read -r name; do
    remove_path "$CURSOR_HOME/skills/$name" "Cursor skill $name"
    remove_path "$OPENCODE_HOME/skills/$name" "OpenCode skill $name"
    remove_path "$PI_HOME/skills/$name" "Pi skill $name"
done < <(each_name skills)

while IFS= read -r name; do
    remove_path "$CURSOR_HOME/rules/$name" "Cursor rule $name"
done < <(each_name rules)

while IFS= read -r name; do
    remove_path "$CURSOR_HOME/agents/$name" "Cursor agent $name"
    remove_path "$OPENCODE_HOME/agents/$name" "OpenCode agent $name"
    remove_path "$HOME/.agents/$name" "Pi agent $name"
done < <(each_name agents)

remove_path "$CURSOR_HOME/hooks/ensure-hindsight-daemon.sh" "Cursor Hindsight hook"
remove_path "$OPENCODE_HOME/plugin/mash-hindsight-daemon.ts" "OpenCode Hindsight plugin"
remove_path "$PI_HOME/scripts/ensure-hindsight-daemon.sh" "Pi Hindsight script"
remove_path "$PI_HOME/extensions/mash-hindsight-daemon.ts" "Pi Hindsight extension"

remove_marked_file "$MASH_CONFIG_DIR/AGENTS.md" "Mash Programming Skills Agent Guidance" "Mash Programming Skills global guidance"
remove_marked_file "$PI_HOME/AGENTS.md" "Mash Programming Skills Agent Guidance" "Pi global guidance"
remove_path "$MASH_CONFIG_DIR/always-on-rules.md" "Mash Programming Skills always-on rules bundle"
remove_path "$MASH_CONFIG_DIR/rules" "obsolete Mash Programming Skills shared rule copies"
remove_marked_file "$PI_HOME/APPEND_SYSTEM.md" "# Mash Programming Skills — always-on rules" "Pi always-on rules"
remove_path "$MASH_CONFIG_DIR/references/model-tiers.md" "Mash Programming Skills model-tiers contract"
remove_path "$MASH_CONFIG_DIR/references/scoping-synthesis.md" "Mash Programming Skills scoping-synthesis contract"
remove_path "$MASH_CONFIG_DIR/references/markdown-rendering.md" "Mash Programming Skills markdown-rendering contract"
remove_path "$MASH_CONFIG_DIR/agentic-env.json" "Mash Programming Skills agentic-env pin"
remove_path "$MASH_CONFIG_DIR/hindsight-pin" "Mash Programming Skills Hindsight pin"
remove_path "$MANIFEST" "Mash Programming Skills install manifest"
remove_path "$MASH_CONFIG_DIR/node_modules" "Mash Programming Skills shared skill node_modules"
remove_path "$MASH_CONFIG_DIR/venvs" "Mash Programming Skills shared skill virtualenvs"
remove_path "$MASH_CONFIG_DIR/uninstall.sh" "Mash Programming Skills uninstaller"

python3 - "$APPLY" "$INVENTORY_DIR/mcp" "$CURSOR_HOME/mcp.json" "$OPENCODE_HOME/opencode.json" "$PI_SHARED_MCP" "$PI_HOME/settings.json" "$CURSOR_HOME/hooks.json" "$MASH_CONFIG_DIR/AGENTS.md" "$MASH_CONFIG_DIR/always-on-rules.md" <<'PY'
import json
import sys
from pathlib import Path

apply = sys.argv[1] == "true"
mcp_file = Path(sys.argv[2])
paths = [Path(p) for p in sys.argv[3:]]
owned = set(mcp_file.read_text().splitlines()) if mcp_file.is_file() else set()
owned.discard("")
mash_instructions = {str(path) for path in paths[5:]}


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

for index, key in ((0, "mcpServers"), (1, "mcp"), (2, "mcpServers"), (3, "mcpServers")):
    path = paths[index]
    data = load(path)
    if data is None or not isinstance(data.get(key), dict) or not owned:
        continue
    merged = {name: value for name, value in data[key].items() if name not in owned}
    if merged == data[key]:
        continue
    if merged:
        data[key] = merged
    else:
        data.pop(key, None)
    save(path, data)

opencode = load(paths[1])
if opencode is not None and isinstance(opencode.get("instructions"), list):
    instructions = [item for item in opencode["instructions"] if item not in mash_instructions]
    if instructions != opencode["instructions"]:
        if instructions:
            opencode["instructions"] = instructions
        else:
            opencode.pop("instructions", None)
        save(paths[1], opencode)

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
remove_empty_dir "$MASH_CONFIG_DIR/references"
remove_empty_dir "$MASH_CONFIG_DIR/node_modules"
remove_empty_dir "$MASH_CONFIG_DIR/venvs"
remove_empty_dir "$MASH_CONFIG_DIR"
remove_global_gitignore_block

note ""
if [ "$APPLY" = true ]; then
    note "Mash Programming Skills global environment removed. Machine tools, Hindsight memory, and repositories were not changed."
else
    note "Dry run complete. No files changed."
fi
