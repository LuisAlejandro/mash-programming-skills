#!/usr/bin/env bash
#
# goal-loop-driver.sh — run goal-loop as a real loop, no OMC required.
#
# Each iteration invokes the agent CLI non-interactively with the
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
#   --agent=AGENT          Agent binary to invoke (default: opencode; alt: pi)
#   --workspace=PATH       Workspace root (default: current directory)
#   --model=MODEL          Optional model override passed to the agent
#   --dry-run              Print the agent command without running it
#
# The agent always runs unattended (opencode: --auto; pi: --approve): it
# executes in a shell the user cannot see or answer, so any approval prompt
# would hang the run.
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
AGENT="opencode"
WORKSPACE="$(pwd)"
MODEL=""
DEFAULT_OPENCODE_MODEL="opencode/deepseek-v4-flash"
DEFAULT_PI_MODEL="deepseek-v4-flash"
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
# Runs fully unattended (opencode: --auto; pi: --approve).
build_cmd() {
  local continue_flag="$1"

  if [[ "$AGENT" == "pi" ]]; then
    local skill_md
    skill_md="$(cd "$(dirname "$0")/../.." && pwd)/goal-loop-iteration/SKILL.md"
    local model="${MODEL:-$DEFAULT_PI_MODEL}"
    local prompt="Run the goal-loop-iteration skill by reading and following ${skill_md} completely. Working directory is the repository."
    [[ "$continue_flag" == "1" ]] && prompt+=" --continue"
    prompt+=" --max-iterations=$MAX_ITERATIONS --no-progress-limit=$NO_PROGRESS_LIMIT --failure-limit=$FAILURE_LIMIT"
    prompt+=" Goal: $GOAL"
    printf 'cd %q && pi -p --approve --mode json --model %q %q\n' "$WORKSPACE" "$model" "$prompt"
    return 0
  fi

  if [[ "$AGENT" == "opencode" ]]; then
    local skill_md
    skill_md="$(cd "$(dirname "$0")/../.." && pwd)/goal-loop-iteration/SKILL.md"
    local model="${MODEL:-$DEFAULT_OPENCODE_MODEL}"
    local prompt="Run the goal-loop-iteration skill by reading and following ${skill_md} completely. Working directory is the repository."
    [[ "$continue_flag" == "1" ]] && prompt+=" --continue"
    prompt+=" --max-iterations=$MAX_ITERATIONS --no-progress-limit=$NO_PROGRESS_LIMIT --failure-limit=$FAILURE_LIMIT"
    prompt+=" Goal: $GOAL"
    printf 'cd %q && opencode run --model %q --auto %q\n' "$WORKSPACE" "$model" "$prompt"
    return 0
  fi

  echo "goal-loop-driver: unsupported agent '$AGENT' (supported: opencode, pi)" >&2
  return 2
}

# ---- automatic integration (rosey-parallel style) --------------------------
# After a terminal decision, commit the deliverable worktree recorded in the
# worklog markers, merge into the fetched default branch, gate with repo lint,
# and advance the local default branch. Local-only: no push, no PR.
DEFAULT_BRANCH="$(cd "$WORKSPACE" && (git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#origin/##' || echo develop))"

loop_integrate() {
  [[ -f "$WORKLOG" ]] || return 0
  local branch worktree
  branch="$(grep -E '^\s*- integration branch: ' "$WORKLOG" | tail -1 | sed 's/.*: //' | tr -d '` ')"
  worktree="$(grep -E '^\s*- integration worktree: ' "$WORKLOG" | tail -1 | sed 's/.*: //' | tr -d '` ')"
  if [[ -z "$branch" || -z "$worktree" || ! -e "$worktree/.git" ]]; then
    echo "goal-loop-driver: integrate: no committed worktree markers found; skipped"
    return 0
  fi

  local int_wt="$WORKSPACE/rosey/loops/goal/integration"
  git -C "$WORKSPACE" worktree remove --force "$int_wt" 2>/dev/null || true
  git -C "$WORKSPACE" fetch origin "$DEFAULT_BRANCH" >/dev/null 2>&1 || true
  if ! git -C "$WORKSPACE" worktree add --detach "$int_wt" "origin/$DEFAULT_BRANCH" >/dev/null 2>&1; then
    echo "goal-loop-driver: integrate: cannot create integration worktree" >&2
    return 1
  fi

  if ! git -C "$int_wt" merge --no-ff "$branch" -m "goal: integrate goal-loop deliverable ($branch)" >/tmp/loop-merge.log 2>&1; then
    echo "goal-loop-driver: integrate: merge conflict on '$branch'; deliverable preserved at $worktree" >&2
    git -C "$int_wt" merge --abort 2>/dev/null || true
    git -C "$WORKSPACE" worktree remove --force "$int_wt" 2>/dev/null || true
    return 1
  fi

  echo "goal-loop-driver: integrate: merged; running lint gate"
  local gate_ok=1 attempt
  for attempt in 1 2; do
    (cd "$int_wt" && docker run --rm -v "$PWD":/home/agoras/app -w /home/agoras/app \
      luisalejandro/agoras:latest tox -e lint) && { gate_ok=0; break; }
    echo "goal-loop-driver: integrate: lint gate attempt $attempt failed; retrying" >&2
    sleep 10
  done
  if [[ "$gate_ok" -ne 0 ]]; then
    echo "goal-loop-driver: integrate: lint gate FAILED; develop not advanced; merged tree at $int_wt" >&2
    return 1
  fi

  local tip
  tip="$(git -C "$int_wt" rev-parse HEAD)"
  git -C "$WORKSPACE" branch -f "$DEFAULT_BRANCH" "$tip"
  git -C "$WORKSPACE" worktree remove --force "$int_wt" 2>/dev/null || true
  echo "goal-loop-driver: integrate: OK — local '$DEFAULT_BRANCH' advanced to $(git -C "$WORKSPACE" rev-parse --short "$DEFAULT_BRANCH")"
  git -C "$WORKSPACE" worktree remove --force "$worktree" 2>/dev/null && \
    git -C "$WORKSPACE" branch -D "$branch" 2>/dev/null || true
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
    loop_integrate
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
