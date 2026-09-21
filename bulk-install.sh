#!/usr/bin/env bash
# Compatibility wrapper: Rosey installation is machine-global now.
# The old fleet loop is intentionally gone; no repository receives IDE trees.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/install.sh" "$@"
