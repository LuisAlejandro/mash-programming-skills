#!/usr/bin/env bash
# Rosey Agentic Environment — uninstaller (repo-local).
#
# Reverses install.sh for ONE target repository. It removes the Rosey-owned
# artifacts that install.sh writes into the install root, and surgically edits
# the shared files it touches (.vscode/tasks.json, opencode.json).
#
# Scope: repo-local only. This script never removes machine-wide tools (uv, bun,
# jq, rg, gh, git-flow, Sentrux, uv tools, Pi extensions, hindsight-embed), user
# data under rosey/ (brainstorms, plans, insights, solutions, ...), or
# ~/.hindsight memory. Those are shared across repositories and are left alone.
#
# Safe by default: without --apply the script only prints a plan. Use
#   ./uninstall.sh              # dry run
#   ./uninstall.sh --apply      # remove repo-local artifacts
#
# Usage: uninstall.sh [--check] [--version] [--apply] [--yes] [--force]
#                      [--targets=cursor,vscode,opencode,pi]
#                      [--purge-git-config]

set -euo pipefail

INSTALL_ROOT="$(pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="${ROSEY_AGENTIC_ENV:-$SCRIPT_DIR}"
VERSION_FILE="$SOURCE_ROOT/VERSION"
UNINSTALL_VERSION="0.1.0"
if [ -f "$VERSION_FILE" ]; then
    UNINSTALL_VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"
fi

APPLY=false
CHECK_ONLY=false
YES=false
FORCE=false
PURGE_GIT_CONFIG=false
TARGETS="cursor,vscode,opencode,pi"

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
            YES=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --targets=*)
            TARGETS="${1#*=}"
            shift
            ;;
        --purge-git-config)
            PURGE_GIT_CONFIG=true
            shift
            ;;
        -h | --help)
            sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

want_target() {
    case ",$TARGETS," in
        *",$1,"*) return 0 ;;
        *) return 1 ;;
    esac
}

# install.sh refuses to install into its own source tree; same guard here.
if [ "$INSTALL_ROOT" = "$SOURCE_ROOT" ]; then
    echo "Error: refusing to uninstall the Rosey Agentic Environment from its own source repository." >&2
    echo "   Run this script from the target project directory, or set ROSEY_AGENTIC_ENV." >&2
    exit 1
fi

# --- Reporting helpers ------------------------------------------------------

removed=0
edited=0
kept=0

note() { printf '%s\n' "$*"; }

warn() { printf '   ! %s\n' "$*"; }

# Print a python edit result and count it only when it actually changed something.
report_edit() {
    if [ -n "$1" ]; then
        printf '%s\n' "$1"
        edited=$((edited + 1))
    fi
}

# remove_tree <path> [label]
remove_tree() {
    local path="$1" label="${2:-$1}"
    if [ ! -e "$path" ] && [ ! -L "$path" ]; then
        return 0
    fi
    if [ "$APPLY" = true ]; then
        rm -rf -- "$path"
        note "   removed       $label"
    else
        note "   would remove  $label"
    fi
    removed=$((removed + 1))
}

# remove_file_if_marker <path> <marker> [label] [expected-tail]
# Removes a generated file only when it still carries the Rosey marker AND, when
# an expected tail is given, still ends with that exact generated line. This
# preserves a file the user has appended to (unless --force).
remove_file_if_marker() {
    local path="$1" marker="$2" label="${3:-$1}" tail="${4:-}"
    [ -e "$path" ] || return 0
    if [ "$FORCE" = true ]; then
        remove_tree "$path" "$label (forced)"
        return 0
    fi
    if ! grep -qF -- "$marker" "$path" 2>/dev/null; then
        warn "$label looks user-owned; keeping it (use --force to remove)"
        kept=$((kept + 1))
        return 0
    fi
    if [ -n "$tail" ]; then
        local last
        last="$(grep -v '^[[:space:]]*$' "$path" | tail -n 1)"
        if [ "$last" != "$tail" ]; then
            warn "$label has user content after the Rosey block; keeping it (use --force to remove)"
            kept=$((kept + 1))
            return 0
        fi
    fi
    remove_tree "$path" "$label"
}

# prune_empty_dir <dir>  — rmdir only if empty, and only the Rosey-owned dirs.
prune_empty_dir() {
    local dir="$1"
    [ -d "$dir" ] || return 0
    if [ -n "$(ls -A "$dir" 2>/dev/null)" ]; then
        return 0
    fi
    if [ "$APPLY" = true ]; then
        rmdir -- "$dir" 2>/dev/null || true
    fi
}

# --- Installed detection ----------------------------------------------------

INSTALLED_MARKERS=(
    rosey/agentic-env.json
    .cursor/rules
    .github/copilot-instructions.md
    .opencode/skills
    .pi/APPEND_SYSTEM.md
)

# Rosey residue from older installs that current install.sh no longer writes:
# a stale Cursor pin file, an OpenCode MCP seed, and a Pi settings MCP block.
# These outlive a normal uninstall, so they count as work to do as well.
RESIDUE_MARKERS=(
    .cursor/hindsight-pin
    .opencode/mcp.json
)

is_installed() {
    local marker
    for marker in "${INSTALLED_MARKERS[@]}"; do
        [ -e "$marker" ] && return 0
    done
    return 1
}

has_pi_mcp_settings() {
    [ -f .pi/settings.json ] && grep -q '"mcp"' .pi/settings.json 2>/dev/null
}

has_residue() {
    local marker
    for marker in "${RESIDUE_MARKERS[@]}"; do
        [ -e "$marker" ] && return 0
    done
    has_pi_mcp_settings && return 0
    return 1
}

if [ "$CHECK_ONLY" = true ]; then
    if is_installed || has_residue; then
        note "Rosey Agentic Environment is installed in $INSTALL_ROOT"
        [ -f rosey/agentic-env.json ] && cat rosey/agentic-env.json
        exit 0
    fi
    note "Rosey Agentic Environment is not installed in $INSTALL_ROOT"
    exit 1
fi

if ! is_installed && ! has_residue; then
    note "Nothing to uninstall: no Rosey artifacts found in $INSTALL_ROOT"
    exit 0
fi

if [ "$APPLY" = false ]; then
    note "Rosey Agentic Environment — DRY RUN (pass --apply to make changes)"
else
    note "Rosey Agentic Environment — uninstalling from $INSTALL_ROOT"
fi
note "-> Version $UNINSTALL_VERSION, source $SOURCE_ROOT"
note ""

# --- Repo-local artifact trees ---------------------------------------------

CURSOR_PATHS=(
    .cursor/rules
    .cursor/skills
    .cursor/agents
    .cursor/hooks
    .cursor/hooks.json
    .cursor/mcp.json
    .cursor/hindsight-pin
)
VSCODE_PATHS=(
    .github/copilot-instructions.md
    .github/instructions
    .github/skills
    .github/agents
    .github/hooks
)
OPENCODE_PATHS=(
    .opencode/skills
    .opencode/agents
    .opencode/rules
    .opencode/hooks
    .opencode/hooks.json
    .opencode/mcp.json
)
PI_PATHS=(
    .pi/skills
    .pi/agents
    .pi/APPEND_SYSTEM.md
    .pi/scripts
    .pi/extensions
    .pi/mcp.json
)
SHARED_PATHS=(
    .agents/shared
    rosey/agentic-env.json
    rosey/hindsight-pin
)

remove_all() {
    local path
    for path in "$@"; do
        remove_tree "$path"
    done
}

note "-> IDE trees"
if want_target cursor; then
    remove_all "${CURSOR_PATHS[@]}"
fi
if want_target vscode; then
    remove_all "${VSCODE_PATHS[@]}"
    # .vscode/mcp.json is seeded by install; the folderOpen task is edited below.
    remove_tree .vscode/mcp.json
fi
if want_target opencode; then
    remove_all "${OPENCODE_PATHS[@]}"
fi
if want_target pi; then
    remove_all "${PI_PATHS[@]}"
fi

note "-> Shared artifacts"
remove_all "${SHARED_PATHS[@]}"

# Generated agent guidance files only if they still match what install wrote.
if want_target cursor || want_target vscode; then
    remove_file_if_marker AGENTS.md \
        "Rosey Agent Guidance" \
        "AGENTS.md" \
        'Hindsight version pin: `rosey/hindsight-pin`.'
    remove_file_if_marker .cursorrules \
        "Rosey Agent Guidance" \
        ".cursorrules" \
        'Hindsight version pin: `rosey/hindsight-pin`.'
fi

# --- Shared file surgery (python3 for JSON) --------------------------------

note "-> Shared config files"

# .vscode/tasks.json: drop only the Rosey folderOpen task, keep user tasks.
if want_target vscode && [ -f .vscode/tasks.json ]; then
    out="$(python3 - .vscode/tasks.json "$APPLY" <<'PY'
import json, sys
from pathlib import Path

path = Path(sys.argv[1])
apply = sys.argv[2] == "true"
label = "Rosey: ensure Hindsight daemon"
try:
    data = json.loads(path.read_text())
except Exception:
    print("   ! .vscode/tasks.json is not valid JSON; leaving it untouched")
    raise SystemExit(0)
if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
    raise SystemExit(0)

before = len(data["tasks"])
tasks = [t for t in data["tasks"] if not (isinstance(t, dict) and t.get("label") == label)]
if len(tasks) == before:
    raise SystemExit(0)

verb_rm = "removed      " if apply else "would remove "
verb_ed = "edited       " if apply else "would edit   "
if not tasks and set(data.keys()) <= {"version", "tasks"}:
    print(f"   {verb_rm} .vscode/tasks.json (only held the Rosey task)")
    if apply:
        path.unlink()
    raise SystemExit(0)

data["tasks"] = tasks
print(f"   {verb_ed} .vscode/tasks.json (Rosey folderOpen task)")
if apply:
    path.write_text(json.dumps(data, indent=2) + "\n")
PY
)"
    report_edit "$out"
fi

# opencode.json: drop the seeded mcp block, plugin, and added $schema.
if want_target opencode && [ -f opencode.json ]; then
    out="$(python3 - opencode.json "$APPLY" <<'PY'
import json, sys
from pathlib import Path

path = Path(sys.argv[1])
apply = sys.argv[2] == "true"
PLUGIN = "@monks1975/opencode-agent-hooks@1.0.1"
try:
    data = json.loads(path.read_text())
except Exception:
    print("   ! opencode.json is not valid JSON; leaving it untouched")
    raise SystemExit(0)
if not isinstance(data, dict):
    raise SystemExit(0)

changed = False
if data.pop("mcp", None) is not None:
    changed = True
plugins = data.get("plugin")
if isinstance(plugins, list):
    kept = [p for p in plugins if p != PLUGIN]
    if kept != plugins:
        changed = True
    if kept:
        data["plugin"] = kept
    else:
        data.pop("plugin", None)
if data.get("$schema") == "https://opencode.ai/config.json":
    data.pop("$schema", None)
    changed = True
if not changed:
    raise SystemExit(0)

verb_rm = "removed      " if apply else "would remove "
verb_ed = "edited       " if apply else "would edit   "
if not data:
    print(f"   {verb_rm} opencode.json (only held Rosey config)")
    if apply:
        path.unlink()
else:
    print(f"   {verb_ed} opencode.json (mcp/plugin entries)")
    if apply:
        path.write_text(json.dumps(data, indent=2) + "\n")
PY
)"
    report_edit "$out"
fi

# .pi/settings.json: older installs seeded an "mcp" block here (with secrets).
# Remove only that key; drop the file when mcp was all it held.
if want_target pi && [ -f .pi/settings.json ]; then
    out="$(python3 - .pi/settings.json "$APPLY" <<'PY'
import json, sys
from pathlib import Path

path = Path(sys.argv[1])
apply = sys.argv[2] == "true"
try:
    data = json.loads(path.read_text())
except Exception:
    print("   ! .pi/settings.json is not valid JSON; leaving it untouched")
    raise SystemExit(0)
if not isinstance(data, dict) or "mcp" not in data:
    raise SystemExit(0)

data.pop("mcp")
verb_rm = "removed      " if apply else "would remove "
verb_ed = "edited       " if apply else "would edit   "
if not data:
    print(f"   {verb_rm} .pi/settings.json (only held the Rosey mcp block)")
    if apply:
        path.unlink()
else:
    print(f"   {verb_ed} .pi/settings.json (Rosey mcp block)")
    if apply:
        path.write_text(json.dumps(data, indent=2) + "\n")
PY
)"
    report_edit "$out"
fi

# Orphaned OpenCode plugin artifacts: once the Rosey-only opencode.json is gone,
# .opencode/ holds nothing but opencode's own dependency install.
if want_target opencode && [ ! -e opencode.json ]; then
    remove_tree .opencode/node_modules
    remove_tree .opencode/package.json
    remove_tree .opencode/package-lock.json
    remove_tree .opencode/.gitignore
fi

# Per-repo .gitignore is no longer touched: install.sh writes Rosey ignores to
# the user's global excludes file, which uninstall never modifies.

# --- Empty-dir cleanup ------------------------------------------------------

note "-> Empty directories"
if want_target cursor; then prune_empty_dir .cursor; fi
if want_target opencode; then prune_empty_dir .opencode; fi
if want_target pi; then prune_empty_dir .pi; fi
if want_target vscode; then
    prune_empty_dir .github/hooks
    prune_empty_dir .github/instructions
    prune_empty_dir .github/skills
    prune_empty_dir .github/agents
    prune_empty_dir .vscode
fi
prune_empty_dir .agents
prune_empty_dir rosey

# --- Optional: repo-local git config ---------------------------------------

if [ "$PURGE_GIT_CONFIG" = true ]; then
    note "-> Repo-local git config (--purge-git-config)"
    if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        warn "not a git repository; skipping"
    elif [ "$APPLY" = true ] && [ "$YES" = true ]; then
        git config --local --unset user.signingkey 2>/dev/null \
            && note "   removed local user.signingkey" \
            || warn "no local user.signingkey set"
        note "   note: git-flow branches/config are NOT touched (never delete branches automatically)"
    else
        warn "would unset local user.signingkey (needs --apply --yes)"
    fi
fi

# --- Summary ----------------------------------------------------------------

note ""
if [ "$APPLY" = true ]; then
    note "Rosey Environment uninstalled from $INSTALL_ROOT"
else
    note "Dry run complete. Re-run with --apply to remove the items above."
fi
note "   removed: $removed   edited: $edited   kept (user-modified): $kept"
note "   Never touched: machine-wide tools, rosey/ user data, ~/.hindsight."
note "   If this repo had a pre-existing AGENTS.md, review it for leftover Rosey lines."
