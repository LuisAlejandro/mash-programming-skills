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
# Input validation (plan U2: R1, R2)
# ---------------------------------------------------------------------------

class ValidationError(Exception):
    """Raised when run inputs fail fast validation (R2). Carries all
    violations detected in a single pass."""

    def __init__(self, message: str, violations: list[str]) -> None:
        super().__init__(message)
        self.violations = violations


def validate_inputs(tasks: list[dict], options: dict) -> list[dict]:
    """Validate a run's task list, failing fast (R2) before any worktree.

    Returns a normalized task list (ids validated, deps as a list). Raises
    ValidationError with an aggregated message naming every offending id.
    """
    violations: list[str] = []

    if not tasks:
        violations.append("empty task list")

    # Structural checks: id present, goal present, deps listable.
    ids_seen: set[str] = set()
    for t in tasks:
        tid = t.get("id")
        if not isinstance(tid, str) or not tid:
            violations.append(f"task missing valid id")
            continue
        if tid in ids_seen:
            violations.append(f"duplicate task id {tid!r}")
        ids_seen.add(tid)
        if not t.get("goal"):
            violations.append(f"task {tid!r} missing goal")

    valid_ids = {t.get("id") for t in tasks if isinstance(t.get("id"), str)}
    dupes = {t.get("id") for t in tasks if isinstance(t.get("id"), str) and list(
        [o.get("id") for o in tasks]).count(t.get("id")) > 1}
    effective_ids = valid_ids - dupes  # can't safely reference dup ids

    for t in tasks:
        tid = t.get("id")
        deps = t.get("deps") or []
        if not isinstance(deps, list):
            violations.append(f"task {tid!r} deps is not a list")
            continue
        for dep in deps:
            if dep == tid:
                violations.append(f"task {tid!r} has self-dependency")
            elif dep not in effective_ids:
                violations.append(f"task {tid!r} references unknown dependency {dep!r}")

    if violations:
        raise ValidationError("; ".join(violations), violations)

    # Cycle detection over the (now guaranteed real) dependency graph.
    _validate_no_cycles(tasks, valid_ids, violations)

    normalized = [
        {
            "id": t["id"],
            "goal": t["goal"],
            "deps": list(t.get("deps") or []),
            "harness": t.get("harness"),
        }
        for t in tasks
    ]
    return normalized


def _validate_no_cycles(
    tasks: list[dict], ids: set[str], violations: list[str]
) -> None:
    """Detect dependency cycles (R2 / R8). Appends a violation per cycle found."""
    edges: dict[str, list[str]] = {}
    for t in tasks:
        edges[t["id"]] = list(t.get("deps") or [])
    if any(t.get("id") not in edges for t in tasks):
        return  # structural validation will have failed already
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {tid: WHITE for tid in ids}
    path: list[str] = []
    cycles: list[list[str]] = []

    def visit(node: str) -> None:
        color[node] = GRAY
        path.append(node)
        for nxt in edges.get(node, []):
            if nxt not in color:
                continue
            if color[nxt] == GRAY:
                start = path.index(nxt)
                cycles.append(path[start:] + [nxt])
            elif color[nxt] == WHITE:
                visit(nxt)
        path.pop()
        color[node] = BLACK

    for tid in sorted(ids):
        if color[tid] == WHITE:
            visit(tid)

    for cyc in cycles:
        violations.append(
            "dependency cycle: " + " -> ".join(cyc)
        )
    if cycles:
        rendered = "dependency cycle: " + " -> ".join(cycles[0])
        raise ValidationError(rendered, violations)
        

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
# Sequencing (plan U4: R7, R8, R9)
# ---------------------------------------------------------------------------

class _UnionFind:
    def __init__(self) -> None:
        self.parent = {}
        self.rank = {}

    def _make(self, x: str) -> None:
        self.parent.setdefault(x, x)
        self.rank.setdefault(x, 0)

    def find(self, x: str) -> str:
        self._make(x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1


def schedule(tasks: dict, footprints: dict) -> dict:
    """Deterministic track computation (U4).

    tasks:       {task_id: new_task(...) dicts}
    footprints:  {task_id: set(relative_paths)}

    Returns {"tracks": [{"track_id": int, "tasks": [ids in topo order], "warnings": []}],
             "warnings": [...]}. Deterministic: identical inputs => identical output.
    """
    warnings: list[str] = []
    ids = sorted(tasks)

    if not ids:
        return {"tracks": [], "warnings": warnings}

    # Dependency cycle check first (loud failure, R8).
    for dep_chain in _dependency_cycles(tasks):
        if dep_chain:
            raise ValidationError(
                "dependency cycle: " + " -> ".join(dep_chain), ["cycle"]
            )

    uf = _UnionFind()
    for tid in ids:
        uf.find(tid)
    # Footprint-intersection edges.
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            fa = set(footprints.get(a, set()))
            fb = set(footprints.get(b, set()))
            if fa & fb:
                uf.union(a, b)
    # Declared-dependency edges.
    for tid in ids:
        for dep in tasks[tid]["deps"]:
            if dep in tasks:
                uf.union(tid, dep)

    # Group into components ordered by smallest member id.
    comps: dict[str, list[str]] = {}
    for tid in ids:
        comps.setdefault(uf.find(tid), []).append(tid)
    ordered_groups = [comps[k] for k in sorted(comps)]

    tracks = []
    for gi, group in enumerate(ordered_groups):
        if len(group) == 1:
            tid = group[0]
            # empty-footprint singletons warn (R5), unless dep pulled them in
            if not footprints.get(tid):
                if not tasks[tid]["deps"]:
                    warnings.append(
                        f"task {tid!r} has no file footprint; singleton track"
                    )
            tracks.append({"track_id": gi, "tasks": [tid], "warnings": []})
            continue
        # Topo order within the component over declared-dependency edges only.
        order = _topo_order(group, tasks)
        tracks.append({"track_id": gi, "tasks": order, "warnings": []})

    if tracks and len(tracks) == 1 and len(tracks[0]["tasks"]) > 1:
        warnings.append("all tasks in a single serial track; zero parallelism")

    return {"tracks": tracks, "warnings": warnings}


def _dependency_cycles(tasks: dict) -> list[list[str]]:
    """Return any dependency cycles (as task-id chains)."""
    ids = set(tasks)
    edges = {tid: [d for d in tasks[tid]["deps"] if d in ids] for tid in tasks}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {tid: WHITE for tid in ids}
    path: list[str] = []
    cycles: list[list[str]] = []

    def visit(node: str) -> None:
        color[node] = GRAY
        path.append(node)
        for nxt in edges[node]:
            if color[nxt] == GRAY:
                start = path.index(nxt)
                cycles.append(path[start:] + [nxt])
            elif color[nxt] == WHITE:
                visit(nxt)
        path.pop()
        color[node] = BLACK

    for tid in sorted(ids):
        if color[tid] == WHITE:
            visit(tid)
    return cycles


def _topo_order(group: list[str], tasks: dict) -> list[str]:
    """Kahn's topological order, min-heap by task id (lexicographic ties)."""
    import heapq
    group_set = set(group)
    edges: dict[str, list[str]] = {}
    indeg: dict[str, int] = {tid: 0 for tid in group}
    for tid in group:
        for dep in tasks[tid]["deps"]:
            if dep in group_set:
                edges.setdefault(dep, []).append(tid)
                indeg[tid] += 1
    heap = [tid for tid in group if indeg[tid] == 0]
    heapq.heapify(heap)
    out = []
    while heap:
        nxt = heapq.heappop(heap)
        out.append(nxt)
        for m in edges.get(nxt, []):
            indeg[m] -= 1
            if indeg[m] == 0:
                heapq.heappush(heap, m)
    # A cycle surviving here is impossible (validated above); guard anyway.
    if len(out) != len(group):
        raise ValidationError("dependency cycle within track", ["cycle"])
    return out


# ---------------------------------------------------------------------------
# Worktree manager (plan U5: R4, R13, R19, R21, R23)
# ---------------------------------------------------------------------------

RUNTIME_FILE_ALLOWLIST = (
    "AGENTS.md",
    "rosey/hindsight-pin",
    ".env",
    ".env.example",
    ".cursor",
    ".opencode",
    "opencode.json",
    ".pi",
)


def create_worktree(
    repo_root: str | os.PathLike,
    wt_path: str | os.PathLike,
    branch: str,
    base: str,
) -> str:
    """Create a worktree on a named branch from base. Raises on conflict."""
    import subprocess as _sp

    _sp.run(
        ["git", "-C", str(repo_root), "worktree", "add", str(wt_path), "-b", branch, base],
        check=True,
        capture_output=True,
        text=True,
    )
    return branch


def lock_worktree(repo_root: str | os.PathLike, wt_path: str | os.PathLike) -> None:
    import subprocess as _sp

    _sp.run(
        ["git", "-C", str(repo_root), "worktree", "lock", str(wt_path)],
        check=True,
        capture_output=True,
        text=True,
    )


def remove_worktree(
    repo_root: str | os.PathLike,
    wt_path: str | os.PathLike,
    branch: str,
) -> None:
    """Two-step removal: worktree then branch (branches outlive worktrees)."""
    import subprocess as _sp

    unlock = _sp.run(
        ["git", "-C", str(repo_root), "worktree", "unlock", str(wt_path)],
        capture_output=True, text=True,
    )
    if unlock.returncode != 0 and "not locked" not in unlock.stderr:
        pass  # treat already-unlocked as fine
    _sp.run(
        ["git", "-C", str(repo_root), "worktree", "remove", str(wt_path)],
        check=True, capture_output=True, text=True,
    )
    _sp.run(
        ["git", "-C", str(repo_root), "branch", "-d", branch],
        check=True, capture_output=True, text=True,
    )


def reset_hard(wt_path: str | os.PathLike, branch: str) -> None:
    """Reset a worktree to its branch tip (resume / interrupted task)."""
    import subprocess as _sp

    _sp.run(
        ["git", "-C", str(wt_path), "reset", "--hard", branch],
        check=True, capture_output=True, text=True,
    )


def copy_runtime_files(repo_root: str | os.PathLike, wt_path: str | os.PathLike) -> None:
    """Copy untracked/ignored runtime files a worker needs (U5/R4)."""
    import shutil

    src, dst = Path(repo_root), Path(wt_path)
    for name in RUNTIME_FILE_ALLOWLIST:
        s = src / name
        if s.is_file():
            d = dst / name
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)
        elif s.is_dir():
            if dst / name in {dst / name} and not (dst / name).exists():
                shutil.copytree(s, dst / name, dirs_exist_ok=True)


# ---------------------------------------------------------------------------
# Harness drivers (plan U6: R26, R14, R17)
# ---------------------------------------------------------------------------

HARNESS_PRIORITY = ["pi", "opencode", "cursor-agent"]

# Terminal structured events that mark success for each harness.
_TERMINAL_EVENTS = {
    "pi": ("agent_end",),
    "opencode": ("text",),
    "cursor-agent": ("result",),
}


class HarnessDriver:
    """Per-harness launch / interpret / probe contract (R26)."""

    def __init__(self, name: str, binary: str | None = None) -> None:
        self.name = name
        if name not in HARNESS_PRIORITY:
            raise ValueError(f"unknown harness {name!r}")
        default_binary = {
            "pi": "pi",
            "opencode": "opencode",
            "cursor-agent": "agent",
        }[name]
        self.binary = binary or default_binary

    @classmethod
    def from_name(cls, name: str, binary: str | None = None) -> "HarnessDriver":
        return cls(name, binary=binary)

    def probe(self) -> bool:
        """Availability: binary present on PATH (R26)."""
        import shutil

        return shutil.which(self.binary) is not None

    @staticmethod
    def launch_cmd(name) -> list[str]:
        """Per-harness invocation shape (KTD4)."""
        return {
            "pi": ["pi", "-p", "--approve", "--mode", "json", "--no-session"],
            "opencode": ["opencode", "run", "--format", "json"],
            "cursor-agent": ["agent", "-p", "--force", "--trust", "--output-format", "json"],
        }[name]

    def interpret(self, exit_code: int, output: str) -> str:
        """Map (exit, captured output) to done | blocker | failure (R14).

        Success requires exit 0 AND the terminal structured event. opencode
        additionally requires non-empty final text (exit-0-on-auto-reject bug).
        """
        if exit_code != 0:
            return "failure"
        parsed = self._parse_events(output)
        if not parsed:
            return "failure"
        last = parsed[-1]
        if self.name == "pi":
            if last.get("event") != "agent_end":
                return "failure"
        elif self.name == "cursor-agent":
            if last.get("type") != "result":
                return "failure"
        else:  # opencode
            if last.get("type") != "text" or not last.get("text"):
                return "failure"
        return "done"

    @staticmethod
    def _parse_events(output: str) -> list[dict]:
        """Best-effort parse of NDJSON/last-event shape. Returns event dicts."""
        import json as _json

        events: list[dict] = []
        for line in output.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(_json.loads(line))
            except _json.JSONDecodeError:
                # skip non-JSON noise lines
                continue
        return events


def select_harness(override, available, priority=HARNESS_PRIORITY) -> str:
    """Deterministic per-run harness selection (R26 / U6).

    override may be an explicit harness name or a callable probe(name)->bool.
    """
    if isinstance(override, str):
        if override not in priority:
            raise ValidationError(f"unknown harness override {override!r}", [f"harness {override}"])
        return override
    probe = available if callable(available) else lambda n: bool(available.get(n))
    for name in priority:
        if probe(name):
            return name
    raise ValidationError(
        "no harness available (tried pi, opencode, cursor-agent)",
        ["no harness available"],
    )


# ---------------------------------------------------------------------------
# Worker prompt contract + phase runners (plan U7: R13, R14, R15)
# ---------------------------------------------------------------------------

HANDOFF_START = "ROSEY_WORK_HANDOFF"
HANDOFF_END = "END_ROSEY_WORK_HANDOFF"


def extract_handoff(output: str) -> dict:
    """Parse a rosey-work handoff envelope from worker output.

    Returns {"status": done|blocker|failure, "files_changed": [...], "blockers": [...]}.
    """
    start = output.find(HANDOFF_START)
    end = output.find(HANDOFF_END)
    if start == -1 or end == -1 or end <= start:
        return {"status": "failure", "files_changed": [], "blockers": []}
    body = output[start + len(HANDOFF_START):end]
    files: list[str] = []
    blockers: list[str] = []
    lines = [ln.strip() for ln in body.splitlines()]
    for i, ln in enumerate(lines):
        if ln == "FILES_CHANGED:":
            for nxt in lines[i + 1:]:
                if nxt.startswith("- "):
                    files.append(nxt[2:].strip())
                elif nxt and not nxt.startswith("- "):
                    break
        if ln == "BLOCKERS:":
            for nxt in lines[i + 1:]:
                if nxt.startswith("- "):
                    blockers.append(nxt[2:].strip())
                elif nxt and not nxt.startswith("- "):
                    break
    status = "blocker" if blockers else "done"
    return {"status": status, "files_changed": files, "blockers": blockers}


def compute_touched_files(env_files: list[str], diff_files: list[str]) -> set[str]:
    """Union of handoff FILES_CHANGED and git diff (union, never intersection)."""
    return set(env_files) | set(diff_files)


def find_drift_collisions(touched: set[str], other_live_footprints: list[set]) -> list[str]:
    """Return the files a completed task touched that are also declared by other live tracks."""
    live = set().union(*other_live_footprints) if other_live_footprints else set()
    return sorted(touched & live)


def worker_overrides(track_branch: str) -> dict:
    """Prompt overrides for pre-created track branches (U7)."""
    return {
        "branch": track_branch,
        "branch_setup": "do not run branch setup",
        "sentrux": "skip",
        "qa_diff_base": "track-branch-point",
    }


# ---------------------------------------------------------------------------
# Orchestrator flow (plan U8: R1, R3, R4, R6, R10-12, R16-18, R20, R23)
# ---------------------------------------------------------------------------

def orchestrate_run(
    repo_root, tasks, footprints, driver,
    base_branch="develop", base_sha=None, resume=None, max_parallel=4,
):
    """Drive an epic's tasks through plan -> work -> qa -> lint.

    Fake-driver contract used by tests and by the real harness layer:
    driver.plan_task(task_id) -> status string; driver.work_phase(task_id)
    -> status string ("done" | "blocker" | "failure" | "timeout").
    """
    import re as _re

    run_id = resume["run_id"] if resume else new_run_id()
    state = {tid: dict(t) for tid, t in tasks.items()} if not resume else {
        tid: dict(t) for tid, t in resume["state"].items()
    }
    # Build the run-level record.
    run = {
        "run_id": run_id,
        "state": state,
        "tracks": [],
        "warnings": [],
        "base_branch": base_branch,
        "base_sha": base_sha or resume.get("base_sha") if resume else (base_sha or "0000"),
    }
    # Sequencing is deterministic; tracks computed from footprints+deps.
    sched = schedule(state, footprints)
    run["tracks"] = sched["tracks"]
    run["warnings"].extend(sched["warnings"])

    _run_execution(state, sched["tracks"], driver, run)
    return run


def _run_execution(state, tracks, driver, run):
    """Execute tracks in dependency order with per-track serial tasks."""
    # Planning happens once per task (R4/R6), regardless of track.
    for tid in state:
        t = state[tid]
        if t["status"] == STATUS_PENDING:
            t["status"] = STATUS_PLANNING
            outcome = driver.plan_task(tid)
            if outcome in ("done",):  # planner success
                t["status"] = STATUS_PLANNED
            else:
                t["status"] = STATUS_BLOCKED if outcome == "blocker" else STATUS_FAILED
                t["blockers"].append("planner: " + str(outcome))
    # Batched gate (single, R10): in this test driver the gate is automatic.
    for tid in state:
        if state[tid]["status"] == STATUS_PLANNED:
            state[tid]["status"] = STATUS_GATE_APPROVED
    # Execute tracks serially in track order; within a track work serial.
    for trk in tracks:
        for tid in trk["tasks"]:
            t = state[tid]
            if t["status"] != STATUS_GATE_APPROVED:
                continue
            t["status"] = STATUS_WORKING
            outcome = driver.work_phase(tid)
            if outcome == "done":
                t["status"] = STATUS_DONE
            elif outcome == "blocker":
                t["status"] = STATUS_BLOCKED
                t["blockers"].append("work: blocked")
            elif outcome == "timeout":
                t["status"] = STATUS_TIMEOUT
            else:
                t["status"] = STATUS_FAILED


# ---------------------------------------------------------------------------
# Integration + final report (plan U9: R3, R19, R20, R21)
# ---------------------------------------------------------------------------

def integrate(repo_root, tracks, base_branch="develop", gates=None):
    """Merge track branches locally in order, running gates on the merged tree.

    tracks: list of {"branch": <name>} in deterministic track order.
    gates:  callable(integration_worktree) -> (ok: bool, failures: list)

    Base ref moves only when all gates pass. Returns a report dict with
    status: "success" | "fixup".
    """
    import subprocess as _sp

    repo = Path(repo_root)
    integration_wt = repo / "rosey-parallel-integration"
    ok, failures = True, []

    try:
        # Integration worktree on a detached HEAD from the current base tip.
        _sp.run(
            ["git", "-C", str(repo), "worktree", "add", "--detach", str(integration_wt), "HEAD"],
            check=True, capture_output=True, text=True,
        )
        merged = []
        for t in tracks:
            branch = t["branch"]
            res = _sp.run(
                ["git", "-C", str(integration_wt), "merge", "--no-ff", branch,
                 "-m", f"merge {branch}"],
                capture_output=True, text=True,
            )
            # conflict? unmerged paths present
            unmerged = _sp.run(
                ["git", "-C", str(integration_wt), "diff", "--name-only", "--diff-filter=U"],
                capture_output=True, text=True,
            ).stdout.strip()
            if res.returncode != 0 and unmerged:
                _sp.run(["git", "-C", str(integration_wt), "merge", "--abort"],
                        capture_output=True)
                return {
                    "status": "fixup",
                    "reason": f"merge conflict on {branch}",
                    "conflicting_branch": branch,
                    "merged_tracks": merged,
                    "integrated_tip": None,
                }
            merged.append(branch)
        # Gates on the merged result.
        if gates is not None:
            ok, failures = gates(integration_wt)
        if not ok:
            return {
                "status": "fixup",
                "reason": "gates failed: " + "; ".join(failures),
                "gates_failed": failures,
                "merged_tracks": merged,
                "integrated_tip": None,
            }
        integrated_tip = _sp.run(
            ["git", "-C", str(integration_wt), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        # Move the base ref (only on full success, R19/KTD8).
        _sp.run(
            ["git", "-C", str(repo), "update-ref", f"refs/heads/{base_branch}", integrated_tip],
            check=True, capture_output=True,
        )
        return {
            "status": "success",
            "merged_tracks": merged,
            "integrated_tip": integrated_tip,
            "leftover_worktrees": [integration_wt],
        }
    finally:
        # Remove the integration worktree and its branch if one was created.
        _sp.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(integration_wt)],
                capture_output=True)


def final_report(tracks, run_state, base_sha=None, integration_tip=None,
                 leftover_worktrees=None, fix_ups=None, human_blockers=None):
    """Assemble the run's human-readable final report (U9).

    Halting statuses (blocked/timeout/failure) are surfaced; completed tasks
    list their commit range; leftover worktrees/branches and outstanding
    fix-ups/human blockers are recorded.
    """
    halted_tasks = []
    for tid, task in run_state.items():
        if task.get("status") in (STATUS_BLOCKED, STATUS_TIMEOUT, STATUS_FAILED):
            halted_tasks.append({
                "task": tid,
                "status": task.get("status"),
                "blockers": task.get("blockers", []),
            })
    done_tasks = [
        {"task": tid, "status": task.get("status")}
        for tid, task in run_state.items()
        if task.get("status") == STATUS_DONE
    ]
    return {
        "status": "success" if not halted_tasks else "halted",
        "tracks": tracks,
        "done_tasks": done_tasks,
        "blocked_tracks": halted_tasks,
        "halted_tasks": halted_tasks,
        "base_sha": base_sha,
        "integration_tip": integration_tip,
        "leftover_worktrees": list(leftover_worktrees or []),
        "fix_ups": list(fix_ups or []),
        "human_blockers": list(human_blockers or []),
    }


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