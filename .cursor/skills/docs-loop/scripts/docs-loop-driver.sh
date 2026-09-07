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
AGENT="opencode"
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
# Docs-loop runs fully unattended; every agent must execute without approval
# prompts (cursor-agent: --yolo/--trust; opencode: --auto).
DEFAULT_OPENCODE_MODEL="opencode/deepseek-v4-flash"

build_cmd() {
  if [[ "$AGENT" == "opencode" ]]; then
    local skill_md
    skill_md="$(cd "$(dirname "$0")/../.." && pwd)/docs-loop-iteration/SKILL.md"
    local model="${MODEL:-$DEFAULT_OPENCODE_MODEL}"
    local prompt="Run the docs-loop-iteration skill by reading and following ${skill_md} completely. Working directory is the repository to audit."
    if [[ ${#REPO_ARGS[@]} -gt 0 ]]; then
      prompt+=" Repositories: ${REPO_ARGS[*]}"
    fi
    # opencode has no --workspace flag; run inside the workspace dir.
    printf 'cd %q && opencode run --model %q --auto %q\n' "$WORKSPACE" "$model" "$prompt"
    return 0
  fi

  # cursor-agent / generic CLI shape (kept for --agent=cursor-agent).
  local -a cmd=("$AGENT" -p --workspace "$WORKSPACE")
  [[ -n "$MODEL" ]] && cmd+=(--model "$MODEL")
  cmd+=(--yolo --trust)
  cmd+=(-- "docs-loop-iteration")
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

# ---- automatic integration (rosey-parallel style) --------------------------
# After a terminal state, commit the deliverable in its worktree, merge it into
# the local default branch, gate with repo lint, and advance the default branch.
# Local-only: no push, no PR. On conflict or gate failure the deliverable is
# preserved and the default branch is not moved.
DEFAULT_BRANCH="$(cd "$WORKSPACE" && (git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#origin/##' || echo develop))"

loop_integrate() {
  local row branch worktree base
  row="$(grep -E '^\|\s*[0-9]+\s*\|' "$LEDGER" | head -1)"
  [[ -z "$row" ]] && { echo "docs-loop-driver: integrate: no repository row; skipped"; return 0; }
  # Table: | # | path | remote | default branch | base commit | branch | worktree | status | deliverable |
  branch="$(printf '%s\n' "$row" | awk -F'|' '{gsub(/^ +| +$/, "", $7); print $7}')"
  worktree="$(printf '%s\n' "$row" | awk -F'|' '{gsub(/^ +| +$/, "", $8); print $8}')"

  if [[ -z "$branch" || -z "$worktree" || ! -e "$worktree/.git" ]]; then
    echo "docs-loop-driver: integrate: deliverable worktree/branch not found; skipped"
    return 0
  fi

  echo "docs-loop-driver: integrate: committing deliverable in $worktree"
  (cd "$worktree" && git add -A && git -c user.name=rosey -c user.email=rosey@local \
    commit -m "docs: apply docs-loop audit fixes" >/dev/null 2>&1) || true

  local int_wt="$WORKSPACE/rosey/loops/docs/integration"
  git -C "$WORKSPACE" worktree remove --force "$int_wt" 2>/dev/null || true
  # Merge against the latest default-branch tip, then advance the local ref.
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

  # Deliverable merged: clean up the worktree and its branch.
  git -C "$WORKSPACE" worktree remove --force "$worktree" 2>/dev/null && \
    git -C "$WORKSPACE" branch -D "$branch" 2>/dev/null || true
}

iteration=0
while true; do
  # Check for a terminal state in the ledger before running. This catches a
  # pre-existing terminal state and the result of the previous pass.
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
