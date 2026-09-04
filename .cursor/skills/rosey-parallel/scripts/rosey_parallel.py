#!/usr/bin/env python3
"""rosey-parallel helper.

Run-state, input validation, footprint parsing, sequencing, worktree ops,
harness drivers, phase runners, and integration for the rosey-parallel skill.

Single stdlib module; the coordinating agent invokes subcommands. State
mutations route through the orchestrator process only (workers write their own
log files), so no cross-process shared-JSON writes exist.
"""

from __future__ import annotations

import json
import re
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Run state (plan U1: R22, R23, R24)
# ---------------------------------------------------------------------------

# Task status enum per the plan's High-Level Technical Design state machine.
STATUS_PENDING = "pending"
STATUS_PLANNING = "planning"
STATUS_PLANNED = "planned"
STATUS_GATE_APPROVED = "gate_approved"
STATUS_WORKING = "working"
STATUS_QA = "qa"
STATUS_LINT = "lint"
STATUS_DONE = "done"
STATUS_FIX_UP = "fix_up"
STATUS_BLOCKED = "blocked"
STATUS_FAILED = "failed"
STATUS_TIMEOUT = "timeout"
STATUS_BLOCKED_BY = "blocked_by"

STATUSES = frozenset(
    {
        STATUS_PENDING,
        STATUS_PLANNING,
        STATUS_PLANNED,
        STATUS_GATE_APPROVED,
        STATUS_WORKING,
        STATUS_QA,
        STATUS_LINT,
        STATUS_DONE,
        STATUS_FIX_UP,
        STATUS_BLOCKED,
        STATUS_FAILED,
        STATUS_TIMEOUT,
        STATUS_BLOCKED_BY,
    }
)

# Valid successors. Keep in lockstep with the state machine diagram.
TRANSITIONS = {
    STATUS_PENDING: {STATUS_PLANNING},
    STATUS_PLANNING: {STATUS_PLANNED, STATUS_BLOCKED, STATUS_TIMEOUT},
    STATUS_PLANNED: {STATUS_GATE_APPROVED, STATUS_BLOCKED_BY},
    STATUS_GATE_APPROVED: {STATUS_WORKING, STATUS_BLOCKED_BY},
    STATUS_WORKING: {STATUS_QA, STATUS_BLOCKED, STATUS_TIMEOUT, STATUS_FAILED},
    STATUS_QA: {STATUS_LINT, STATUS_TIMEOUT, STATUS_FAILED},
    STATUS_LINT: {STATUS_DONE, STATUS_TIMEOUT, STATUS_FAILED},
    STATUS_DONE: {STATUS_FIX_UP},
    STATUS_FIX_UP: {STATUS_WORKING},
    STATUS_BLOCKED: set(),
    STATUS_FAILED: set(),
    STATUS_TIMEOUT: set(),
    STATUS_BLOCKED_BY: set(),
}

TERMINAL_STATUSES = frozenset(
    {STATUS_BLOCKED, STATUS_FAILED, STATUS_TIMEOUT, STATUS_BLOCKED_BY}
)


class StateError(Exception):
    """Raised for state-schema and transition violations."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_run_id() -> str:
    """Run id: timestamp-based, unique per invocation second + counter."""
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def runs_root(repo_root: str | os.PathLike) -> Path:
    return Path(repo_root) / "rosey" / "runs"


def run_dir(repo_root: str | os.PathLike, run_id: str) -> Path:
    return runs_root(repo_root) / run_id


def state_path(repo_root: str | os.PathLike, run_id: str) -> Path:
    return run_dir(repo_root, run_id) / "state.json"


def new_task(task_id: str, goal: str, deps: list[str] | None = None) -> dict:
    """Fresh per-task record. Fields mirror plan R22."""
    return {
        "id": task_id,
        "goal": goal,
        "deps": list(deps or []),
        "status": STATUS_PENDING,
        "plan_path": None,
        "track": None,
        "worktree_path": None,
        "branch": None,
        "footprint": [],
        "touched_files": [],
        "start_sha": None,
        "end_sha": None,
        "blockers": [],
        "warnings": [],
    }


def new_run(
    run_id: str,
    tasks: list[dict],
    base_branch: str,
    base_sha: str,
    harness: str,
) -> dict:
    """Fresh run record. Fields mirror plan R22 (run-level + per task)."""
    return {
        "version": 1,
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "base_branch": base_branch,
        "base_sha_snapshot": base_sha,
        "harness": harness,
        "gate": None,
        "fix_up_round": 0,
        "tracks": [],
        "tasks": {task["id"]: task for task in tasks},
    }


def transition(task: dict, new_status: str) -> None:
    """Advance a task's status through the transition table. Mutates task."""
    if new_status not in STATUSES:
        raise StateError(
            f"unknown status {new_status!r} for task {task['id']!r}"
        )
    allowed = TRANSITIONS.get(task["status"], set())
    if new_status not in allowed:
        raise StateError(
            f"invalid transition {task['status']!r} -> {new_status!r} "
            f"for task {task['id']!r}"
        )
    task["status"] = new_status


def atomic_write_json(path: str | os.PathLike, data: dict) -> None:
    """Write JSON atomically: temp file in the same dir, then os.replace."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n")
    os.replace(tmp, target)


def load_state(path: str | os.PathLike) -> dict:
    """Read and validate a run-state file (resume path)."""
    target = Path(path)
    try:
        raw = target.read_text()
    except OSError as exc:
        raise StateError(f"cannot read state file {target}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise StateError(f"corrupt state JSON in {target}: {exc}") from exc
    _validate_state(data, source=target)
    return data


def _validate_state(data: dict, source: Path) -> None:
    if not isinstance(data, dict):
        raise StateError(f"state in {source} is not a JSON object")
    for key in ("version", "run_id", "base_branch", "base_sha_snapshot", "tasks"):
        if key not in data:
            raise StateError(f"state in {source} missing required key {key!r}")
    if not isinstance(data["tasks"], dict) or not data["tasks"]:
        raise StateError(f"state in {source} has empty or invalid tasks map")
    for task_id, task in data["tasks"].items():
        if task_id != task.get("id"):
            raise StateError(
                f"state in {source}: task key {task_id!r} != task id {task.get('id')!r}"
            )
        if task.get("status") not in STATUSES:
            raise StateError(
                f"state in {source}: task {task_id!r} has unknown status "
                f"{task.get('status')!r}"
            )


def save_run(repo_root: str | os.PathLike, run: dict) -> Path:
    """Persist run state atomically. Returns the state file path."""
    path = state_path(repo_root, run["run_id"])
    atomic_write_json(path, run)
    return path


def load_run(repo_root: str | os.PathLike, run_id: str) -> dict:
    """Resume path: load run state, raising a clear error when unusable."""
    return load_state(state_path(repo_root, run_id))


# ---------------------------------------------------------------------------
# Footprint parsing (plan U3: R5)
# ---------------------------------------------------------------------------

_UNIT_HEADING = re.compile(r"^###\s+U\d+", re.MULTILINE)
_FILES_LINE = re.compile(r"^\s*-\s*\*\*Files:\*\*\s*(.+)$", re.MULTILINE)
_BACKTICK = re.compile(r"`([^`]+)`")


def parse_footprint(plan_text: str) -> tuple[set[str], list[str]]:
    """Parse a rosey plan's per-unit ``**Files:**`` sections.

    Returns (files, warnings). files is a set of repo-relative paths; a plan
    with no parseable footprint yields an empty set plus a plan-quality
    warning (task defaults to singleton track per R5).
    """
    warnings: list[str] = []
    files: set[str] = set()

    # Split into units; keep the preamble separate for warning attribution.
    sections: list[tuple[str | None, str]] = []
    matches = list(_UNIT_HEADING.finditer(plan_text))
    if not matches:
        sections.append((None, plan_text))
    else:
        if matches[0].start() > 0:
            sections.append((None, plan_text[: matches[0].start()]))
        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(plan_text)
            sections.append((plan_text[m.start():m.end()].strip(), plan_text[m.start():end]))

    for heading, body in sections:
        unit_files: list[str] = []
        for fm in _FILES_LINE.finditer(body):
            raw = fm.group(1)
            # Backticked paths first; fall back to comma-split bare tokens.
            candidates = _BACKTICK.findall(raw)
            if not candidates:
                candidates = [tok.strip() for tok in raw.split(",")]
            for tok in candidates:
                tok = tok.strip()
                # Strip trailing annotations like "(create)" / "(modify)".
                tok = re.sub(r"\s*\((?:create|modify|new|test)\)\s*$", "", tok).strip()
                if not tok or tok.lower() in {"(none)", "none", "-"}:
                    continue
                if "/" not in tok and not tok.endswith(".py") and not tok.endswith(".md"):
                    continue  # not a path-shaped token
                unit_files.append(tok)
        if heading is not None and not unit_files:
            warnings.append(f"unit {heading!r} has a Files section with no parseable paths")
        files.update(unit_files)

    if not files:
        warnings.append(
            "plan has no parseable file footprint; task defaults to a singleton track"
        )
    return files, warnings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--self-check":
        _self_check()
        return 0
    print(
        "usage: rosey_parallel.py --self-check\n"
        "(subcommands land with later units)",
        file=sys.stderr,
    )
    return 2


def _self_check() -> None:
    """Minimal smoke: state round-trip + transition enforcement."""
    run = new_run(new_run_id(), [new_task("t1", "demo")], "develop", "abc123", "pi")
    assert run["tasks"]["t1"]["status"] == STATUS_PENDING
    transition(run["tasks"]["t1"], STATUS_PLANNING)
    try:
        transition(run["tasks"]["t1"], STATUS_WORKING)
    except StateError:
        pass
    else:
        raise AssertionError("invalid transition was not rejected")
    print("self-check ok")


if __name__ == "__main__":
    sys.exit(main())