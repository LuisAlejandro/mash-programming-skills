#!/usr/bin/env bash
# Rosey Hindsight warm-start: ensure embed daemon is running when configured.
# Cursor: registered via .cursor/hooks.json sessionStart.
# VS Code: registered via .vscode/tasks.json runOn folderOpen (Copilot has no session hooks).
# OpenCode: .opencode/hooks.json SessionStart via opencode-agent-hooks plugin.
# Pi: .pi/extensions/rosey-hindsight-daemon.ts session_start hook.
# Fail open — Hindsight is optional; never block the IDE session on startup errors.
#
# Requires `uv tool install hindsight-embed==<pin> --with hindsight-api==<pin>`
# (run by install.sh when Hindsight is configured). No uvx fallback — cold starts
# belong in install, not warm-start.

exec 0</dev/null

HINDSIGHT_HOOK_LOG="${HOME}/.hindsight/hook-last-run.log"
HINDSIGHT_HOOK_LOG_MAX="${HINDSIGHT_HOOK_LOG_MAX:-1048576}" # 1 MiB before rotate

# Repo attribution: which project triggered this hook run. The log is shared
# across every Rosey repo, so each entry records its repo root basename.
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
    local pin_file=".cursor/hindsight-pin"
    if [ -f "$pin_file" ]; then
        tr -d '[:space:]' <"$pin_file"
    else
        echo "0.8.2"
    fi
}

if [ ! -f "${HOME}/.hindsight/embed" ] && [ ! -f "${HOME}/.hindsight/config.env" ]; then
    exit 0
fi

# Cursor hook env may omit ~/.local/bin (uv tool install shims).
PATH="${HOME}/.local/bin:${PATH}"

HINDSIGHT_PIN="$(read_hindsight_pin)"

if ! command -v hindsight-embed >/dev/null 2>&1; then
    hindsight_hook_log "hindsight-embed not on PATH (pin ${HINDSIGHT_PIN}); re-run install.sh (uv tool install)"
    exit 0
fi

if hindsight-embed daemon status >/dev/null 2>&1; then
    hindsight_hook_log "daemon already up (pin ${HINDSIGHT_PIN})"
    exit 0
fi

if HINDSIGHT_EMBED_DAEMON_STARTUP_TIMEOUT="${HINDSIGHT_EMBED_DAEMON_STARTUP_TIMEOUT:-60}" \
    hindsight-embed daemon start >>"$HINDSIGHT_HOOK_LOG" 2>&1; then
    hindsight_hook_log "daemon started (pin ${HINDSIGHT_PIN})"
else
    hindsight_hook_log "daemon start failed (pin ${HINDSIGHT_PIN}); see log above; retry via install.sh"
fi

exit 0
