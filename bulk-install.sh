#!/usr/bin/env bash
# Bulk installer: run install.sh across every repository in install.list.
#
# All arguments are forwarded to install.sh, e.g.:
#   ./bulk-install.sh --check
#   ./bulk-install.sh --write-pin --agents
#   ./bulk-install.sh --no-agents
#
# Entries that are missing (unmounted volume, deleted folder) are skipped.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIST_FILE="${INSTALL_LIST:-$SCRIPT_DIR/install.list}"
INSTALL_SH="$SCRIPT_DIR/install.sh"

while [ "$#" -gt 0 ]; do
    case "$1" in
        -h | --help)
            sed -n '2,9p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            break
            ;;
    esac
done

if [ ! -f "$LIST_FILE" ]; then
    echo "Error: list file not found: $LIST_FILE" >&2
    exit 1
fi

if [ ! -f "$INSTALL_SH" ]; then
    echo "Error: install.sh not found: $INSTALL_SH" >&2
    exit 1
fi

ok=0
fail=0
skip=0

while IFS= read -r dir || [ -n "$dir" ]; do
    [[ -z "$dir" || "$dir" =~ ^[[:space:]]*# ]] && continue
    dir="${dir%"${dir##*[![:space:]]}"}"

    if [ ! -d "$dir" ]; then
        echo "SKIP (missing): $dir"
        skip=$((skip + 1))
        continue
    fi

    echo "==== Installing into $dir ===="
    if (cd "$dir" && bash "$INSTALL_SH" "$@"); then
        ok=$((ok + 1))
    else
        echo "FAIL: $dir" >&2
        fail=$((fail + 1))
    fi
done < "$LIST_FILE"

echo
echo "Done. ok=$ok fail=$fail skip=$skip"
[ "$fail" -eq 0 ]
