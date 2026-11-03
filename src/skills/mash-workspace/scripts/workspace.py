#!/usr/bin/env python3
"""Workspace coordination for concurrent Mash Programming Skills workflows.

Every mutating workflow registers a run, then holds leases on what it writes:
the workspace it edits, the base ref it publishes, and the runtime resources it
uses. Contention never degrades to sharing — it returns a blocker naming the
holder, so the losing workflow stops loudly instead of corrupting the winner.

Subcommands (stdlib only, JSON on stdout):

  run start --workflow <name> [--workspace <dir>] [--branch <b>] [--base <sha>]
      Register a run and print its record. The run id is collision-resistant and
      registered atomically, so two runs starting in the same second never share
      state.

  run show --run <id>
  run heartbeat --run <id>
      Prove liveness. A lease is reclaimable only after its owner's process is
      gone AND its heartbeat has aged past the stale window.

  run end --run <id> [--status finished|failed]
      Release every lease this run owns, and nothing else.

  lease acquire --run <id> --kind <kind> --key <key>
  lease release --run <id> --kind <kind> --key <key>
  lease show --kind <kind> --key <key>
      Exclusive claims. `kind` is the resource class (run, workspace, port,
      compose, db, browser, release); `key` identifies the instance.

Every command takes `--repo <dir>`: any directory inside the target repository.
State lives under the primary checkout's gitignored `.mash/`.

Exit codes: 0 success, 2 refusal or contention, 1 unexpected failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# A lease whose owner process is gone is reclaimed only after this much silence.
# Matches the window mash-parallel already uses for its track locks.
DEFAULT_STALE_WINDOW_S = 300.0

LEASE_KINDS = (
    "run",
    "workspace",  # a checkout or worktree being written
    "port",       # a listening port
    "compose",    # a container project
    "db",         # a database or destructive dataset
    "browser",    # a browser profile or session
    "release",    # a release/tag operation
)

RUN_STATUSES = ("active", "finished", "failed")
_SAFE_KEY = re.compile(r"[^A-Za-z0-9._-]+")

# A run id and a publication stem both become a path component. Anything that
# can introduce a separator, a parent reference, or an empty component turns
# a name into a traversal, so both are validated at the choke point rather
# than at each call site.
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


def validate_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not RUN_ID_RE.match(run_id):
        raise WorkspaceError(
            f"invalid run id {run_id!r}: use letters, digits, dot, dash and underscore, "
            "starting with a letter or digit (no separators)"
        )
    return run_id


def _validate_component(value: str, what: str) -> str:
    """Refuse anything that is not a single, self-contained filename component."""
    if not isinstance(value, str) or not value:
        raise WorkspaceError(f"invalid {what} {value!r}: must not be empty")
    if value in (".", "..") or "/" in value or "\\" in value or "\0" in value:
        raise WorkspaceError(
            f"invalid {what} {value!r}: must be one filename component "
            "(no separators, no '..')"
        )
    return value


class WorkspaceError(RuntimeError):
    """A refusal. The message is the blocker text shown to the caller."""


class Blocked(WorkspaceError):
    """Contention: another live owner holds what this run asked for."""

    def __init__(self, message: str, payload: dict) -> None:
        super().__init__(message)
        self.payload = payload


# --- primitives ------------------------------------------------------------


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def hostname() -> str:
    return socket.gethostname()


def new_run_id() -> str:
    """Timestamp for readability plus entropy for uniqueness.

    The timestamp alone has one-second resolution, which is not enough: two
    workflows started in the same second would resolve the same state paths.
    """
    return f"{utc_now_compact()}-{secrets.token_hex(4)}"


def is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists, owned by another user
    except OSError:
        return False
    return True


def _age_seconds(stamp: str | None, now: datetime | None = None) -> float:
    if not stamp:
        return float("inf")
    try:
        moment = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return float("inf")
    return ((now or datetime.now(timezone.utc)) - moment).total_seconds()


def primary_checkout(path: str | Path) -> Path:
    """The checkout that owns `path`'s git common dir.

    Coordination state belongs to the repository, not to whichever linked
    worktree happens to be running, so every participant resolves the same root.
    Falls back to `path` outside a git repository.
    """
    res = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--git-common-dir"],
        capture_output=True, text=True, check=False,
    )
    if res.returncode != 0 or not res.stdout.strip():
        return Path(path).resolve()
    common = Path(res.stdout.strip())
    if not common.is_absolute():
        common = Path(path) / common
    common = common.resolve()
    return common.parent if common.name == ".git" else Path(path).resolve()


def state_root(repo: str | Path) -> Path:
    return primary_checkout(repo) / ".mash"


def runs_root(repo: str | Path) -> Path:
    return state_root(repo) / "runs"


def run_dir(repo: str | Path, run_id: str) -> Path:
    return runs_root(repo) / validate_run_id(run_id)


def run_record_path(repo: str | Path, run_id: str) -> Path:
    return run_dir(repo, run_id) / "run.json"


def lease_path(repo: str | Path, kind: str, key: str) -> Path:
    """One file per claim.

    The readable part is for humans reading `.mash/locks/`; the digest keeps
    two different keys that sanitize alike from colliding on one file.
    """
    if kind not in LEASE_KINDS:
        raise WorkspaceError(f"unknown lease kind {kind!r}")
    digest = hashlib.sha256(key.encode()).hexdigest()[:12]
    readable = _SAFE_KEY.sub("-", key).strip("-")[:48] or "key"
    return state_root(repo) / "locks" / kind / f"{readable}-{digest}.lock"


def write_json_atomic(path: Path, data: dict) -> None:
    """Publish JSON atomically through a uniquely named temporary.

    The temp name carries pid and entropy so two writers never share it.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n")
    os.replace(tmp, path)


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


# --- runs ------------------------------------------------------------------


def register_run(
    repo: str | Path,
    workflow: str,
    run_id: str | None = None,
    workspace: str | Path | None = None,
    branch: str | None = None,
    base: str | None = None,
    agent: str | None = None,
) -> dict:
    """Register a run, failing rather than overwriting an existing one."""
    if not workflow:
        raise WorkspaceError("workflow is required")
    explicit = run_id is not None
    for _ in range(5):
        candidate = run_id if explicit else new_run_id()
        try:
            run_dir(repo, candidate).mkdir(parents=True)
        except FileExistsError:
            if explicit:
                raise WorkspaceError(f"run {candidate} is already registered") from None
            continue
        record = {
            "schema": 1,
            "run_id": candidate,
            "workflow": workflow,
            "repo": str(primary_checkout(repo)),
            "workspace": str(Path(workspace).resolve()) if workspace else None,
            "branch": branch,
            "base": base,
            "owner": {
                "pid": os.getpid(),
                "host": hostname(),
                "agent": agent or os.environ.get("MASH_AGENT") or "unknown",
            },
            "status": "active",
            "started_at": utc_now_iso(),
            "heartbeat": utc_now_iso(),
            "leases": [],
            "receipts": [],
        }
        write_json_atomic(run_record_path(repo, candidate), record)
        return record
    raise WorkspaceError("could not allocate a unique run id")


def load_run(repo: str | Path, run_id: str) -> dict:
    record = read_json(run_record_path(repo, run_id))
    if record is None:
        raise WorkspaceError(f"unknown run {run_id!r}; start one with `run start`")
    return record


def save_run(repo: str | Path, record: dict) -> None:
    write_json_atomic(run_record_path(repo, record["run_id"]), record)


def heartbeat(repo: str | Path, run_id: str, now: str | None = None) -> dict:
    """Refresh the run and every lease it owns, so liveness is observable."""
    stamp = now or utc_now_iso()
    record = load_run(repo, run_id)
    record["heartbeat"] = stamp
    for token in record.get("leases", []):
        kind, _, key = token.partition(":")
        lease = read_lease(repo, kind, key)
        if lease and lease.get("run_id") == run_id:
            lease["heartbeat"] = stamp
            write_json_atomic(lease_path(repo, kind, key), lease)
    save_run(repo, record)
    return record


def end_run(repo: str | Path, run_id: str, status: str = "finished") -> dict:
    """Release every lease this run owns, and nothing else."""
    if status not in RUN_STATUSES:
        raise WorkspaceError(f"unknown run status {status!r}")
    record = load_run(repo, run_id)
    released, kept = [], []
    for token in list(record.get("leases", [])):
        kind, _, key = token.partition(":")
        try:
            outcome = release_lease(repo, run_id, kind, key, _update_run=False)
        except Blocked:
            # A lease this run no longer owns must not abort the cleanup: the
            # remaining leases would leak until someone noticed.
            kept.append(token)
            continue
        (released if outcome["status"] in ("released", "absent") else kept).append(token)
    record["leases"] = kept
    record["status"] = status
    record["ended_at"] = utc_now_iso()
    save_run(repo, record)
    return {"status": "ended", "run_id": run_id, "released": released, "kept": kept}


# --- leases ----------------------------------------------------------------


def read_lease(repo: str | Path, kind: str, key: str) -> dict | None:
    return read_json(lease_path(repo, kind, key))


def _holder_view(lease: dict) -> dict:
    return {
        "run_id": lease.get("run_id"),
        "pid": lease.get("pid"),
        "host": lease.get("host"),
        "agent": lease.get("agent"),
        "acquired_at": lease.get("acquired_at"),
        "heartbeat": lease.get("heartbeat"),
        "age_seconds": round(_age_seconds(lease.get("heartbeat")), 1),
    }


def is_reclaimable(lease: dict, stale_window_s: float = DEFAULT_STALE_WINDOW_S) -> tuple[bool, str]:
    """Whether a lease can be reclaimed without an explicit `--force`.

    Liveness is only checkable on the machine that holds it, so a lease written
    by another host is never reclaimed here.

    The recorded owner is the invoking process, not necessarily the long-lived
    workflow, so a "dead pid" is evidence rather than proof: that is why a
    reclaim is always an explicit, logged action and never a silent steal.
    """
    if lease.get("host") != hostname():
        return False, f"held on another host ({lease.get('host')!r}); cannot verify liveness"
    pid = lease.get("owner_pid", lease.get("pid"))
    if isinstance(pid, int) and is_pid_alive(pid):
        return False, f"owner pid {pid} is still alive"
    age = _age_seconds(lease.get("heartbeat"))
    if age <= stale_window_s:
        return False, f"owner is gone but heartbeat is only {age:.0f}s old"
    return True, f"owner pid {pid} is gone and silent for {age:.0f}s"


def reclaim_lease(
    repo: str | Path,
    run_id: str,
    kind: str,
    key: str,
    force: bool = False,
    stale_window_s: float = DEFAULT_STALE_WINDOW_S,
) -> dict:
    """Take back a lease whose owner is gone. Explicit, never automatic.

    The lease file is renamed to a private name first. Rename is atomic, so
    exactly one process can win, and the winner re-reads what it grabbed
    before deleting it. Verifying before unlinking is what stops two
    recoverers from both deciding they own the resource.
    """
    path = lease_path(repo, kind, key)
    existing = read_json(path)
    if existing is None:
        return {"status": "absent", "kind": kind, "key": key}
    ok, why = is_reclaimable(existing, stale_window_s)
    if not ok and not force:
        raise Blocked(
            f"{kind}:{key} cannot be reclaimed: {why}",
            {
                "status": "blocked", "kind": kind, "key": key,
                "blocker": f"refusing to reclaim {kind}:{key}: {why}",
                "holder": _holder_view(existing),
                "recovery": [
                    "let the holder finish and retry",
                    (
                        f"if you are certain no owner is running: lease reclaim --force "
                        f"--kind {kind} --key {key!r}"
                    ),
                ],
            },
        )
    grabbed = path.with_name(f"{path.name}.reclaim.{os.getpid()}.{secrets.token_hex(4)}")
    try:
        os.rename(path, grabbed)
    except FileNotFoundError:
        return {"status": "absent", "kind": kind, "key": key}
    try:
        moved = read_json(grabbed)
        if moved is not None and moved.get("run_id") != existing.get("run_id"):
            # Someone else's lease landed in the gap; put it back untouched.
            os.rename(grabbed, path)
            raise Blocked(
                f"{kind}:{key} changed owner while reclaiming",
                {"status": "blocked", "kind": kind, "key": key,
                 "blocker": f"{kind}:{key} is now held by run {moved.get('run_id')}",
                 "holder": _holder_view(moved),
                 "recovery": ["retry; the resource was reassigned"]},
            )
    finally:
        grabbed.unlink(missing_ok=True)
    returned = load_run(repo, run_id)
    token = f"{kind}:{key}"
    if token in returned.get("leases", []):
        returned["leases"].remove(token)
        save_run(repo, returned)
    return {"status": "reclaimed", "kind": kind, "key": key,
            "reclaimed_from": _holder_view(existing), "forced": force}


def acquire_lease(
    repo: str | Path,
    run_id: str,
    kind: str,
    key: str,
    stale_window_s: float = DEFAULT_STALE_WINDOW_S,
    owner_pid: int | None = None,
) -> dict:
    if kind not in LEASE_KINDS:
        raise WorkspaceError(f"unknown lease kind {kind!r}; expected one of {', '.join(LEASE_KINDS)}")
    record = load_run(repo, run_id)
    path = lease_path(repo, kind, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    owner = owner_pid if isinstance(owner_pid, int) else os.getpid()
    lease = {
        "run_id": run_id,
        "kind": kind,
        "key": key,
        "pid": os.getpid(),
        "owner_pid": owner,
        "host": hostname(),
        "agent": record["owner"].get("agent"),
        "acquired_at": utc_now_iso(),
        "heartbeat": utc_now_iso(),
    }
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        existing = read_lease(repo, kind, key)
        if existing is None:
            # Unreadable or half-written: treat as held rather than stealing.
            raise Blocked(
                f"{kind}:{key} is held by an unreadable lease at {path}",
                {"status": "blocked", "kind": kind, "key": key, "holder": None,
                 "blocker": f"{kind}:{key} lease file is unreadable",
                 "recovery": [f"inspect {path}",
                              f"reclaim it if no owner is running: lease reclaim --force --kind {kind} --key {key!r}"]},
            ) from None
        same_owner = (
            existing.get("run_id") == run_id
            and existing.get("host") == hostname()
            and existing.get("pid") == os.getpid()
        )
        if same_owner:
            return {"status": "held", "run_id": run_id, "kind": kind, "key": key,
                    "holder": _holder_view(existing)}
        ok, why = is_reclaimable(existing, stale_window_s)
        # Never reclaim silently. A reclaim moves the resource between owners,
        # so it is an explicit decision with a recorded reason.
        raise Blocked(
            f"{kind}:{key} is held by run {existing.get('run_id')}",
            {
                "status": "blocked",
                "kind": kind, "key": key,
                "blocker": f"{kind}:{key} is held by run {existing.get('run_id')}: {why}",
                "holder": _holder_view(existing),
                "stale": ok,
                "recovery": [
                    "wait for the holder to finish and retry",
                    "use a different workspace or resource",
                    (f"if no owner is running: lease reclaim --run {run_id} "
                     f"--kind {kind} --key {key!r}")
                    if ok else
                    (f"if you are certain no owner is running: lease reclaim --force "
                     f"--run {run_id} --kind {kind} --key {key!r}"),
                ],
            },
        ) from None
    with os.fdopen(fd, "w") as handle:
        json.dump(lease, handle)
    token = f"{kind}:{key}"
    if token not in record.get("leases", []):
        record.setdefault("leases", []).append(token)
        record["heartbeat"] = utc_now_iso()
        save_run(repo, record)
    return {"status": "acquired", "run_id": run_id, "kind": kind, "key": key,
            "reclaimed_from": None}


def release_lease(
    repo: str | Path, run_id: str, kind: str, key: str, _update_run: bool = True,
) -> dict:
    existing = read_lease(repo, kind, key)
    if existing is None:
        outcome = {"status": "absent", "kind": kind, "key": key}
    elif existing.get("run_id") != run_id:
        raise Blocked(
            f"{kind}:{key} belongs to run {existing.get('run_id')}",
            {
                "status": "blocked",
                "kind": kind, "key": key,
                "blocker": f"refusing to release {kind}:{key}: it belongs to run {existing.get('run_id')}",
                "holder": _holder_view(existing),
                "recovery": ["release it from its owning run", "or let it expire after the stale window"],
            },
        )
    else:
        lease_path(repo, kind, key).unlink(missing_ok=True)
        outcome = {"status": "released", "kind": kind, "key": key}
    if _update_run:
        record = load_run(repo, run_id)
        token = f"{kind}:{key}"
        if token in record.get("leases", []):
            record["leases"].remove(token)
            save_run(repo, record)
    return outcome


# --- publication -----------------------------------------------------------

# `YYYY-MM-DD-NNN-rest`: plan names carry a daily sequence, so a collision
# advances the number rather than appending a suffix.
_SEQUENCED_STEM = re.compile(r"^(\d{4}-\d{2}-\d{2}-)(\d{3})(-.*)$")


def stem_candidates(stem: str, limit: int = 200):
    """The requested name first, then the next free names."""
    yield stem
    match = _SEQUENCED_STEM.match(stem)
    for step in range(1, limit):
        if match:
            yield f"{match.group(1)}{int(match.group(2)) + step:03d}{match.group(3)}"
        else:
            yield f"{stem}-{step + 1}"


def _same_bytes(a: Path, b: Path) -> bool:
    try:
        return a.read_bytes() == b.read_bytes()
    except OSError:
        return False


def _link_exclusive(src: Path, dst: Path) -> bool:
    """Publish `src`'s content at `dst`, atomically, without overwriting.

    Content is staged in a uniquely named temporary and then hard-linked into
    place: `os.link` fails when the destination exists, so the reservation and
    the content land in one indivisible step. Reserving an empty placeholder
    first would let a racing writer read it as real content.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(f".{dst.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    try:
        # O_EXCL|O_NOFOLLOW: a pre-planted symlink at the temp name must not be
        # followed, and a half-written temp must never be visible as content.
        fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o644)
        try:
            os.write(fd, src.read_bytes())
        finally:
            os.close(fd)
        try:
            os.link(tmp, dst)
        except FileExistsError:
            return False
        except OSError as exc:
            # No hardlink support, a full disk, or a cross-device destination.
            # That is a refusal to report, never a traceback.
            raise WorkspaceError(
                f"cannot publish {dst}: {exc.strerror or exc}. "
                "This filesystem must support hard links inside one directory."
            ) from exc
        return True
    finally:
        tmp.unlink(missing_ok=True)


def _receipt(src: Path, dst: Path) -> dict:
    """What was published, from where.

    The source path is recorded because cleanup asks "is *this* artifact
    published?". A basename cannot answer that: `.mash/plans/x.md` and
    `.mash/qa/x.md` share one, so a basename match would hide an unpublished
    artifact behind a published namesake.
    """
    return {"source": str(src.resolve()), "dest": str(dst.resolve())}


def published_sources(record: dict) -> set[str]:
    return {r["source"] for r in (record.get("receipts") or []) if isinstance(r, dict)}


def publish_exact(repo: str | Path, run_id: str | None, src: str | Path, dst: str | Path) -> dict:
    """Publish at exactly `dst`, never renaming.

    Identical content is a no-op. Different content is a refusal rather than an
    overwrite: the caller chose this exact path, so moving it would hide the
    collision.
    """
    record = load_run(repo, run_id) if run_id else None
    src, dst = Path(src), Path(dst)
    if not src.is_file():
        raise WorkspaceError(f"{src} is not a readable file")
    if dst.is_symlink():
        raise WorkspaceError(f"{dst} is a symlink; refusing to publish through it")
    if dst.exists():
        if _same_bytes(src, dst):
            return {"status": "unchanged", "path": str(dst)}
        raise WorkspaceError(f"{dst} exists with different content; move it aside first")
    if not _link_exclusive(src, dst):
        if _same_bytes(src, dst):
            return {"status": "unchanged", "path": str(dst)}
        raise WorkspaceError(f"{dst} was created by another run with different content")
    if record is not None:
        record.setdefault("receipts", []).append(_receipt(src, dst))
        save_run(repo, record)
    return {"status": "published", "path": str(dst)}


def publish_group(
    repo: str | Path,
    run_id: str | None,
    entries: list[tuple[Path, str]],
    dest_dir: str | Path,
    stem: str,
) -> dict:
    """Publish one document and its siblings under a single shared stem.

    Two runs publishing the same destination never both land: the loser moves
    to the next free name. A group moves as a unit, so a plan and its sidecars
    stay paired.

    A group is placed by deciding the candidate against every member first and
    only then linking. Nothing is ever unlinked: a rollback cannot distinguish
    a file this call created from one a concurrent publisher already accepted
    as unchanged, so deleting it could remove another run's artifact.
    """
    _validate_component(stem, "stem")
    for _, suffix in entries:
        _validate_component(suffix, "suffix")
    record = load_run(repo, run_id) if run_id else None
    sources = [(Path(src), suffix) for src, suffix in entries]
    for src, _ in sources:
        if not src.is_file():
            raise WorkspaceError(f"{src} is not a readable file")
    if not sources:
        raise WorkspaceError("no files to publish")
    dest = Path(dest_dir).resolve()

    for candidate in stem_candidates(stem):
        # Decide the whole group before touching it, so a collision costs
        # nothing and two runs never half-publish.
        plan: list[tuple[Path, Path, str]] = []
        blocked = False
        for src, suffix in sources:
            target = dest / f"{candidate}{suffix}"
            if target.parent != dest:
                raise WorkspaceError(f"refusing to publish {target}: outside {dest}")
            if target.is_symlink() or (target.exists() and not _same_bytes(src, target)):
                blocked = True
                break
            plan.append((src, target, "unchanged" if target.exists() else "published"))
        if blocked:
            continue

        landed: list[str] = []
        statuses: dict[str, str] = {}
        for src, target, state in plan:
            if state == "unchanged":
                statuses[target.name] = "unchanged"
                continue
            if _link_exclusive(src, target):
                statuses[target.name] = "published"
                landed.append(str(target))
            elif _same_bytes(src, target):
                statuses[target.name] = "unchanged"
            elif not landed:
                # Lost the race before anything of this group landed: try the
                # next name. Nothing to undo, and nothing is lost.
                blocked = True
                break
            else:
                # Something of this group already landed. Keep it and say so;
                # removing it could delete a file another run just accepted.
                if record is not None and landed:
                    record.setdefault("receipts", []).extend(
                        _receipt(s, Path(t)) for s, t, st in plan
                        if st == "published" and str(t) in landed
                    )
                    save_run(repo, record)
                return {"status": "partial", "run_id": run_id, "stem": candidate,
                        "dest_dir": str(dest), "files": statuses, "landed": landed}
        if blocked:
            continue
        if landed and record is not None:
            record.setdefault("receipts", []).extend(
                _receipt(s, Path(t)) for s, t, st in plan
                if st == "published" and str(t) in landed
            )
            record["heartbeat"] = utc_now_iso()
            save_run(repo, record)
        return {"status": "ok", "run_id": run_id, "stem": candidate,
                "dest_dir": str(dest), "files": statuses}
    raise WorkspaceError(f"no free name for {stem!r} in {dest}")


# --- workspaces ------------------------------------------------------------

# Copied into a new workspace because git does not carry ignored runtime files.
# Kept in step with mash-parallel's allowlist by a parity test.
RUNTIME_FILE_ALLOWLIST = (
    "AGENTS.md", ".env", ".env.example", ".cursor", ".opencode", "opencode.json", ".pi",
)

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def _git(args: list[str], cwd: str | Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(cwd), *args],
                          capture_output=True, text=True, check=False)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy_runtime_files(primary: Path, workspace: Path) -> dict[str, str]:
    """Copy ignored runtime files and remember what was copied, per file.

    The digest is what later lets cleanup tell "a copy we made" from "work the
    user did here". A directory is recorded file-by-file rather than as one
    opaque "directory" marker, because an edit inside a copied directory is
    still an edit, and a marker cannot see it.
    """
    copied: dict[str, str] = {}
    for name in RUNTIME_FILE_ALLOWLIST:
        src, dst = primary / name, workspace / name
        if dst.exists() or not src.exists():
            continue
        if src.is_file():
            shutil.copy2(src, dst)
            copied[name] = _digest(dst)
        elif src.is_dir():
            shutil.copytree(src, dst, symlinks=True)
            for path in sorted(dst.rglob("*")):
                relative = path.relative_to(workspace).as_posix()
                if path.is_symlink():
                    copied[relative] = "symlink:" + os.readlink(path)
                elif path.is_file():
                    copied[relative] = _digest(path)
    return copied


def workspaces_root(repo: str | Path) -> Path:
    return state_root(repo) / "worktrees"


def create_workspace(repo: str | Path, run_id: str, slug: str, base: str = "HEAD") -> dict:
    """Create a workspace this run owns.

    The directory and branch carry the run id, so a repeated slug can never
    hand a second run the first run's working directory.
    """
    if not SLUG_RE.match(slug):
        raise WorkspaceError(f"invalid slug {slug!r}: use lowercase letters, digits, hyphens")
    record = load_run(repo, run_id)
    primary = primary_checkout(repo)
    suffix = run_id.rsplit("-", 1)[-1]
    name = f"{slug}-{suffix}"
    workspace = workspaces_root(repo) / name
    branch = f"feature/{name}"
    if workspace.exists():
        raise WorkspaceError(f"{workspace} already exists; resume it instead")
    if _git(["rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"], primary).returncode == 0:
        raise WorkspaceError(f"branch {branch} already exists; resume it instead")

    acquire_lease(repo, run_id, "workspace", str(workspace))
    workspace.parent.mkdir(parents=True, exist_ok=True)
    res = _git(["worktree", "add", "-b", branch, str(workspace), base], primary)
    if res.returncode != 0:
        release_lease(repo, run_id, "workspace", str(workspace))
        raise WorkspaceError(f"git worktree add failed: {res.stderr.strip()}")

    copied = _copy_runtime_files(primary, workspace)
    record = load_run(repo, run_id)
    record["workspace"] = str(workspace)
    record["branch"] = branch
    record["base"] = base
    record["copied_runtime_files"] = copied
    save_run(repo, record)
    return {"status": "created", "run_id": run_id, "workspace": str(workspace),
            "branch": branch, "base": base, "copied": sorted(copied)}


def adopt_workspace(repo: str | Path, run_id: str, path: str | Path) -> dict:
    """Claim an existing checkout for in-place work."""
    record = load_run(repo, run_id)
    workspace = Path(path).resolve()
    if not workspace.is_dir():
        raise WorkspaceError(f"{workspace} is not a directory")
    acquire_lease(repo, run_id, "workspace", str(workspace))
    record = load_run(repo, run_id)
    record["workspace"] = str(workspace)
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], workspace)
    record["branch"] = branch.stdout.strip() or None
    save_run(repo, record)
    return {"status": "adopted", "run_id": run_id, "workspace": str(workspace),
            "branch": record["branch"]}


def resume_workspace(repo: str | Path, run_id: str, path: str | Path) -> dict:
    """Take over a workspace whose previous owner released it or died."""
    workspace = Path(path).resolve()
    if not workspace.is_dir():
        raise WorkspaceError(f"{workspace} is not a directory")
    acquire_lease(repo, run_id, "workspace", str(workspace))
    record = load_run(repo, run_id)
    record["workspace"] = str(workspace)
    save_run(repo, record)
    return {"status": "resumed", "run_id": run_id, "workspace": str(workspace)}


def _modified_copied_files(record: dict, workspace: Path) -> list[str]:
    """Copied runtime files whose content no longer matches what was copied."""
    changed = []
    for name, digest in (record.get("copied_runtime_files") or {}).items():
        path = workspace / name
        if isinstance(digest, str) and digest.startswith("symlink:"):
            if not path.is_symlink() or "symlink:" + os.readlink(path) != digest:
                changed.append(name)
            continue
        if digest == "directory":
            continue  # legacy record from before per-file manifests
        if not path.is_file():
            changed.append(name)
            continue
        if _digest(path) != digest:
            changed.append(name)
    return changed


def _unpublished_artifacts(repo: str | Path, run_id: str, workspace: Path) -> list[str]:
    """Artifacts written in the workspace that never reached the primary checkout.

    Matched by recorded source path. A basename would confuse
    `.mash/plans/x.md` with `.mash/qa/x.md`, letting a published namesake hide
    an unpublished artifact from the cleanup guard.
    """
    published = published_sources(load_run(repo, run_id))
    pending = []
    for area in ("brainstorms", "plans", "qa", "dogfood", "ideation", "insights", "solutions"):
        root = workspace / ".mash" / area
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or "scratch" in path.parts:
                continue
            if str(path.resolve()) not in published:
                pending.append(str(path.relative_to(workspace)))
    return pending


def _dirty_paths(workspace: Path, record: dict) -> list[str]:
    """Real changes, ignoring copies this helper made and still owns."""
    copied = set(record.get("copied_runtime_files") or {})
    res = _git(["status", "--porcelain", "--untracked-files=all"], workspace)
    dirty = []
    for line in res.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip().strip('"')
        if line[:2] == "??" and (path in copied or any(path.startswith(f"{c}/") for c in copied)):
            continue
        dirty.append(path)
    return dirty


def remove_workspace(repo: str | Path, run_id: str, path: str | Path, force: bool = False) -> dict:
    """Remove a workspace this run owns, refusing to discard unfinished work."""
    record = load_run(repo, run_id)
    workspace = Path(path).resolve()
    primary = primary_checkout(repo)
    managed = workspaces_root(repo).resolve()
    if managed not in workspace.parents:
        raise WorkspaceError(
            f"refusing to remove {workspace}: it is outside the managed root {managed}"
        )

    lease = read_lease(repo, "workspace", str(workspace))
    if lease is not None and lease.get("run_id") != run_id:
        raise Blocked(
            f"{workspace} is held by run {lease.get('run_id')}",
            {"status": "blocked", "kind": "workspace", "key": str(workspace),
             "blocker": f"refusing to remove {workspace}: it is held by run {lease.get('run_id')}",
             "holder": _holder_view(lease),
             "recovery": ["let the holder finish", "or end that run first"]},
        )

    if not force:
        dirty = _dirty_paths(workspace, record)
        if dirty:
            raise WorkspaceError(
                f"{workspace} has uncommitted changes ({', '.join(dirty[:5])}); "
                "commit them, or pass --force to discard"
            )
        modified = _modified_copied_files(record, workspace)
        if modified:
            raise WorkspaceError(
                f"{workspace} has modified copied files ({', '.join(modified)}); "
                "save them, or pass --force to discard"
            )
        pending = _unpublished_artifacts(repo, run_id, workspace)
        if pending:
            raise WorkspaceError(
                f"{workspace} holds unpublished artifacts ({', '.join(pending[:5])}); "
                "publish them, or pass --force to discard"
            )

    res = _git(["worktree", "remove", "--force", str(workspace)], primary)
    if res.returncode != 0:
        raise WorkspaceError(f"git worktree remove failed: {res.stderr.strip()}")
    release_lease(repo, run_id, "workspace", str(workspace))
    return {"status": "removed", "run_id": run_id, "workspace": str(workspace)}


# --- transfer ---------------------------------------------------------------


def _resolve_within(root: Path, relative: str) -> Path:
    """Resolve `relative` under `root`, refusing anything that escapes it."""
    if Path(relative).is_absolute():
        raise WorkspaceError(f"{relative!r} must be relative to the source checkout")
    resolved = (root / relative).resolve()
    if root not in resolved.parents and resolved != root:
        raise WorkspaceError(f"{relative!r} resolves outside {root}")
    return resolved


def transfer(source: str | Path, target: str | Path, files: list[str]) -> dict:
    """Copy a declared set of files from one checkout into another.

    This replaces `git stash` for carrying work onto a feature branch. A stash
    is one shared stack in the shared checkout, so concurrent runs could pop
    each other's entries; naming the files touches nothing else. The source
    checkout is left exactly as it was.
    """
    source_root = Path(source).resolve()
    target_root = Path(target).resolve()
    if not files:
        raise WorkspaceError("no files to transfer: name the files to carry forward")
    if not target_root.is_dir():
        raise WorkspaceError(f"{target_root} is not a directory")

    # Resolve and check everything before copying anything, so a bad entry
    # cannot leave the target half-populated. Both sides are confined: checking
    # only the source would let a symlink in the target write through it.
    planned: list[tuple[Path, Path, str]] = []
    for relative in files:
        src = _resolve_within(source_root, relative)
        if not src.is_file():
            raise WorkspaceError(f"{relative!r} does not exist in {source_root}")
        dst = _resolve_within(target_root, relative)
        if dst.is_symlink():
            raise WorkspaceError(f"{relative!r} is a symlink in the target; refusing to write through it")
        planned.append((src, dst, relative))

    moved = {}
    for src, dst, relative in planned:
        if dst.exists():
            # A tracked file from the base is the normal case for shipping: the
            # worktree carries the old content and the source carries the edit.
            # Replacing is expected, but it is reported, never silent.
            moved[relative] = "unchanged" if _same_bytes(src, dst) else "replaced"
            if moved[relative] == "unchanged":
                continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst, follow_symlinks=False)
    return {"status": "ok", "source": str(source_root), "target": str(target_root),
            "files": moved}


# --- CLI -------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    # `--repo` is accepted before or after the subcommand: skills write it at
    # the end of a command line, and argparse only honors a parent-level option
    # before the subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", dest="repo_leaf", default=None,
                        help="any directory inside the target repo")

    parser = argparse.ArgumentParser(prog="workspace.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", default=".", help="any directory inside the target repo")
    sub = parser.add_subparsers(dest="group", required=True)

    run = sub.add_parser("run", help="run registry").add_subparsers(dest="cmd", required=True)
    start = run.add_parser("start", help="register a run", parents=[common])
    start.add_argument("--workflow", required=True)
    start.add_argument("--workspace")
    start.add_argument("--branch")
    start.add_argument("--base")
    start.add_argument("--agent")
    for name in ("show", "heartbeat"):
        node = run.add_parser(name, parents=[common])
        node.add_argument("--run", required=True)
    end = run.add_parser("end", parents=[common])
    end.add_argument("--run", required=True)
    end.add_argument("--status", default="finished", choices=RUN_STATUSES)

    lease = sub.add_parser("lease", help="exclusive claims").add_subparsers(dest="cmd", required=True)
    for name in ("acquire", "release"):
        node = lease.add_parser(name, parents=[common])
        node.add_argument("--run", required=True)
        node.add_argument("--kind", required=True, choices=LEASE_KINDS)
        node.add_argument("--key", required=True)
    acquire_node = lease.choices["acquire"]
    acquire_node.add_argument("--owner-pid", type=int, default=None,
                              help="long-lived process that owns this claim (default: this process)")
    reclaim = lease.add_parser("reclaim", help="take back a lease whose owner is gone", parents=[common])
    reclaim.add_argument("--run", required=True)
    reclaim.add_argument("--kind", required=True, choices=LEASE_KINDS)
    reclaim.add_argument("--key", required=True)
    reclaim.add_argument("--force", action="store_true",
                         help="reclaim even when the owner cannot be proven gone")
    show = lease.add_parser("show", parents=[common])
    show.add_argument("--kind", required=True, choices=LEASE_KINDS)
    show.add_argument("--key", required=True)

    space = sub.add_parser("workspace", help="workspace lifecycle").add_subparsers(
        dest="cmd", required=True)
    create = space.add_parser("create", parents=[common])
    create.add_argument("--run", required=True)
    create.add_argument("--slug", required=True)
    create.add_argument("--base", default="HEAD")
    for name in ("adopt", "resume"):
        node = space.add_parser(name, parents=[common])
        node.add_argument("--run", required=True)
        node.add_argument("--path", required=True)
    remove = space.add_parser("remove", parents=[common])
    remove.add_argument("--run", required=True)
    remove.add_argument("--path", required=True)
    remove.add_argument("--force", action="store_true")

    move = sub.add_parser("transfer", help="carry declared files into a workspace",
                          parents=[common])
    move.add_argument("--from", dest="source", required=True)
    move.add_argument("--to", dest="target", required=True)
    move.add_argument("--file", action="append", required=True,
                      help="path relative to the source checkout; repeatable")

    publish = sub.add_parser("publish", help="atomic artifact publication", parents=[common])
    publish.add_argument("--run", required=True)
    publish.add_argument("--dest-dir", required=True)
    publish.add_argument("--stem", required=True)
    publish.add_argument("--file", action="append", required=True, metavar="PATH:SUFFIX",
                         help="source path and the suffix it takes under the stem")
    return parser


def _parse_file_arg(raw: str) -> tuple[Path, str]:
    path, sep, suffix = raw.rpartition(":")
    if not sep:
        raise WorkspaceError(f"--file expects PATH:SUFFIX, got {raw!r}")
    return Path(path), suffix


def _dispatch(args) -> dict:
    repo = getattr(args, "repo_leaf", None) or args.repo
    if args.group == "publish":
        entries = [_parse_file_arg(raw) for raw in args.file]
        return publish_group(repo, args.run, entries, args.dest_dir, args.stem)
    if args.group == "transfer":
        return transfer(args.source, args.target, args.file)
    if args.group == "lease" and args.cmd == "reclaim":
        return reclaim_lease(repo, args.run, args.kind, args.key, force=args.force)
    if args.group == "workspace":
        if args.cmd == "create":
            return create_workspace(repo, args.run, args.slug, args.base)
        if args.cmd == "adopt":
            return adopt_workspace(repo, args.run, args.path)
        if args.cmd == "resume":
            return resume_workspace(repo, args.run, args.path)
        return remove_workspace(repo, args.run, args.path, args.force)
    if args.group == "run":
        if args.cmd == "start":
            return register_run(repo, args.workflow, workspace=args.workspace,
                                branch=args.branch, base=args.base, agent=args.agent)
        if args.cmd == "show":
            return load_run(repo, args.run)
        if args.cmd == "heartbeat":
            return heartbeat(repo, args.run)
        return end_run(repo, args.run, args.status)
    if args.cmd == "acquire":
        return acquire_lease(repo, args.run, args.kind, args.key)
    if args.cmd == "release":
        return release_lease(repo, args.run, args.kind, args.key)
    lease = read_lease(repo, args.kind, args.key)
    return {"status": "held" if lease else "free", "kind": args.kind, "key": args.key,
            "holder": _holder_view(lease) if lease else None}


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        payload = _dispatch(args)
    except SystemExit:
        raise
    except Blocked as exc:
        print(json.dumps(exc.payload, indent=2))
        return 2
    except WorkspaceError as exc:
        print(json.dumps({"status": "blocked", "blocker": str(exc)}, indent=2))
        return 2
    except OSError as exc:
        # A read-only state root, a full disk, or a filesystem without hard
        # links is a refusal to report, not a traceback for the agent to parse.
        print(json.dumps({
            "status": "error", "kind": "io",
            "blocker": f"{getattr(exc, 'strerror', None) or exc}",
            "recovery": ["check the .mash state root is writable and has space",
                         "stop and report; this is not contention"],
        }, indent=2))
        return 1
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
