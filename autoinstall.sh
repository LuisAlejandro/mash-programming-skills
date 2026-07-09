#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIST_FILE="$SCRIPT_DIR/autoinstall.list"
INSTALL_SH="$SCRIPT_DIR/install.sh"

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
