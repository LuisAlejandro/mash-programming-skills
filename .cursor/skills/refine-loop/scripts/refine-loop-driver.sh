#!/usr/bin/env bash
#
# refine-loop-driver.sh — run refine-loop as a real loop, no OMC required.
#
# Each round invokes the agent CLI non-interactively with the
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
#   --agent=AGENT          Agent binary to invoke (default: opencode; alt: pi)
#   --workspace=PATH       Workspace root (default: current directory)
#   --model=MODEL          Optional model override passed to the agent
#   --dry-run              Print the agent command without running it
#
# The agent always runs unattended (opencode: --auto; pi: --approve): it
# executes in a shell the user cannot see or answer, so any approval prompt
# would hang the run.
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
AGENT="opencode"
DEFAULT_OPENCODE_MODEL="opencode/deepseek-v4-flash"
DEFAULT_PI_MODEL="deepseek-v4-flash"
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

  if [[ "$AGENT" == "pi" ]]; then
    local skill_md
    skill_md="$(cd "$(dirname "$0")/../.." && pwd)/refine-loop-iteration/SKILL.md"
    local model="${MODEL:-$DEFAULT_PI_MODEL}"
    local prompt="Run the refine-loop-iteration skill by reading and following ${skill_md} completely. Working directory is the repository."
    [[ "$continue_flag" == "1" ]] && prompt+=" --continue"
    [[ -n "$THETA" ]] && prompt+=" theta=$THETA"
    [[ -n "$FOCUS" ]] && prompt+=" focus=$FOCUS"
    if [[ ${#INTENT_ARGS[@]} -gt 0 ]]; then
      prompt+=" ${INTENT_ARGS[*]}"
    fi
    printf 'cd %q && pi -p --approve --mode json --model %q %q\n' "$WORKSPACE" "$model" "$prompt"
    return 0
  fi

  if [[ "$AGENT" == "opencode" ]]; then
    local skill_md
    skill_md="$(cd "$(dirname "$0")/../.." && pwd)/refine-loop-iteration/SKILL.md"
    local model="${MODEL:-$DEFAULT_OPENCODE_MODEL}"
    local prompt="Run the refine-loop-iteration skill by reading and following ${skill_md} completely. Working directory is the repository."
    [[ "$continue_flag" == "1" ]] && prompt+=" --continue"
    [[ -n "$THETA" ]] && prompt+=" theta=$THETA"
    [[ -n "$FOCUS" ]] && prompt+=" focus=$FOCUS"
    if [[ ${#INTENT_ARGS[@]} -gt 0 ]]; then
      prompt+=" ${INTENT_ARGS[*]}"
    fi
    printf 'cd %q && opencode run --model %q --auto %q\n' "$WORKSPACE" "$model" "$prompt"
    return 0
  fi

  echo "refine-loop-driver: unsupported agent '$AGENT' (supported: opencode, pi)" >&2
  return 2
}

# ---- automatic integration (rosey-parallel style) --------------------------
# After a terminal outcome, commit the deliverable worktree recorded in the
# backlog markers, merge into the fetched default branch, gate with repo lint,
# and advance the local default branch. Local-only: no push, no PR.
DEFAULT_BRANCH="$(cd "$WORKSPACE" && (git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#origin/##' || echo develop))"

loop_integrate() {
  [[ -f "$BACKLOG" ]] || return 0
  local branch worktree
  branch="$(grep -E '^\s*- integration branch: ' "$BACKLOG" | tail -1 | sed 's/.*: //' | tr -d '` ')"
  worktree="$(grep -E '^\s*- integration worktree: ' "$BACKLOG" | tail -1 | sed 's/.*: //' | tr -d '` ')"
  if [[ -z "$branch" || -z "$worktree" || ! -e "$worktree/.git" ]]; then
    echo "refine-loop-driver: integrate: no committed worktree markers found; skipped"
    return 0
  fi

  local int_wt="$WORKSPACE/rosey/loops/refine/integration"
  git -C "$WORKSPACE" worktree remove --force "$int_wt" 2>/dev/null || true
  git -C "$WORKSPACE" fetch origin "$DEFAULT_BRANCH" >/dev/null 2>&1 || true
  if ! git -C "$WORKSPACE" worktree add --detach "$int_wt" "origin/$DEFAULT_BRANCH" >/dev/null 2>&1; then
    echo "refine-loop-driver: integrate: cannot create integration worktree" >&2
    return 1
  fi

  if ! git -C "$int_wt" merge --no-ff "$branch" -m "refine: integrate refine-loop deliverable ($branch)" >/tmp/loop-merge.log 2>&1; then
    echo "refine-loop-driver: integrate: merge conflict on '$branch'; deliverable preserved at $worktree" >&2
    git -C "$int_wt" merge --abort 2>/dev/null || true
    git -C "$WORKSPACE" worktree remove --force "$int_wt" 2>/dev/null || true
    return 1
  fi

  echo "refine-loop-driver: integrate: merged; running lint gate"
  local gate_ok=1 attempt
  for attempt in 1 2; do
    (cd "$int_wt" && docker run --rm -v "$PWD":/home/agoras/app -w /home/agoras/app \
      luisalejandro/agoras:latest tox -e lint) && { gate_ok=0; break; }
    echo "refine-loop-driver: integrate: lint gate attempt $attempt failed; retrying" >&2
    sleep 10
  done
  if [[ "$gate_ok" -ne 0 ]]; then
    echo "refine-loop-driver: integrate: lint gate FAILED; develop not advanced; merged tree at $int_wt" >&2
    return 1
  fi

  local tip
  tip="$(git -C "$int_wt" rev-parse HEAD)"
  git -C "$WORKSPACE" branch -f "$DEFAULT_BRANCH" "$tip"
  git -C "$WORKSPACE" worktree remove --force "$int_wt" 2>/dev/null || true
  echo "refine-loop-driver: integrate: OK — local '$DEFAULT_BRANCH' advanced to $(git -C "$WORKSPACE" rev-parse --short "$DEFAULT_BRANCH")"
  git -C "$WORKSPACE" worktree remove --force "$worktree" 2>/dev/null && \
    git -C "$WORKSPACE" branch -D "$branch" 2>/dev/null || true
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
    loop_integrate
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
