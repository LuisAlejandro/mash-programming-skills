#!/usr/bin/env bash
# Bulk uninstaller: run uninstall.sh across every repository in install.list.
#
# All arguments are forwarded to uninstall.sh, so the default is a DRY RUN:
#   ./bulk-uninstall.sh                          # plan for every repo (safe)
#   ./bulk-uninstall.sh --check                  # which repos have Rosey installed
#   ./bulk-uninstall.sh --apply --yes            # actually remove repo-local artifacts
#   ./bulk-uninstall.sh --apply --yes --targets=cursor,vscode
#
# Safety: because this touches many repositories at once, --apply is refused
# unless --yes is also passed. Machine-wide tools and user data are never
# removed by uninstall.sh (it is repo-local only).
#
# Entries that are missing (unmounted volume, deleted folder) are skipped.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIST_FILE="${INSTALL_LIST:-$SCRIPT_DIR/install.list}"
UNINSTALL_SH="$SCRIPT_DIR/uninstall.sh"

CHECKING=false
APPLYING=false
CONFIRMED=false

for arg in "$@"; do
    case "$arg" in
        -h | --help)
            sed -n '2,15p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        --check) CHECKING=true ;;
        --apply) APPLYING=true ;;
        --yes) CONFIRMED=true ;;
    esac
done

if [ ! -f "$LIST_FILE" ]; then
    echo "Error: list file not found: $LIST_FILE" >&2
    exit 1
fi

if [ ! -f "$UNINSTALL_SH" ]; then
    echo "Error: uninstall.sh not found: $UNINSTALL_SH" >&2
    exit 1
fi

if [ "$APPLYING" = true ] && [ "$CONFIRMED" != true ]; then
    echo "Error: bulk --apply requires --yes (this would mutate every repository in $LIST_FILE)." >&2
    echo "   Run without --apply first to review the plan for each repo." >&2
    exit 1
fi

ok=0
fail=0
skip=0
absent=0

while IFS= read -r dir || [ -n "$dir" ]; do
    [[ -z "$dir" || "$dir" =~ ^[[:space:]]*# ]] && continue
    dir="${dir%"${dir##*[![:space:]]}"}"

    if [ ! -d "$dir" ]; then
        echo "SKIP (missing): $dir"
        skip=$((skip + 1))
        continue
    fi

    if [ "$CHECKING" = true ]; then
        rc=0
        (cd "$dir" && bash "$UNINSTALL_SH" --check >/dev/null 2>&1) || rc=$?
        if [ "$rc" -eq 0 ]; then
            echo "INSTALLED: $dir"
            ok=$((ok + 1))
        elif [ "$rc" -eq 1 ]; then
            echo "NOT INSTALLED: $dir"
            absent=$((absent + 1))
        else
            echo "FAIL: $dir" >&2
            fail=$((fail + 1))
        fi
        continue
    fi

    echo "==== Uninstalling from $dir ===="
    if (cd "$dir" && bash "$UNINSTALL_SH" "$@"); then
        ok=$((ok + 1))
    else
        echo "FAIL: $dir" >&2
        fail=$((fail + 1))
    fi
done < "$LIST_FILE"

echo
if [ "$CHECKING" = true ]; then
    echo "Done. installed=$ok not-installed=$absent fail=$fail skip=$skip"
else
    echo "Done. ok=$ok fail=$fail skip=$skip"
fi
[ "$fail" -eq 0 ]
