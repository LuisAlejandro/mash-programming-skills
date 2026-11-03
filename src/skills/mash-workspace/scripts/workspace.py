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
      Exclusive claims. `kind` is the resource class (workspace, baseref, port,
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
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# A lease whose owner process is gone is reclaimed only after this much silence.
# Matches the window mash-parallel already uses for its track locks.
DEFAULT_STALE_WINDOW_S = 300.0

LEASE_KINDS = (
    "workspace",  # a checkout or worktree being written
    "baseref",    # a branch being published
    "port",       # a listening port
    "compose",    # a container project
    "db",         # a database or destructive dataset
    "browser",    # a browser profile or session
    "release",    # a release/tag operation
)

RUN_STATUSES = ("active", "finished", "failed")
_SAFE_KEY = re.compile(r"[^A-Za-z0-9._-]+")


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
    return runs_root(repo) / run_id


def run_record_path(repo: str | Path, run_id: str) -> Path:
    return run_dir(repo, run_id) / "run.json"


def lease_path(repo: str | Path, kind: str, key: str) -> Path:
    """One file per claim.

    The readable part is for humans reading `.mash/locks/`; the digest keeps
    two different keys that sanitize alike from colliding on one file.
    """
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
        candidate = run_id or new_run_id()
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
        outcome = release_lease(repo, run_id, kind, key, _update_run=False)
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
    """A lease is reclaimable only when its owner is provably gone.

    Liveness is only checkable on the machine that holds it, so a lease written
    by another host is never reclaimed here.
    """
    if lease.get("host") != hostname():
        return False, f"held on another host ({lease.get('host')!r}); cannot verify liveness"
    pid = lease.get("pid")
    if isinstance(pid, int) and is_pid_alive(pid):
        return False, f"owner pid {pid} is still alive"
    age = _age_seconds(lease.get("heartbeat"))
    if age <= stale_window_s:
        return False, f"owner is gone but heartbeat is only {age:.0f}s old"
    return True, f"owner pid {pid} is gone and silent for {age:.0f}s"


def acquire_lease(
    repo: str | Path,
    run_id: str,
    kind: str,
    key: str,
    stale_window_s: float = DEFAULT_STALE_WINDOW_S,
) -> dict:
    if kind not in LEASE_KINDS:
        raise WorkspaceError(f"unknown lease kind {kind!r}; expected one of {', '.join(LEASE_KINDS)}")
    record = load_run(repo, run_id)
    path = lease_path(repo, kind, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    lease = {
        "run_id": run_id,
        "kind": kind,
        "key": key,
        "pid": os.getpid(),
        "host": hostname(),
        "agent": record["owner"].get("agent"),
        "acquired_at": utc_now_iso(),
        "heartbeat": utc_now_iso(),
    }
    reclaimed_from = None
    for _ in range(2):
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
                     "recovery": [f"inspect {path}", "remove it only if no owner is running"]},
                ) from None
            if existing.get("run_id") == run_id:
                return {"status": "held", "run_id": run_id, "kind": kind, "key": key,
                        "holder": _holder_view(existing)}
            ok, why = is_reclaimable(existing, stale_window_s)
            if not ok:
                raise Blocked(
                    f"{kind}:{key} is held by run {existing.get('run_id')}",
                    {
                        "status": "blocked",
                        "kind": kind, "key": key,
                        "blocker": f"{kind}:{key} is held by run {existing.get('run_id')}: {why}",
                        "holder": _holder_view(existing),
                        "recovery": [
                            "wait for the holder to finish and retry",
                            "use a different workspace or resource",
                            f"if the holder is gone, it is reclaimed automatically after {stale_window_s:.0f}s of silence",
                        ],
                    },
                ) from None
            reclaimed_from = _holder_view(existing)
            path.unlink(missing_ok=True)
            continue
        with os.fdopen(fd, "w") as handle:
            json.dump(lease, handle)
        token = f"{kind}:{key}"
        if token not in record.get("leases", []):
            record.setdefault("leases", []).append(token)
            record["heartbeat"] = utc_now_iso()
            save_run(repo, record)
        return {"status": "acquired", "run_id": run_id, "kind": kind, "key": key,
                "reclaimed_from": reclaimed_from}
    raise WorkspaceError(f"could not acquire {kind}:{key} after reclaiming a stale lease")


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
        tmp.write_bytes(src.read_bytes())
        try:
            os.link(tmp, dst)
        except FileExistsError:
            return False
        return True
    finally:
        tmp.unlink(missing_ok=True)


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
    if dst.exists():
        if _same_bytes(src, dst):
            return {"status": "unchanged", "path": str(dst)}
        raise WorkspaceError(f"{dst} exists with different content; move it aside first")
    if not _link_exclusive(src, dst):
        if _same_bytes(src, dst):
            return {"status": "unchanged", "path": str(dst)}
        raise WorkspaceError(f"{dst} was created by another run with different content")
    if record is not None:
        record.setdefault("receipts", []).append(str(dst))
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
    stay paired. `run_id` may be None for callers that do not own a run yet;
    receipts are then not recorded.
    """
    record = load_run(repo, run_id) if run_id else None
    sources = [(Path(src), suffix) for src, suffix in entries]
    for src, _ in sources:
        if not src.is_file():
            raise WorkspaceError(f"{src} is not a readable file")
    dest = Path(dest_dir)

    for candidate in stem_candidates(stem):
        statuses: dict[str, str] = {}
        linked: list[Path] = []
        collided = False
        for src, suffix in sources:
            target = dest / f"{candidate}{suffix}"
            if target.exists():
                # Identical content is not a conflict; it is the same artifact.
                if _same_bytes(src, target):
                    statuses[target.name] = "unchanged"
                    continue
                collided = True
                break
            if _link_exclusive(src, target):
                statuses[target.name] = "published"
                linked.append(target)
                continue
            # Lost the race for this name: re-read before deciding.
            if _same_bytes(src, target):
                statuses[target.name] = "unchanged"
                continue
            collided = True
            break
        if collided:
            # Keep the group together: give back this candidate entirely.
            for path in linked:
                path.unlink(missing_ok=True)
            continue
        published = [str(dest / name) for name, state in statuses.items() if state == "published"]
        if published and record is not None:
            record.setdefault("receipts", []).extend(published)
            record["heartbeat"] = utc_now_iso()
            save_run(repo, record)
        return {"status": "ok", "run_id": run_id, "stem": candidate,
                "dest_dir": str(dest), "files": statuses}
    raise WorkspaceError(f"no free name for {stem!r} in {dest}")


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
    show = lease.add_parser("show", parents=[common])
    show.add_argument("--kind", required=True, choices=LEASE_KINDS)
    show.add_argument("--key", required=True)

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
    except Blocked as exc:
        print(json.dumps(exc.payload, indent=2))
        return 2
    except WorkspaceError as exc:
        print(json.dumps({"status": "blocked", "blocker": str(exc)}, indent=2))
        return 2
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
