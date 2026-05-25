#!/usr/bin/env bash
set -euo pipefail

# Writes git log snapshots to docs/memory-bank/_diffs/recent.tmp (log text, not patches).
# Cursor: docs/memory-bank/_state/HEAD.sha (full SHA written by --record after a run).
# First run (no valid .sha): last 100 commits only. Later: commits since recorded SHA up to HEAD.
#
# Usage:
#   bash .cursor/scripts/memory-update.sh
#   bash .cursor/scripts/memory-update.sh --record

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workspace_root="$(cd "$script_dir/../.." && pwd)"
record_only=0

usage() {
  echo "Usage: $0 [--record]" >&2
  echo "  Capture: writes docs/memory-bank/_diffs/recent.tmp from git log." >&2
  echo "  --record: writes docs/memory-bank/_state/HEAD.sha = git rev-parse HEAD." >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --record)
      record_only=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

snapshots_dir="${workspace_root}/docs/memory-bank/_diffs"
state_dir="${workspace_root}/docs/memory-bank/_state"
state_file="${state_dir}/HEAD.sha"
out="${snapshots_dir}/recent.tmp"
FIRST_RUN_LIMIT=100

record_repo_head() {
  mkdir -p "$state_dir"
  (
    cd "$workspace_root"
    git rev-parse HEAD
  ) >"$state_file"
  echo "📌 Recorded HEAD → $state_file"
}

capture_repo_log() {
  mkdir -p "$snapshots_dir"

  (
    cd "$workspace_root"

    local head_sha
    head_sha="$(git rev-parse HEAD)"

    local log_range_label=""
    local -a log_cmd

    if [[ -f "$state_file" ]]; then
      local old_sha
      old_sha="$(tr -d '[:space:]' <"$state_file")"
      if [[ -n "$old_sha" ]] && git cat-file -e "${old_sha}^{commit}" 2>/dev/null; then
        local count
        count="$(git rev-list --count "${old_sha}..HEAD" 2>/dev/null || echo 0)"
        if [[ "$count" -eq 0 ]]; then
          rm -f "$out"
          echo "⏭ No new commits since last run (HEAD=$head_sha)"
          return 0
        fi
        log_cmd=(git --no-pager log --reverse --name-status "${old_sha}..HEAD")
        log_range_label="${old_sha}..HEAD (${count} commits)"
      else
        echo "⚠️  Invalid or unreadable stored SHA; using first-run limit (${FIRST_RUN_LIMIT} commits)" >&2
        log_cmd=(git --no-pager log -n "$FIRST_RUN_LIMIT" --reverse --name-status)
        log_range_label="FIRST_RUN: last ${FIRST_RUN_LIMIT} commits"
      fi
    else
      log_cmd=(git --no-pager log -n "$FIRST_RUN_LIMIT" --reverse --name-status)
      log_range_label="FIRST_RUN: last ${FIRST_RUN_LIMIT} commits"
    fi

    {
      echo "MEMORY BANK UPDATE REQUEST"
      echo "ROOT: $workspace_root"
      echo "SOURCE: git_log"
      echo "RANGE: $log_range_label"
      echo "HEAD: $head_sha"
      echo "Generated: $(date '+%Y-%m-%d %H:%M')"
      echo "============================================"
      echo "COMMITS:"
      echo "============================================"
      "${log_cmd[@]}" --pretty=format:'---COMMIT---%n%H%n%an <%ae> %ad%n%s%n%b'
    } >"$out"
    echo "📋 git log → $out"
  )
}

echo "============================================"
if [[ "$record_only" -eq 1 ]]; then
  echo "   MEMORY BANK — record HEAD"
else
  echo "   MEMORY BANK — git log snapshot"
fi
echo "   $(date '+%Y-%m-%d %H:%M')"
echo "============================================"

if [[ "$record_only" -eq 1 ]]; then
  record_repo_head
else
  capture_repo_log
fi

echo "============================================"

if [[ "$record_only" -eq 1 ]]; then
  echo "✅ State file updated: ${state_file}"
else
  if [[ -f "$out" ]]; then
    echo "✅ Snapshot created: ${out}"
    echo "   Run the update-memory skill, then: bash .cursor/scripts/memory-update.sh --record"
  else
    echo "✅ No new commits to snapshot."
  fi
fi
echo "============================================"