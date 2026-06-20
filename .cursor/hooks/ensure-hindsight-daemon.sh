#!/usr/bin/env bash
# Rosey sessionStart hook: ensure Hindsight embed daemon is running when configured.
# Fail open — Hindsight is optional; never block the Cursor session on startup errors.

exec 0</dev/null

if [ ! -f "${HOME}/.hindsight/embed" ] && [ ! -f "${HOME}/.hindsight/config.env" ]; then
    exit 0
fi

if ! command -v uvx >/dev/null 2>&1; then
    exit 0
fi

HINDSIGHT_EMBED=(uvx hindsight-embed@0.8.2)

if "${HINDSIGHT_EMBED[@]}" daemon status >/dev/null 2>&1; then
    exit 0
fi

HINDSIGHT_EMBED_DAEMON_STARTUP_TIMEOUT="${HINDSIGHT_EMBED_DAEMON_STARTUP_TIMEOUT:-600}" \
    "${HINDSIGHT_EMBED[@]}" daemon start >/dev/null 2>&1 || true

exit 0
