#!/usr/bin/env bash
# Network-free release checks shared by Push CI and published-tag verification.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
expected_tag="${1:-}"

version="$(tr -d '[:space:]' < VERSION)"
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "VERSION must be X.Y.Z (got: $version)" >&2
    exit 1
fi

config_version="$(sed -nE 's/^current_version[[:space:]]*=[[:space:]]*//p' .bumpversion.cfg | tr -d '[:space:]')"
if [[ "$config_version" != "$version" ]]; then
    echo ".bumpversion.cfg ($config_version) does not match VERSION ($version)" >&2
    exit 1
fi
if [[ -n "$expected_tag" && "$expected_tag" != "$version" ]]; then
    echo "Release tag ($expected_tag) does not match VERSION ($version)" >&2
    exit 1
fi

for file in install.sh uninstall.sh scripts/preflight.sh scripts/lib.sh scripts/release.sh scripts/rollback.sh .gitchangelog.rc .gitchangelog.tpl RELEASE_DESCRIPTION.md HISTORY.md; do
    if [[ ! -f "$file" ]]; then
        echo "Missing release input: $file" >&2
        exit 1
    fi
done

for file in install.sh uninstall.sh scripts/*.sh; do
    bash -n "$file"
done
if [[ "$(bash install.sh --version)" != "$version" ]]; then
    echo "Installer version does not match VERSION ($version)" >&2
    exit 1
fi

printf 'Release inputs and shell syntax verified for %s\n' "$version"
