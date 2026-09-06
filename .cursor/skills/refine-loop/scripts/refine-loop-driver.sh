#!/usr/bin/env bash
#
# refine-loop-driver.sh — run refine-loop as a real loop, no OMC required.
#
# Each round invokes the Cursor agent non-interactively with the
# refine-loop-iteration skill. State lives on disk (REFINE-BACKLOG.md), so every
# round starts fresh and resumes from the last recorded state. The loop stops
# when the backlog records a terminal outcome.
#
# Usage:
#   refine-loop-driver.sh [theta=N] [focus=LENS,...] \
#       [--max-iterations=N] [--agent=AGENT] [--workspace=PATH] [--model=MODEL] <intent...>
#
# Options:
#   theta=N                ROI threshold (default: 2.0)
#   focus=LENS,...         Allowlisted lens subset
#   --max-iterations=N     Hard cap on rounds (default: 50)
#   --agent=AGENT          Agent binary to invoke (default: cursor-agent)
#   --workspace=PATH       Workspace root (default: current directory)
#   --model=MODEL          Optional model override passed to the agent
#   --dry-run              Print the agent command without running it
#
# The agent always runs unattended (--yolo --trust): it executes in a shell the
# user cannot see or answer, so any approval prompt would hang the run.
#
# The target is always the workspace root. State always lives under
# <workspace>/rosey/loops/refine/.
#
# The remaining text is the refinement intent.

set -euo pipefail

# ---- defaults -------------------------------------------------------------
STATE_DIR="rosey/loops/refine"
THETA=""
FOCUS=""
MAX_ITERATIONS=50
AGENT="cursor-agent"
WORKSPACE="$(pwd)"
MODEL=""
DRY_RUN=0

# ---- parse leading options ------------------------------------------------
INTENT_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    theta=*) THETA="${1#*=}" ;;
    focus=*) FOCUS="${1#*=}" ;;
    --max-iterations=*) MAX_ITERATIONS="${1#*=}" ;;
    --agent=*) AGENT="${1#*=}" ;;
    --workspace=*) WORKSPACE="${1#*=}" ;;
    --model=*) MODEL="${1#*=}" ;;
    --dry-run) DRY_RUN=1 ;;
    --) shift; INTENT_ARGS+=("$@"); break ;;
    -*) echo "unknown option: $1" >&2; exit 2 ;;
    *) INTENT_ARGS+=("$@"); break ;;
  esac
  shift
done

# Validate numeric options.
if ! [[ "$MAX_ITERATIONS" =~ ^[1-9][0-9]*$ ]]; then
  echo "error: --max-iterations must be a positive integer (got '$MAX_ITERATIONS')" >&2
  exit 2
fi
if [[ -n "$THETA" ]] && ! [[ "$THETA" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
  echo "error: theta must be a finite decimal (got '$THETA')" >&2
  exit 2
fi

# Resolve state dir relative to the workspace.
STATE_DIR_ABS="$WORKSPACE/$STATE_DIR"
BACKLOG="$STATE_DIR_ABS/REFINE-BACKLOG.md"

# ---- terminal-state detection ---------------------------------------------
# The backlog records the authoritative outcome. A terminal outcome ends the loop.
terminal_state() {
  [[ -f "$BACKLOG" ]] || return 1
  local outcome
  outcome="$(grep -E '^- \*\*outcome:\*\* ' "$BACKLOG" | tail -n 1 || true)"
  case "$outcome" in
    *SUCCESS*|*BUDGET*|*ERROR*|*NEEDS-FIX*|*CANCELLED*) echo "$outcome" ;;
    *) return 1 ;;
  esac
}

# ---- build the agent invocation -------------------------------------------
build_cmd() {
  local continue_flag="$1"
  local -a cmd=("$AGENT" -p --workspace "$WORKSPACE")
  [[ -n "$MODEL" ]] && cmd+=(--model "$MODEL")
  # Always unattended: --yolo runs everything without approval prompts; --trust
  # trusts the workspace without prompting. The agent runs in a shell the user
  # cannot see or answer, so any approval prompt would hang the run.
  cmd+=(--yolo --trust)
  cmd+=(-- "refine-loop-iteration")
  [[ "$continue_flag" == "1" ]] && cmd+=("--continue")
  [[ -n "$THETA" ]] && cmd+=("theta=$THETA")
  [[ -n "$FOCUS" ]] && cmd+=("focus=$FOCUS")
  if [[ ${#INTENT_ARGS[@]} -gt 0 ]]; then
    cmd+=("--" "${INTENT_ARGS[@]}")
  fi
  printf '%q ' "${cmd[@]}"
}

# ---- run ------------------------------------------------------------------
echo "refine-loop-driver: workspace=$WORKSPACE state=$STATE_DIR_ABS"
if [[ -n "$THETA" ]]; then
  echo "refine-loop-driver: theta=$THETA"
fi
if [[ -n "$FOCUS" ]]; then
  echo "refine-loop-driver: focus=$FOCUS"
fi
if [[ ${#INTENT_ARGS[@]} -gt 0 ]]; then
  echo "refine-loop-driver: intent=${INTENT_ARGS[*]}"
fi
echo "refine-loop-driver: max_iterations=$MAX_ITERATIONS"
echo

iteration=0
continue_flag=0
while true; do
  # Check for a terminal outcome in the backlog before running. This catches a
  # pre-existing terminal state and the result of the previous round.
  if outcome="$(terminal_state)"; then
    echo
    echo "refine-loop-driver: terminal state reached: $outcome"
    echo "refine-loop-driver: done after $iteration round(s)."
    exit 0
  fi

  iteration=$((iteration + 1))
  if [[ $iteration -gt $MAX_ITERATIONS ]]; then
    echo "refine-loop-driver: reached max_iterations=$MAX_ITERATIONS; stopping." >&2
    exit 1
  fi

  echo "=== round $iteration ($(date -u +%Y-%m-%dT%H:%M:%SZ)) ==="
  if [[ $continue_flag -eq 1 ]]; then
    echo "  resuming with --continue"
  else
    echo "  starting fresh"
  fi

  cmd="$(build_cmd "$continue_flag")"
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "  [dry-run] $cmd"
    continue_flag=1
    continue
  fi

  # Run the agent. Non-zero exit is not fatal here: the backlog is the source of
  # truth for whether the loop should continue.
  eval "$cmd" || echo "  agent exited with status $? (continuing based on backlog)" >&2

  # After the first round, subsequent ones resume.
  continue_flag=1

  echo
done
