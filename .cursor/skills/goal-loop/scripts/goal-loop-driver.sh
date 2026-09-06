#!/usr/bin/env bash
#
# goal-loop-driver.sh — run goal-loop as a real loop, no OMC required.
#
# Each iteration invokes the Cursor agent non-interactively with the
# goal-loop-iteration skill. State lives on disk (GOAL.md / GOAL-WORKLOG.md), so
# every iteration starts fresh and resumes from the last recorded next action.
# The loop stops when the worklog records a terminal stop decision.
#
# Usage:
#   goal-loop-driver.sh [--max-iterations=N] \
#       [--no-progress-limit=N] [--failure-limit=N] [--agent=AGENT] <goal...>
#
# Options:
#   --max-iterations=N     Hard cap on iterations (default: 50)
#   --no-progress-limit=N  Consecutive no-progress cap (default: 3)
#   --failure-limit=N      Consecutive failure cap (default: 3)
#   --agent=AGENT          Agent binary to invoke (default: cursor-agent)
#   --workspace=PATH       Workspace root (default: current directory)
#   --model=MODEL          Optional model override passed to the agent
#   --dry-run              Print the agent command without running it
#
# The agent always runs unattended (--yolo --trust): it executes in a shell the
# user cannot see or answer, so any approval prompt would hang the run.
#
# State always lives under <workspace>/rosey/loops/goal/.
#
# The remaining text is the goal, passed verbatim to goal-loop.

set -euo pipefail

# ---- defaults -------------------------------------------------------------
STATE_DIR="rosey/loops/goal"
MAX_ITERATIONS=50
NO_PROGRESS_LIMIT=3
FAILURE_LIMIT=3
AGENT="cursor-agent"
WORKSPACE="$(pwd)"
MODEL=""
DRY_RUN=0

# ---- parse leading options ------------------------------------------------
GOAL_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --max-iterations=*) MAX_ITERATIONS="${1#*=}" ;;
    --no-progress-limit=*) NO_PROGRESS_LIMIT="${1#*=}" ;;
    --failure-limit=*) FAILURE_LIMIT="${1#*=}" ;;
    --agent=*) AGENT="${1#*=}" ;;
    --workspace=*) WORKSPACE="${1#*=}" ;;
    --model=*) MODEL="${1#*=}" ;;
    --dry-run) DRY_RUN=1 ;;
    --) shift; GOAL_ARGS+=("$@"); break ;;
    -*) echo "unknown option: $1" >&2; exit 2 ;;
    *) GOAL_ARGS+=("$@"); break ;;
  esac
  shift
done

if [[ ${#GOAL_ARGS[@]} -eq 0 ]]; then
  echo "error: no goal supplied" >&2
  exit 2
fi
GOAL="${GOAL_ARGS[*]}"

# Validate numeric options.
for v in "$MAX_ITERATIONS" "$NO_PROGRESS_LIMIT" "$FAILURE_LIMIT"; do
  if ! [[ "$v" =~ ^[1-9][0-9]*$ ]]; then
    echo "error: numeric options must be positive integers (got '$v')" >&2
    exit 2
  fi
done

# Resolve state dir relative to the workspace.
STATE_DIR_ABS="$WORKSPACE/$STATE_DIR"
WORKLOG="$STATE_DIR_ABS/GOAL-WORKLOG.md"

# ---- terminal-state detection ---------------------------------------------
# The worklog records a stop decision per iteration. A terminal decision ends
# the loop. We read only the newest entry's decision.
terminal_state() {
  [[ -f "$WORKLOG" ]] || return 1
  # Find the last "Stop decision:" line that is not "continue".
  local decision
  decision="$(grep -E '^\s*- Stop decision: ' "$WORKLOG" | tail -n 1 || true)"
  case "$decision" in
    *SUCCESS*|*BLOCKED*|*BUDGET*|*ERROR*|*CANCELLED*) echo "$decision" ;;
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
  cmd+=(-- "goal-loop-iteration")
  [[ "$continue_flag" == "1" ]] && cmd+=("--continue")
  cmd+=("--state-dir=$STATE_DIR")
  cmd+=("--max-iterations=$MAX_ITERATIONS")
  cmd+=("--no-progress-limit=$NO_PROGRESS_LIMIT")
  cmd+=("--failure-limit=$FAILURE_LIMIT")
  cmd+=("--" "$GOAL")
  printf '%q ' "${cmd[@]}"
}

# ---- run ------------------------------------------------------------------
echo "goal-loop-driver: workspace=$WORKSPACE state=$STATE_DIR_ABS"
echo "goal-loop-driver: goal=$GOAL"
echo "goal-loop-driver: max_iterations=$MAX_ITERATIONS no_progress=$NO_PROGRESS_LIMIT failures=$FAILURE_LIMIT"
echo

iteration=0
continue_flag=0
while true; do
  # Check for a terminal decision in the worklog before running. This catches
  # a pre-existing terminal state and the result of the previous iteration.
  if decision="$(terminal_state)"; then
    echo
    echo "goal-loop-driver: terminal state reached: $decision"
    echo "goal-loop-driver: done after $iteration iteration(s)."
    exit 0
  fi

  iteration=$((iteration + 1))
  if [[ $iteration -gt $MAX_ITERATIONS ]]; then
    echo "goal-loop-driver: reached max_iterations=$MAX_ITERATIONS; stopping." >&2
    exit 1
  fi

  echo "=== iteration $iteration ($(date -u +%Y-%m-%dT%H:%M:%SZ)) ==="
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

  # Run the agent. Non-zero exit is not fatal here: the worklog is the source
  # of truth for whether the loop should continue.
  eval "$cmd" || echo "  agent exited with status $? (continuing based on worklog)" >&2

  # After the first iteration, subsequent ones resume.
  continue_flag=1

  echo
done
