#!/usr/bin/env bash
# Mash Programming Skills Hindsight warm-start: ensure embed daemon is running when configured.
# Cursor: registered via ~/.cursor/hooks.json sessionStart.
# OpenCode: ~/.config/opencode/plugin/mash-hindsight-daemon.ts.
# Pi: ~/.pi/agent/extensions/mash-hindsight-daemon.ts session_start hook.
# Fail open — Hindsight is optional; never block the IDE session on startup errors.
#
# Requires `uv tool install hindsight-embed==<pin> --with hindsight-api==<pin>`
# (run by install.sh when Hindsight is configured). No uvx fallback — cold starts
# belong in install, not warm-start.

exec 0</dev/null

HINDSIGHT_HOOK_LOG="${HOME}/.hindsight/hook-last-run.log"
HINDSIGHT_HOOK_LOG_MAX="${HINDSIGHT_HOOK_LOG_MAX:-1048576}" # 1 MiB before rotate

# Repo attribution: which project triggered this hook run. The log is shared
# across every Mash Programming Skills repo, so each entry records its repo root basename.
REPO="$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")"

hindsight_hook_log() {
    mkdir -p "${HOME}/.hindsight"
    # Rotate before appending so the log never grows unbounded.
    if [ -f "$HINDSIGHT_HOOK_LOG" ] && [ "$(wc -c <"$HINDSIGHT_HOOK_LOG")" -ge "$HINDSIGHT_HOOK_LOG_MAX" ]; then
        mv -f "$HINDSIGHT_HOOK_LOG" "${HINDSIGHT_HOOK_LOG}.1"
    fi
    printf '%s [%s] %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$REPO" "$*" >>"$HINDSIGHT_HOOK_LOG"
}

read_hindsight_pin() {
    local pin_file="${MASH_CONFIG_DIR:-${HOME}/.config/mash}/hindsight-pin"
    if [ -f "$pin_file" ]; then
        tr -d '[:space:]' <"$pin_file"
    else
        echo "0.8.3"
    fi
}

if [ ! -f "${HOME}/.hindsight/embed" ] && [ ! -f "${HOME}/.hindsight/config.env" ]; then
    exit 0
fi

# Cursor hook env may omit ~/.local/bin (uv tool install shims).
PATH="${HOME}/.local/bin:${PATH}"

# Port of the default profile's daemon (mirrors profile_manager._resolve_ports).
daemon_port() {
    local cfg port=""
    for cfg in "${HOME}/.hindsight/embed" "${HOME}/.hindsight/config.env"; do
        [ -f "$cfg" ] || continue
        port="$(sed -n 's/^HINDSIGHT_API_PORT=\([0-9][0-9]*\).*/\1/p' "$cfg" | tail -1)"
        [ -n "$port" ] && break
    done
    printf '%s' "${port:-8888}"
}

# `hindsight-embed daemon status` is a bare `GET /health == 200`, so any service
# squatting on the daemon port is mistaken for Hindsight. Require the /version
# fingerprint instead.
daemon_healthy() {
    local port
    if ! command -v curl >/dev/null 2>&1; then
        hindsight-embed daemon status >/dev/null 2>&1
        return $?
    fi
    port="$(daemon_port)"
    curl -fsS -m 2 "http://127.0.0.1:${port}/version" 2>/dev/null | grep -q '"api_version"'
}

HINDSIGHT_PIN="$(read_hindsight_pin)"

if ! command -v hindsight-embed >/dev/null 2>&1; then
    hindsight_hook_log "hindsight-embed not on PATH (pin ${HINDSIGHT_PIN}); re-run install.sh (uv tool install)"
    exit 0
fi

if daemon_healthy; then
    hindsight_hook_log "daemon already up (pin ${HINDSIGHT_PIN})"
    exit 0
fi

if hindsight-embed daemon status >/dev/null 2>&1; then
    # Not Hindsight, but the port answers /health: a foreign service holds it.
    # `daemon start` would refuse to act, so report instead of pretending.
    hindsight_hook_log "port $(daemon_port) answers /health but is not Hindsight; daemon not started (pin ${HINDSIGHT_PIN})"
    exit 0
fi

if HINDSIGHT_EMBED_DAEMON_STARTUP_TIMEOUT="${HINDSIGHT_EMBED_DAEMON_STARTUP_TIMEOUT:-60}" \
    hindsight-embed daemon start >>"$HINDSIGHT_HOOK_LOG" 2>&1; then
    hindsight_hook_log "daemon started (pin ${HINDSIGHT_PIN})"
else
    hindsight_hook_log "daemon start failed (pin ${HINDSIGHT_PIN}); see log above; retry via install.sh"
fi

exit 0
