#!/usr/bin/env bash
# Compatibility wrapper: Rosey uninstallation is machine-global now.
# The old fleet loop is intentionally gone; repositories are never touched.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/uninstall.sh" "$@"
