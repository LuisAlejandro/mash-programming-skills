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
STATUS_SKIPPED = "skipped"

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
        STATUS_SKIPPED,
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
    STATUS_BLOCKED_BY: {STATUS_SKIPPED},
    STATUS_SKIPPED: set(),
}

TERMINAL_STATUSES = frozenset(
    {STATUS_BLOCKED, STATUS_FAILED, STATUS_TIMEOUT, STATUS_BLOCKED_BY, STATUS_SKIPPED}
)


class StateError(Exception):
    """Raised for state-schema and transition violations."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_run_id() -> str:
    """Run id: timestamp-based, unique per invocation second + counter."""
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def runs_root(repo_root: str | os.PathLike) -> Path:
    return Path(repo_root) / "rosey" / "parallel"


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
# State integrity (hardening U1: R1, R2) — stale-lock liveness + exactly-once claim
# ---------------------------------------------------------------------------

DEFAULT_STALE_WINDOW_S = 300.0  # 5 minutes


def is_pid_alive(pid: int) -> bool:
    """Best-effort liveness probe for a pid (signal 0)."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists, owned by another user
    except OSError:
        return False
    return True


def _iso_age(ts: str | None, now: datetime) -> float:
    """Seconds since an ISO timestamp; inf when unparseable/missing."""
    if not ts:
        return float("inf")
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return float("inf")
    return (now - dt).total_seconds()


def detect_stale_lock(lock: dict, stale_window_s: float = DEFAULT_STALE_WINDOW_S) -> bool:
    """True when a lock should be reaped (R1).

    Reap when the owner pid is dead AND past the stale window, OR when the
    owner has not heartbeated past the stale window (hung-but-alive recovery).
    A live, progressing owner's lock is never stolen.
    """
    now = datetime.now(timezone.utc)
    pid = lock.get("pid")
    if pid is not None and not is_pid_alive(pid):
        return _iso_age(lock.get("acquiredAt"), now) > stale_window_s
    # hung-but-alive: heartbeat older than the stale window
    return _iso_age(lock.get("lastHeartbeat"), now) > stale_window_s


def acquire_lock(
    path: str | os.PathLike,
    owner_tag: str,
    pid: int | None = None,
    stale_window_s: float = DEFAULT_STALE_WINDOW_S,
) -> bool:
    """Atomically acquire a lock file (O_EXCL). Returns True on success.

    A held lock is reaped (and retried) only when detect_stale_lock says so;
    otherwise acquisition fails without stealing a live owner's lock.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    pid = pid or os.getpid()
    lock = {
        "ownerTag": owner_tag,
        "pid": pid,
        "acquiredAt": utc_now_iso(),
        "lastHeartbeat": utc_now_iso(),
    }
    try:
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            existing = json.loads(target.read_text())
        except (OSError, json.JSONDecodeError):
            return False
        if detect_stale_lock(existing, stale_window_s):
            target.unlink(missing_ok=True)
            return acquire_lock(path, owner_tag, pid, stale_window_s)
        return False
    with os.fdopen(fd, "w") as f:
        json.dump(lock, f)
    return True


def release_lock(path: str | os.PathLike) -> None:
    """Release a lock file (idempotent)."""
    Path(path).unlink(missing_ok=True)


def heartbeat_lock(path: str | os.PathLike) -> None:
    """Refresh a lock's lastHeartbeat (hung-but-alive recovery signal)."""
    target = Path(path)
    try:
        lock = json.loads(target.read_text())
    except (OSError, json.JSONDecodeError):
        return
    lock["lastHeartbeat"] = utc_now_iso()
    atomic_write_json(target, lock)


def claim_result(run_dir: str | os.PathLike, task_id: str) -> Path | None:
    """Claim a task's result exactly once (R2).

    Atomic rename of ``<task>.json`` to ``.delivering-<task>.json``, then a
    ``processed/`` ledger commit. A resume completes a mid-claim (a leftover
    ``.delivering-`` slot) instead of re-processing. Returns the processed
    path, or None when the result was already claimed / absent.
    """
    rd = Path(run_dir)
    src = rd / f"{task_id}.json"
    delivering = rd / f".delivering-{task_id}.json"
    processed_dir = rd / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    final = processed_dir / f"{task_id}.json"
    # Resume: complete a mid-claim left by a crash.
    if delivering.exists():
        os.rename(delivering, final)
        return final
    if final.exists():
        return None  # already processed
    if not src.exists():
        return None
    os.rename(src, delivering)
    os.rename(delivering, final)
    return final


# ---------------------------------------------------------------------------
# Recovery (hardening U3: R5, R6) — fingerprint-keyed resume + skip-cascade
# ---------------------------------------------------------------------------

def task_fingerprint(task: dict, dep_fingerprints: dict | None = None) -> str:
    """Canonicalize a task definition to a sha256 fingerprint (R5).

    Folds each dependency's fingerprint into the task's fingerprint so a
    re-run dependency forces its dependents to re-run. Keys on the task
    definition (id, goal, deps, footprint), never on skill content.
    """
    import hashlib

    canonical = {
        "id": task.get("id"),
        "goal": task.get("goal"),
        "deps": sorted(task.get("deps") or []),
        "footprint": sorted(task.get("footprint") or []),
    }
    if dep_fingerprints:
        canonical["depFingerprints"] = {
            d: dep_fingerprints.get(d) for d in sorted(task.get("deps") or [])
        }
    blob = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def diff_fingerprints(old: dict, new: dict) -> dict:
    """Classify tasks as unchanged / changed / added / removed (R5).

    old/new: {task_id: fingerprint}. Returns a dict of task_id -> category.
    """
    result: dict[str, str] = {}
    for tid in new:
        if tid in old:
            result[tid] = "unchanged" if old[tid] == new[tid] else "changed"
        else:
            result[tid] = "added"
    for tid in old:
        if tid not in new:
            result[tid] = "removed"
    return result


def apply_skip_cascade(state: dict, failed_ids: set[str]) -> None:
    """Cascade a failed task's dependents to a terminal `skipped` state (R6).

    Runs only at frontier quiescence (nothing attached / no sibling progress),
    so a revived sibling can still complete a dependent before the cascade.
    """
    # Transitive dependents of any failed task, PLUS dependents of tasks
    # already terminal-skipped/blocked (which a prior run cascaded). This
    # closes the resume gap: a dependent added in a later run must also
    # cascade instead of hanging on a skipped dependency.
    sources = set(failed_ids) | {
        tid for tid, t in state.items()
        if t["status"] in (STATUS_SKIPPED, STATUS_BLOCKED_BY)
    }
    dependents: set[str] = set()
    changed = True
    while changed:
        changed = False
        for tid, t in state.items():
            if tid in dependents:
                continue
            if any(d in sources or d in dependents for d in t["deps"]):
                dependents.add(tid)
                changed = True
    for tid in dependents:
        t = state[tid]
        if t["status"] == STATUS_GATE_APPROVED:
            t["status"] = STATUS_BLOCKED_BY
        if t["status"] == STATUS_BLOCKED_BY:
            t["status"] = STATUS_SKIPPED


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
    # Footprint-intersection edges only (hardening U2: track membership is
    # footprint-overlap only; dependency edges are handled by the frontier
    # admission loop, not the Union-Find track computation).
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            fa = set(footprints.get(a, set()))
            fb = set(footprints.get(b, set()))
            if fa & fb:
                uf.union(a, b)

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
EVIDENCE_START = "ROSEY_EVIDENCE"
EVIDENCE_END = "END_ROSEY_EVIDENCE"


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


def has_evidence(output: str) -> bool:
    """True when the worker emitted an evidence artifact (hardening U4: R7).

    A task is `done` only when it produces an evidence artifact (captured
    output, test run) in addition to the handoff envelope. No evidence
    artifact = not done.
    """
    start = output.find(EVIDENCE_START)
    end = output.find(EVIDENCE_END)
    if start == -1 or end == -1 or end <= start:
        return False
    body = output[start + len(EVIDENCE_START):end].strip()
    return bool(body)


# Known harness error strings -> {errorType, fixHint} (hardening U4: R8).
RETRY_PATTERNS = [
    {
        "pattern": "permission denied",
        "errorType": "permission",
        "fixHint": "grant the missing tool/file permission and retry",
    },
    {
        "pattern": "no harness available",
        "errorType": "harness_unavailable",
        "fixHint": "install or start the harness binary, then retry",
    },
    {
        "pattern": "timeout",
        "errorType": "timeout",
        "fixHint": "split the task or raise the timeout, then retry",
    },
    {
        "pattern": "merge conflict",
        "errorType": "merge_conflict",
        "fixHint": "resolve the conflicting files, then retry",
    },
]


def retry_guidance(output: str) -> dict:
    """Map a harness error string to a corrective fix hint (hardening U4: R8).

    Returns {"errorType": ..., "fixHint": ...} for a known pattern, or a
    generic retry hint when nothing matches.
    """
    lowered = output.lower()
    for entry in RETRY_PATTERNS:
        if entry["pattern"] in lowered:
            return {"errorType": entry["errorType"], "fixHint": entry["fixHint"]}
    return {"errorType": "unknown", "fixHint": "generic retry"}


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
    run_id = resume["run_id"] if resume else new_run_id()
    # Build state from the CURRENT task definitions, carrying over statuses
    # from a resume (hardening U3: R5). This keeps fingerprints keyed to the
    # live definitions, not a stale snapshot.
    state: dict[str, dict] = {}
    for tid, t in tasks.items():
        nt = dict(t)
        if resume and tid in resume["state"]:
            nt["status"] = resume["state"][tid]["status"]
            nt["blockers"] = list(resume["state"][tid].get("blockers", []))
        state[tid] = nt
    # Build the run-level record.
    run = {
        "run_id": run_id,
        "state": state,
        "tracks": [],
        "warnings": [],
        "base_branch": base_branch,
        "base_sha": base_sha or resume.get("base_sha") if resume else (base_sha or "0000"),
    }
    # Fingerprint-keyed resume (hardening U3: R5). Compute fingerprints with
    # dependency folding; reuse unchanged completed tasks, re-run changed/added.
    for tid, t in state.items():
        t["footprint"] = sorted(footprints.get(tid, set()))
    fingerprints = _compute_fingerprints(state)
    if resume:
        old_fp = resume.get("fingerprints", {})
        diff = diff_fingerprints(old_fp, fingerprints)
        for tid, cat in diff.items():
            if cat == "unchanged" and state[tid]["status"] == STATUS_DONE:
                continue  # reuse completed work
            if cat in ("changed", "added"):
                # re-run: reset to pending so planning/work re-fire. A changed
                # task reset unconditionally (even if left mid WORKING/QA/LINT,
                # where it would otherwise strand and never re-fire). An `added`
                # task is fresh — only rewind if a snapshot left it terminal.
                if cat == "changed":
                    state[tid]["status"] = STATUS_PENDING
                elif state[tid]["status"] in (STATUS_DONE, STATUS_BLOCKED_BY, STATUS_SKIPPED):
                    state[tid]["status"] = STATUS_PENDING
    # Guard removed-task deps (hardening R6): if a task's dep no longer exists
    # in the live task set (removed between runs) it can never resolve — mark
    # it skipped so it doesn't hang in gate_approved forever.
    live_ids = set(state)
    for tid, t in state.items():
        missing = [d for d in t["deps"] if d not in live_ids]
        # Cascade only live task instances; never touch already-terminal work
        # or completed (DONE) work.
        if (
            missing
            and t["status"] not in TERMINAL_STATUSES
            and t["status"] != STATUS_DONE
        ):
            t["status"] = STATUS_SKIPPED
            t.setdefault("blockers", []).append(
                "dependency removed between runs: " + ",".join(missing)
            )

    run["fingerprints"] = fingerprints
    # Sequencing is deterministic; tracks computed from footprints+deps.
    sched = schedule(state, footprints)
    run["tracks"] = sched["tracks"]
    run["warnings"].extend(sched["warnings"])

    _run_execution(state, sched["tracks"], driver, run, max_parallel=max_parallel)
    run["waves"] = run.pop("_waves", [])
    return run


def _compute_fingerprints(state: dict) -> dict:
    """Compute per-task fingerprints with dependency folding (R5)."""
    fps: dict[str, str] = {}
    # Iterate until stable (deps may be ordered arbitrarily).
    for _ in range(len(state) + 1):
        changed = False
        for tid, t in state.items():
            new = task_fingerprint(t, fps)
            if fps.get(tid) != new:
                fps[tid] = new
                changed = True
        if not changed:
            break
    return fps


def _run_execution(state, tracks, driver, run, max_parallel=4):
    """Execute tasks via dependency-frontier admission (hardening U2: R3, R4).

    A task is admitted the moment every dependency is terminal-`done` and a
    resident slot is free. File-overlap tasks remain serialized on a track
    (one task per track per pass). Oversubscribed tasks park in a FIFO denied
    queue and are offered a freed slot oldest-first. Waves are informational,
    never barriers.
    """
    # Planning happens once per task (R4/R6), regardless of track.
    for tid in state:
        t = state[tid]
        if t["status"] == STATUS_PENDING:
            t["status"] = STATUS_PLANNING
            outcome = driver.plan_task(tid)
            if outcome in ("done",):  # planner success
                # Capture the plan the planner produced so work/qa/lint honor it.
                # Driver may expose optional plan_path(tid); fall back to the
                # footprint-derived plan path only if the driver has one recorded.
                plan_path = None
                pp_fn = getattr(driver, "plan_path", None)
                if callable(pp_fn):
                    plan_path = pp_fn(tid)
                if plan_path:
                    t["plan_path"] = plan_path
                    set_pp = getattr(driver, "set_plan_path", None)
                    if callable(set_pp):
                        set_pp(tid, plan_path)
                t["status"] = STATUS_PLANNED
            else:
                t["status"] = STATUS_BLOCKED if outcome == "blocker" else STATUS_FAILED
                t["blockers"].append("planner: " + str(outcome))
    # Batched gate (single, R10): in this test driver the gate is automatic.
    for tid in state:
        if state[tid]["status"] == STATUS_PLANNED:
            state[tid]["status"] = STATUS_GATE_APPROVED

    # Track membership: task -> track_id (footprint-overlap tracks).
    track_of: dict[str, int] = {}
    for trk in tracks:
        for tid in trk["tasks"]:
            track_of[tid] = trk["track_id"]

    done: set[str] = {tid for tid, t in state.items() if t["status"] == STATUS_DONE}
    denied: list[str] = []  # FIFO of admissible-but-denied (no slot this pass)
    waves: list[list[str]] = []  # informational wave groupings (never barriers)
    run["_waves"] = waves

    def deps_done(tid: str) -> bool:
        return all(d in done for d in state[tid]["deps"])

    while True:
        # Admissible = gate-approved and all deps terminal-done.
        admissible = [
            tid for tid in state
            if state[tid]["status"] == STATUS_GATE_APPROVED and deps_done(tid)
        ]
        # FIFO: oldest denied first, then fresh admissible.
        queue = denied + [tid for tid in admissible if tid not in denied]
        denied = []
        admitted: list[str] = []
        admitted_tracks: set[int] = set()
        slots = max_parallel
        for tid in queue:
            if slots <= 0:
                denied.append(tid)  # oversubscription: park for a freed slot
                continue
            trk = track_of[tid]
            if trk in admitted_tracks:
                denied.append(tid)  # track busy this pass -> park
                continue
            admitted.append(tid)
            admitted_tracks.add(trk)
            slots -= 1
        if not admitted:
            # Frontier quiescence: nothing runnable. Cascade dependents of
            # failed tasks to `skipped` (hardening U3: R6) so they don't hang
            # in `blocked_by` forever.
            failed_ids = {
                tid for tid, t in state.items()
                if t["status"] in (STATUS_FAILED, STATUS_TIMEOUT, STATUS_BLOCKED)
            }
            apply_skip_cascade(state, failed_ids)
            break  # nothing runnable; remaining tasks are dep-blocked
        waves.append(list(admitted))
        # Evidence gate (hardening U4: R7) + retry guidance (R8). The driver
        # may expose raw worker output via an optional `evidence(tid)` method;
        # when present, `done` requires an evidence artifact and a `failure`
        # carries a corrective fix hint. FakeDrivers without evidence() skip
        # the gate, keeping the orchestrator loop contract intact.
        def _worker_output(tid: str) -> str | None:
            fn = getattr(driver, "evidence", None)
            return fn(tid) if callable(fn) else None

        for tid in admitted:
            t = state[tid]
            # Full per-task loop: work -> qa -> lint -> done (hardening:
            # QA and lint previously never executed — only work_phase was
            # dispatched and tasks jumped straight to done). Each phase runs
            # inline while the task holds its track slot; a failure at any
            # phase halts the task (and via the frontier, cascades its
            # dependents) the same way a work failure did.
            t["status"] = STATUS_WORKING
            outcome = driver.work_phase(tid)
            raw = _worker_output(tid)
            if outcome == "done":
                if raw is not None and not has_evidence(raw):
                    # worker claims done but produced no evidence artifact
                    t["status"] = STATUS_FAILED
                    t["blockers"].append(
                        "work: done without evidence artifact"
                    )
                else:
                    # work passed its evidence gate -> QA
                    t["status"] = STATUS_QA
                    outcome = driver.qa_phase(tid)
                    if outcome != "done":
                        t["status"] = STATUS_FAILED
                        t["blockers"].append(
                            f"qa: {outcome} (expected terminal 'Review complete')"
                        )
                    else:
                        # QA passed -> lint
                        t["status"] = STATUS_LINT
                        outcome = driver.lint_phase(tid)
                        if outcome != "done":
                            t["status"] = STATUS_FAILED
                            t["blockers"].append(f"lint: {outcome} (expected LINT_STATUS: pass)")
                        else:
                            t["status"] = STATUS_DONE
                            done.add(tid)
            elif outcome == "blocker":
                t["status"] = STATUS_BLOCKED
                t["blockers"].append("work: blocked")
            elif outcome == "timeout":
                t["status"] = STATUS_TIMEOUT
            else:
                t["status"] = STATUS_FAILED
                if raw:
                    g = retry_guidance(raw)
                    t["blockers"].append(
                        f"work failed ({g['errorType']}): {g['fixHint']}"
                    )
                else:
                    t["blockers"].append("work: failed")


# ---------------------------------------------------------------------------
# Flow shape (hardening U5: R9, R10) — scaffold phase + parallel verification
# ---------------------------------------------------------------------------

def run_scaffold(driver, tasks: dict) -> dict:
    """Contracts-before-code scaffold phase (hardening U5: R10).

    One architect worker defines shared contracts (interfaces, types, schemas,
    stubs) before executors fan out. Returns a scaffold record with the
    contract doc path and any blockers.
    """
    outcome = driver.scaffold_phase()
    return {
        "phase": "scaffold",
        "outcome": outcome,
        "contract_doc": "rosey/parallel/scaffold-contract.md" if outcome == "done" else None,
        "blockers": [] if outcome == "done" else [f"scaffold: {outcome}"],
    }


def run_parallel_verification(driver, integrated_tip: str | None) -> dict:
    """Parallel verification after integration (hardening U5: R9).

    Fans out 3 verifiers concurrently (code review + test runner +
    architecture/contract check) on the integrated result. Returns a record
    of per-verifier outcomes and any rejections.
    """
    import concurrent.futures as _cf

    verifiers = ["code_review", "test_runner", "architecture"]

    def _run(v: str) -> tuple[str, str]:
        return v, driver.verify_phase(v, integrated_tip)

    results: dict[str, str] = {}
    with _cf.ThreadPoolExecutor(max_workers=len(verifiers)) as ex:
        for v, outcome in ex.map(_run, verifiers):
            results[v] = outcome
    rejected = [v for v, r in results.items() if r != "pass"]
    return {
        "phase": "parallel_verification",
        "verifiers": results,
        "rejected": rejected,
        "passed": not rejected,
    }


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
# Real harness phase-driver (plan U6/R26) + CLI
# ---------------------------------------------------------------------------

class HarnessPhaseDriver:
    """Real driver that shells out to a delegated harness worker.

    Implements the same contract as the test FakeDrivers (plan_task,
    work_phase, scaffold_phase, verify_phase, evidence) so orchestrate_run
    and the flow phases run against a live harness. Each phase invokes the
    harness binary with the worker prompt and interprets the captured output.
    """

    def __init__(self, name: str, repo_root: str | os.PathLike,
                 run_id: str, prompt_builder=None) -> None:
        self.harness = HarnessDriver.from_name(name)
        self.repo_root = Path(repo_root)
        self.run_id = run_id
        self._prompt_builder = prompt_builder or self._default_prompt
        self._outputs: dict[str, str] = {}
        self._plan_paths: dict[str, str] = {}

    def set_plan_path(self, task_id: str, path: str) -> None:
        """Record the plan file a task's planner produced (honored by work/qa/lint)."""
        self._plan_paths[task_id] = path

    def plan_path(self, task_id: str) -> str | None:
        """Return the plan file a task's planner wrote.

        Prefers an explicitly set path (via set_plan_path); otherwise derives
        it from a `PLAN PATH: <path>` line in the planner's captured output,
        matching the worker-prompt contract that plan emits its path.
        """
        if task_id in self._plan_paths:
            return self._plan_paths[task_id]
        raw = self._outputs.get(task_id) or ""
        for line in raw.splitlines():
            line = line.strip()
            if line.lower().startswith("plan path:"):
                value = line.split(":", 1)[1].strip()
                if value:
                    return value
        return None

    def _default_prompt(self, task_id: str, phase: str) -> str:
        plan = self._plan_paths.get(task_id)
        lines = [
            f"You are a rosey worker running task {task_id!r} phase {phase!r} "
            f"of run {self.run_id!r}. Follow the worker prompt contract.",
        ]
        if plan:
            lines.append(f"PLAN PATH: {plan}")
        return "\n".join(lines)

    def _invoke(self, task_id: str, phase: str) -> str:
        """Run the harness, return the interpreted outcome string."""
        import subprocess as _sp

        prompt = self._prompt_builder(task_id, phase)
        cmd = self.harness.launch_cmd(self.harness.name) + [prompt]
        res = _sp.run(
            cmd, capture_output=True, text=True, cwd=self.repo_root,
        )
        output = (res.stdout or "") + (res.stderr or "")
        self._outputs[task_id] = output
        return self.harness.interpret(res.returncode, output)

    def plan_task(self, task_id: str) -> str:
        return self._invoke(task_id, "plan")

    def work_phase(self, task_id: str) -> str:
        return self._invoke(task_id, "work")

    def qa_phase(self, task_id: str) -> str:
        return self._invoke(task_id, "qa")

    def lint_phase(self, task_id: str) -> str:
        return self._invoke(task_id, "lint")

    def evidence(self, task_id: str) -> str | None:
        return self._outputs.get(task_id)

    def scaffold_phase(self) -> str:
        return self._invoke("__scaffold__", "scaffold")

    def verify_phase(self, verifier: str, tip: str | None) -> str:
        return self._invoke(f"__verify__/{verifier}", "verify")


def _load_run_inputs(path: str) -> tuple[list[dict], dict]:
    """Load and validate a run-inputs JSON file -> (tasks, options)."""
    data = json.loads(Path(path).read_text())
    tasks = data.get("tasks", [])
    options = data.get("options", {})
    return validate_inputs(tasks, options), options


def _cmd_run(argv: list[str]) -> int:
    """run <inputs.json> [--resume <run-id>] [--max-parallel N]"""
    if not argv:
        print("usage: rosey_parallel.py run <inputs.json> [--resume <run-id>]",
              file=sys.stderr)
        return 2
    inputs_path = argv[0]
    resume_id = None
    max_parallel = 4
    i = 1
    while i < len(argv):
        if argv[i] == "--resume" and i + 1 < len(argv):
            resume_id = argv[i + 1]
            i += 2
        elif argv[i] == "--max-parallel" and i + 1 < len(argv):
            max_parallel = int(argv[i + 1])
            i += 2
        else:
            i += 1
    tasks, options = _load_run_inputs(inputs_path)
    repo_root = Path.cwd()
    footprints = {
        t["id"]: set(t.get("footprint") or []) for t in tasks
    }
    harness = options.get("harness")
    if not harness:
        harness = select_harness(
            None, lambda n: HarnessDriver.from_name(n).probe()
        )
    run_id = resume_id or new_run_id()
    driver = HarnessPhaseDriver(harness, repo_root, run_id)
    resume = load_run(repo_root, run_id) if resume_id else None
    run = orchestrate_run(
        repo_root, {t["id"]: t for t in tasks}, footprints, driver,
        base_branch=options.get("base_branch", "develop"),
        base_sha=options.get("base_sha"),
        resume=resume, max_parallel=max_parallel,
    )
    save_run(repo_root, run)
    print(json.dumps(run, indent=2, sort_keys=False))
    return 0


def _cmd_scaffold(argv: list[str]) -> int:
    """scaffold <inputs.json>"""
    if not argv:
        print("usage: rosey_parallel.py scaffold <inputs.json>", file=sys.stderr)
        return 2
    tasks, options = _load_run_inputs(argv[0])
    harness = options.get("harness") or "pi"
    driver = HarnessPhaseDriver(harness, Path.cwd(), new_run_id())
    result = run_scaffold(driver, {t["id"]: t for t in tasks})
    print(json.dumps(result, indent=2, sort_keys=False))
    return 0


def _cmd_verify(argv: list[str]) -> int:
    """verify <integrated-tip>"""
    if not argv:
        print("usage: rosey_parallel.py verify <integrated-tip>", file=sys.stderr)
        return 2
    driver = HarnessPhaseDriver("pi", Path.cwd(), new_run_id())
    result = run_parallel_verification(driver, argv[0])
    print(json.dumps(result, indent=2, sort_keys=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(
            "usage: rosey_parallel.py <run|scaffold|verify|--self-check> ...",
            file=sys.stderr,
        )
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "--self-check":
        _self_check()
        return 0
    if cmd == "run":
        return _cmd_run(rest)
    if cmd == "scaffold":
        return _cmd_scaffold(rest)
    if cmd == "verify":
        return _cmd_verify(rest)
    print(f"unknown subcommand {cmd!r}", file=sys.stderr)
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