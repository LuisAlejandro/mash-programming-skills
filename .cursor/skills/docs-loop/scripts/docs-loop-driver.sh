#!/usr/bin/env bash
#
# docs-loop-driver.sh — iterative documentation audit/fix loop for ONE repository
# (the workspace it is executed in). Each pass audits the documentation, applies
# supported fixes in an isolated worktree, and records an outcome in the ledger.
# The loop stops when the docs are fully updated and audited: two consecutive
# clean passes (no actionable findings) -> SUCCESS, or a budget/failure cap.
# On a terminal state the driver auto-integrates the deliverable into the local
# default branch (commit -> merge -> lint gate -> advance), local-only, no push.
#
# Usage:
#   docs-loop-driver.sh [--max-iterations=N] [--clean-passes=N]
#                       [--failure-limit=N] [--agent=AGENT] [--workspace=PATH]
#                       [--model=MODEL] [--dry-run]
#
# State lives under <workspace>/rosey/loops/docs/. Re-invoking resumes from the
# recorded state unless the run is terminal (then it only integrates).

set -euo pipefail

STATE_DIR="rosey/loops/docs"
MAX_ITERATIONS=12
CLEAN_PASSES=2
FAILURE_LIMIT=3
AGENT="opencode"
WORKSPACE="$(pwd)"
MODEL=""
DEFAULT_OPENCODE_MODEL="opencode/deepseek-v4-flash"
DRY_RUN=0

# ---- parse leading options ------------------------------------------------
REPO_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --max-iterations=*) MAX_ITERATIONS="${1#*=}" ;;
    --clean-passes=*) CLEAN_PASSES="${1#*=}" ;;
    --failure-limit=*) FAILURE_LIMIT="${1#*=}" ;;
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

for v in "$MAX_ITERATIONS" "$CLEAN_PASSES" "$FAILURE_LIMIT"; do
  if ! [[ "$v" =~ ^[1-9][0-9]*$ ]]; then
    echo "error: numeric options must be positive integers (got '$v')" >&2
    exit 2
  fi
done

STATE_DIR_ABS="$WORKSPACE/$STATE_DIR"
LEDGER="$STATE_DIR_ABS/DOCS-LOOP-LEDGER.md"

# ---- terminal-state detection ---------------------------------------------
# Terminal when the ledger's last result line is a stop state (the iteration
# skill writes IN-PROGRESS otherwise).
terminal_state() {
  [[ -f "$LEDGER" ]] || return 1
  local result
  result="$(grep -E '^- result: ' "$LEDGER" | tail -n 1 || true)"
  case "$result" in
    *SUCCESS*|*BUDGET*|*BLOCKED*|*ERROR*) echo "$result" ;;
    *) return 1 ;;
  esac
}

# ---- build the agent invocation -------------------------------------------
build_cmd() {
  if [[ "$AGENT" == "opencode" ]]; then
    local skill_md
    skill_md="$(cd "$(dirname "$0")/../.." && pwd)/docs-loop-iteration/SKILL.md"
    local model="${MODEL:-$DEFAULT_OPENCODE_MODEL}"
    local prompt="Run the docs-loop-iteration skill by reading and following ${skill_md} completely. Working directory is the repository whose documentation is audited."
    prompt+=" --max-iterations=$MAX_ITERATIONS --clean-passes=$CLEAN_PASSES --failure-limit=$FAILURE_LIMIT"
    printf 'cd %q && opencode run --model %q --auto %q\n' "$WORKSPACE" "$model" "$prompt"
    return 0
  fi

  # cursor-agent / generic CLI shape (kept for --agent=cursor-agent).
  local -a cmd=("$AGENT" -p --workspace "$WORKSPACE")
  [[ -n "$MODEL" ]] && cmd+=(--model "$MODEL")
  cmd+=(--yolo --trust)
  cmd+=(-- "docs-loop-iteration")
  cmd+=("--max-iterations=$MAX_ITERATIONS" "--clean-passes=$CLEAN_PASSES" "--failure-limit=$FAILURE_LIMIT")
  printf '%q ' "${cmd[@]}"
}

# ---- automatic integration (rosey-parallel style) --------------------------
DEFAULT_BRANCH="$(cd "$WORKSPACE" && (git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#origin/##' || echo develop))"

loop_integrate() {
  local branch worktree
  branch="$(grep -E '^\s*- integration branch: ' "$LEDGER" | tail -1 | sed 's/.*: //' | tr -d '` ')"
  worktree="$(grep -E '^\s*- integration worktree: ' "$LEDGER" | tail -1 | sed 's/.*: //' | tr -d '` ')"
  if [[ -z "$branch" || -z "$worktree" || ! -e "$worktree/.git" ]]; then
    echo "docs-loop-driver: integrate: no committed worktree markers found; skipped"
    return 0
  fi
  if [[ "$(git -C "$WORKSPACE" rev-list --count "origin/$DEFAULT_BRANCH".."$branch" 2>/dev/null || echo 0)" == "0" ]]; then
    echo "docs-loop-driver: integrate: no commits ahead of default branch; nothing to integrate"
    return 0
  fi

  local int_wt="$WORKSPACE/rosey/loops/docs/integration"
  git -C "$WORKSPACE" worktree remove --force "$int_wt" 2>/dev/null || true
  git -C "$WORKSPACE" fetch origin "$DEFAULT_BRANCH" >/dev/null 2>&1 || true
  if ! git -C "$WORKSPACE" worktree add --detach "$int_wt" "origin/$DEFAULT_BRANCH" >/dev/null 2>&1; then
    echo "docs-loop-driver: integrate: cannot create integration worktree" >&2
    return 1
  fi

  if ! git -C "$int_wt" merge --no-ff "$branch" -m "docs: integrate docs-loop deliverable ($branch)" >/tmp/loop-merge.log 2>&1; then
    echo "docs-loop-driver: integrate: merge conflict on '$branch'; deliverable preserved at $worktree" >&2
    git -C "$int_wt" merge --abort 2>/dev/null || true
    git -C "$WORKSPACE" worktree remove --force "$int_wt" 2>/dev/null || true
    return 1
  fi

  echo "docs-loop-driver: integrate: merged; running lint gate"
  local gate_ok=1 attempt
  for attempt in 1 2; do
    (cd "$int_wt" && docker run --rm -v "$PWD":/home/agoras/app -w /home/agoras/app \
      luisalejandro/agoras:latest tox -e lint) && { gate_ok=0; break; }
    echo "docs-loop-driver: integrate: lint gate attempt $attempt failed; retrying" >&2
    sleep 10
  done
  if [[ "$gate_ok" -ne 0 ]]; then
    echo "docs-loop-driver: integrate: lint gate FAILED; develop not advanced; merged tree at $int_wt" >&2
    return 1
  fi

  local tip
  tip="$(git -C "$int_wt" rev-parse HEAD)"
  git -C "$WORKSPACE" branch -f "$DEFAULT_BRANCH" "$tip"
  git -C "$WORKSPACE" worktree remove --force "$int_wt" 2>/dev/null || true
  echo "docs-loop-driver: integrate: OK — local '$DEFAULT_BRANCH' advanced to $(git -C "$WORKSPACE" rev-parse --short "$DEFAULT_BRANCH")"
  git -C "$WORKSPACE" worktree remove --force "$worktree" 2>/dev/null && \
    git -C "$WORKSPACE" branch -D "$branch" 2>/dev/null || true
}

# ---- run ------------------------------------------------------------------
echo "docs-loop-driver: workspace=$WORKSPACE state=$STATE_DIR_ABS"
echo "docs-loop-driver: max_iterations=$MAX_ITERATIONS clean_passes=$CLEAN_PASSES failures=$FAILURE_LIMIT"
echo

iteration=0
continue_flag=0
while true; do
  if result="$(terminal_state)"; then
    echo
    echo "docs-loop-driver: terminal state reached: $result"
    echo "docs-loop-driver: done after $iteration pass(es)."
    loop_integrate
    exit 0
  fi

  iteration=$((iteration + 1))
  if [[ $iteration -gt $MAX_ITERATIONS ]]; then
    echo "docs-loop-driver: reached max_iterations=$MAX_ITERATIONS; stopping." >&2
    exit 1
  fi

  echo "=== pass $iteration ($(date -u +%Y-%m-%dT%H:%M:%SZ)) ==="
  if [[ $continue_flag -eq 1 ]]; then
    echo "  resuming existing run"
  else
    echo "  starting fresh"
  fi

  cmd="$(build_cmd)"
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "  [dry-run] $cmd"
    continue_flag=1
    continue
  fi

  eval "$cmd" || echo "  agent exited with status $? (continuing based on ledger)" >&2
  continue_flag=1
  echo
done
