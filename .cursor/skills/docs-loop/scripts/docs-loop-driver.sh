#!/usr/bin/env bash
#
# docs-loop-driver.sh — run docs-loop as a real loop, no OMC required.
#
# Each pass invokes the Cursor agent non-interactively with the
# docs-loop-iteration skill, which processes one repository. State lives on disk
# (DOCS-LOOP-LEDGER.md), so every pass starts fresh and resumes from the last
# recorded next repository. The loop stops when the ledger records every
# repository as terminal (no PENDING or IN-PROGRESS rows remain).
#
# Usage:
#   docs-loop-driver.sh [--max-iterations=N] [--agent=AGENT] \
#       [--workspace=PATH] [--model=MODEL] [--root=PATH | REPO_PATH ...]
#
# Options:
#   --max-iterations=N     Hard cap on passes (default: 50)
#   --agent=AGENT          Agent binary to invoke (default: cursor-agent)
#   --workspace=PATH       Workspace root (default: current directory)
#   --model=MODEL          Optional model override passed to the agent
#   --dry-run              Print the agent command without running it
#
# The agent always runs unattended (--yolo --trust): it executes in a shell the
# user cannot see or answer, so any approval prompt would hang the run.
#
# State always lives under <workspace>/rosey/loops/docs/.
#
# The remaining text is the repository path list (or empty for the current repo).

set -euo pipefail

# ---- defaults -------------------------------------------------------------
STATE_DIR="rosey/loops/docs"
MAX_ITERATIONS=50
AGENT="cursor-agent"
WORKSPACE="$(pwd)"
MODEL=""
DRY_RUN=0

# ---- parse leading options ------------------------------------------------
REPO_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --max-iterations=*) MAX_ITERATIONS="${1#*=}" ;;
    --agent=*) AGENT="${1#*=}" ;;
    --workspace=*) WORKSPACE="${1#*=}" ;;
    --model=*) MODEL="${1#*=}" ;;
    --dry-run) DRY_RUN=1 ;;
    --) shift; REPO_ARGS+=("$@"); break ;;
    -*) echo "unknown option: $1" >&2; exit 2 ;;
    *) REPO_ARGS+=("$@"); break ;;
  esac
  shift
done

# Validate numeric options.
if ! [[ "$MAX_ITERATIONS" =~ ^[1-9][0-9]*$ ]]; then
  echo "error: --max-iterations must be a positive integer (got '$MAX_ITERATIONS')" >&2
  exit 2
fi

# Resolve state dir relative to the workspace.
STATE_DIR_ABS="$WORKSPACE/$STATE_DIR"
LEDGER="$STATE_DIR_ABS/DOCS-LOOP-LEDGER.md"

# ---- terminal-state detection ---------------------------------------------
# The ledger records one row per repository with a Status. The loop is done when
# no row is PENDING or IN-PROGRESS. We also read the run result line.
terminal_state() {
  [[ -f "$LEDGER" ]] || return 1
  # Any row still PENDING or IN-PROGRESS means the loop continues.
  if grep -Eq '^\|\s*[0-9]+\s*\|.*\|\s*(PENDING|IN-PROGRESS)\s*\|' "$LEDGER"; then
    return 1
  fi
  # No pending rows: report the run result if present.
  local result
  result="$(grep -E '^- result: ' "$LEDGER" | tail -n 1 || true)"
  case "$result" in
    *SUCCESS*|*BLOCKED*|*PARTIAL*) echo "$result" ;;
    *) echo "all repositories terminal" ;;
  esac
}

# ---- build the agent invocation -------------------------------------------
build_cmd() {
  local -a cmd=("$AGENT" -p --workspace "$WORKSPACE")
  [[ -n "$MODEL" ]] && cmd+=(--model "$MODEL")
  # Always unattended: --yolo runs everything without approval prompts; --trust
  # trusts the workspace without prompting. The agent runs in a shell the user
  # cannot see or answer, so any approval prompt would hang the run.
  cmd+=(--yolo --trust)
  cmd+=(-- "docs-loop-iteration")
  cmd+=("--state-dir=$STATE_DIR")
  if [[ ${#REPO_ARGS[@]} -gt 0 ]]; then
    cmd+=("--" "${REPO_ARGS[@]}")
  fi
  printf '%q ' "${cmd[@]}"
}

# ---- run ------------------------------------------------------------------
echo "docs-loop-driver: workspace=$WORKSPACE state=$STATE_DIR_ABS"
if [[ ${#REPO_ARGS[@]} -gt 0 ]]; then
  echo "docs-loop-driver: repos=${REPO_ARGS[*]}"
else
  echo "docs-loop-driver: repos=<current repository>"
fi
echo "docs-loop-driver: max_iterations=$MAX_ITERATIONS"
echo

iteration=0
while true; do
  # Check for a terminal state in the ledger before running. This catches a
  # pre-existing terminal state and the result of the previous pass.
  if result="$(terminal_state)"; then
    echo
    echo "docs-loop-driver: terminal state reached: $result"
    echo "docs-loop-driver: done after $iteration pass(es)."
    exit 0
  fi

  iteration=$((iteration + 1))
  if [[ $iteration -gt $MAX_ITERATIONS ]]; then
    echo "docs-loop-driver: reached max_iterations=$MAX_ITERATIONS; stopping." >&2
    exit 1
  fi

  echo "=== pass $iteration ($(date -u +%Y-%m-%dT%H:%M:%SZ)) ==="

  cmd="$(build_cmd)"
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "  [dry-run] $cmd"
    continue
  fi

  # Run the agent. Non-zero exit is not fatal here: the ledger is the source of
  # truth for whether the loop should continue.
  eval "$cmd" || echo "  agent exited with status $? (continuing based on ledger)" >&2

  echo
done
