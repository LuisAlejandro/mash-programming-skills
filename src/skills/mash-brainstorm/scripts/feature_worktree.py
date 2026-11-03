#!/usr/bin/env python3
"""Feature worktree helper for the brainstorm -> plan -> work pipeline (U1).

Subcommands (stdlib only, JSON on stdout):

  create <slug>
      Ensure `.mash/worktrees/<slug>` exists on branch `feature/<slug>`,
      created from HEAD of the primary checkout, and copy the runtime allowlist
      into it. Idempotent: an existing worktree on the same branch is reused.

  copy-back <worktree> [--plan <path>] [--qa-run <run-id>]
      Copy this run's gitignored `.mash/` artifacts from a linked feature
      worktree into the primary checkout. Copies flat `.mash/brainstorms/*-requirements.md`
      files and, when given, the plan plus its `.topology.json` and
      `.sentrux-review-brief.json` siblings; `--qa-run` copies
      `.mash/qa/<run-id>/`. Never overwrites: identical files are skipped, and a
      name that is taken by different content moves to the next free name (plan
      sequence NNN is bumped; other names get `-2`, `-3`). Plan siblings are
      renamed together so they stay paired.

  review-create <sha> --run-id <id>
      Detached worktree at `<sha>` under `.mash/qa-worktrees/<id>` for a
      `mash-qa` review of a PR or branch target. Detached so a branch already
      checked out in the primary checkout still works.

  ship-create <slug> --base <ref>
      `feature/<slug>` worktree under `.mash/worktrees/<slug>` from `<ref>`, so
      `mash-pr` ships without moving the primary checkout off its base branch.

  stash-apply <worktree> --message <msg>
      Apply the newest stash whose subject contains `<msg>` inside `<worktree>`
      with `--index`. A conflict leaves the stash in place and reports it.

  stash-drop --message <msg>
      Drop the newest stash whose subject contains `<msg>`. Refuses when none
      matches, so a near-miss never discards someone else's stash.

  remove <path> [--force]
      Remove a worktree under `.mash/`. Refuses tracked changes without
      `--force`, and refuses any path outside `.mash/`.

Exit codes: 0 success or no-op, 2 usage or refusal, 1 git failure.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def _load_workspace():
    """Load the shared coordination helper from the sibling skill.

    Publication must be atomic against other runs, and that logic lives in one
    place (`mash-workspace`) rather than being duplicated here.
    """
    path = Path(__file__).resolve().parents[2] / "mash-workspace" / "scripts" / "workspace.py"
    spec = importlib.util.spec_from_file_location("mash_workspace", path)
    if spec is None or spec.loader is None:  # pragma: no cover - packaging error
        raise RuntimeError(f"cannot load the mash-workspace helper at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_ws = _load_workspace()

# Owned by mash-workspace, which is the single definition. A parity test keeps
# mash_parallel's copy equal to it.
RUNTIME_FILE_ALLOWLIST = _ws.RUNTIME_FILE_ALLOWLIST

PLAN_SIBLING_SUFFIXES = (".topology.json", ".sentrux-review-brief.json")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class FeatureWorktreeError(RuntimeError):
    """A refusal or git failure. Message is the blocker text."""


def _git(args: list[str], cwd: str | Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=False
    )


def primary_checkout(path: str | Path) -> Path:
    """Primary checkout that owns `path`'s git common dir (same rule as mash_parallel)."""
    res = _git(["rev-parse", "--git-common-dir"], path)
    if res.returncode != 0 or not res.stdout.strip():
        return Path(path).resolve()
    common = Path(res.stdout.strip())
    if not common.is_absolute():
        common = Path(path) / common
    common = common.resolve()
    return common.parent if common.name == ".git" else Path(path).resolve()


def is_linked_worktree(path: str | Path) -> bool:
    res = _git(
        ["rev-parse", "--path-format=absolute", "--git-dir", "--git-common-dir"], path
    )
    if res.returncode != 0:
        return False
    git_dir, common = res.stdout.split()[:2]
    return Path(git_dir).resolve() != Path(common).resolve()


def copy_runtime_files(primary: Path, wt: Path) -> list[str]:
    """Copy allowlisted runtime files into `wt`, never replacing existing ones."""
    copied: list[str] = []
    for name in RUNTIME_FILE_ALLOWLIST:
        src, dst = primary / name, wt / name
        if dst.exists():
            continue
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(name)
        elif src.is_dir():
            shutil.copytree(src, dst)
            copied.append(name)
    return copied


def _worktree_branch(wt: Path) -> str | None:
    res = _git(["rev-parse", "--abbrev-ref", "HEAD"], wt)
    return res.stdout.strip() if res.returncode == 0 else None


def create(primary: Path, slug: str) -> dict:
    if not SLUG_RE.match(slug):
        raise FeatureWorktreeError(f"invalid slug {slug!r}: use lowercase letters, digits, hyphens")
    branch = f"feature/{slug}"
    wt = primary / ".mash" / "worktrees" / slug

    if wt.exists():
        # Resume path: reuse only when the existing directory is this slug's worktree.
        if _worktree_branch(wt) != branch:
            raise FeatureWorktreeError(
                f"{wt} exists but is not a worktree on {branch}; remove it or pick another slug"
            )
        copied = copy_runtime_files(primary, wt)
        return {"status": "reused", "worktree": str(wt), "branch": branch, "copied": copied}

    if _git(["rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"], primary).returncode == 0:
        raise FeatureWorktreeError(
            f"branch {branch} already exists without a worktree at {wt}; "
            "check it out with `git worktree add` manually or pick another slug"
        )

    wt.parent.mkdir(parents=True, exist_ok=True)
    res = _git(["worktree", "add", "-b", branch, str(wt), "HEAD"], primary)
    if res.returncode != 0:
        raise FeatureWorktreeError(f"git worktree add failed: {res.stderr.strip()}")
    copied = copy_runtime_files(primary, wt)
    return {"status": "created", "worktree": str(wt), "branch": branch, "copied": copied}


def _place_group(group: list[tuple[Path, str]], dst_dir: Path, stem: str,
                 run_id: str | None = None) -> dict:
    """Place a group (main file + siblings) under one shared stem.

    Delegates to the shared atomic publisher so a concurrent run can never win
    the gap between "does it exist" and "copy it". Statuses keep this helper's
    published vocabulary (`copied` / `unchanged`).
    """
    try:
        placed = _ws.publish_group(dst_dir, run_id, group, dst_dir, stem)
    except _ws.WorkspaceError as exc:
        raise FeatureWorktreeError(str(exc)) from exc
    return {
        "stem": placed["stem"],
        "files": {name: ("copied" if state == "published" else state)
                  for name, state in placed["files"].items()},
    }


def copy_back(worktree: Path, plan_rel: str | None, qa_run: str | None = None) -> dict:
    wt = worktree.resolve()
    if not is_linked_worktree(wt):
        return {"status": "noop", "reason": "not a linked feature worktree; nothing to copy back"}
    primary = primary_checkout(wt)
    results: list[dict] = []

    wt_brains = wt / ".mash" / "brainstorms"
    if wt_brains.is_dir():
        for req in sorted(wt_brains.glob("*-requirements.md")):
            if req.parent != wt_brains:
                continue
            placed = _place_group(
                [(req, ".md")], primary / ".mash" / "brainstorms", req.name[: -len(".md")]
            )
            results.append({"kind": "requirements", **placed})

    if plan_rel:
        plan = (wt / plan_rel).resolve()
        if not plan.is_file() or plan.parent != (wt / ".mash" / "plans").resolve():
            raise FeatureWorktreeError(f"plan {plan_rel} is not a file under .mash/plans/ in the worktree")
        stem = plan.name[: -len(".md")]
        group = [(plan, ".md")]
        for suffix in PLAN_SIBLING_SUFFIXES:
            sib = plan.parent / f"{stem}{suffix}"
            if sib.is_file():
                group.append((sib, suffix))
        placed = _place_group(group, primary / ".mash" / "plans", stem)
        results.append({"kind": "plan", **placed})

    if qa_run:
        if not SLUG_RE.match(qa_run):
            raise FeatureWorktreeError(f"invalid qa run id {qa_run!r}")
        src_dir = wt / ".mash" / "qa" / qa_run
        if not src_dir.is_dir():
            raise FeatureWorktreeError(f"no QA artifact at {src_dir}")
        copied: dict[str, str] = {}
        for src in sorted(src_dir.rglob("*")):
            if not src.is_file():
                continue
            rel = src.relative_to(src_dir)
            dst = primary / ".mash" / "qa" / qa_run / rel
            try:
                placed = _ws.publish_exact(primary, None, src, dst)
            except _ws.WorkspaceError as exc:
                raise FeatureWorktreeError(str(exc)) from exc
            copied[str(rel)] = "copied" if placed["status"] == "published" else placed["status"]
        results.append({"kind": "qa", "run": qa_run, "files": copied})

    return {"status": "ok", "primary": str(primary), "results": results}


def review_create(primary: Path, sha: str, run_id: str) -> dict:
    if not SLUG_RE.match(run_id):
        raise FeatureWorktreeError(f"invalid run id {run_id!r}: use lowercase letters, digits, hyphens")
    wt = primary / ".mash" / "qa-worktrees" / run_id
    if wt.exists():
        if _worktree_branch(wt) != "HEAD":
            raise FeatureWorktreeError(f"{wt} exists but is not a detached worktree; remove it first")
        return {"status": "reused", "worktree": str(wt), "copied": copy_runtime_files(primary, wt)}
    wt.parent.mkdir(parents=True, exist_ok=True)
    res = _git(["worktree", "add", "--detach", str(wt), sha], primary)
    if res.returncode != 0:
        raise FeatureWorktreeError(f"git worktree add --detach failed: {res.stderr.strip()}")
    head = _git(["rev-parse", "HEAD"], wt).stdout.strip()
    return {
        "status": "created",
        "worktree": str(wt),
        "head": head,
        "copied": copy_runtime_files(primary, wt),
    }


def ship_create(primary: Path, slug: str, base_ref: str) -> dict:
    if not SLUG_RE.match(slug):
        raise FeatureWorktreeError(f"invalid slug {slug!r}: use lowercase letters, digits, hyphens")
    branch = f"feature/{slug}"
    wt = primary / ".mash" / "worktrees" / slug
    if wt.exists():
        raise FeatureWorktreeError(
            f"{wt} already exists; resume that worktree instead of creating another on {branch}"
        )
    if _git(["rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"], primary).returncode == 0:
        raise FeatureWorktreeError(f"branch {branch} already exists without a worktree; check it out manually")
    if _git(["rev-parse", "--verify", "--quiet", base_ref], primary).returncode != 0:
        raise FeatureWorktreeError(f"base ref {base_ref} does not resolve; fetch it first")
    wt.parent.mkdir(parents=True, exist_ok=True)
    res = _git(["worktree", "add", "-b", branch, str(wt), base_ref], primary)
    if res.returncode != 0:
        raise FeatureWorktreeError(f"git worktree add failed: {res.stderr.strip()}")
    return {
        "status": "created",
        "worktree": str(wt),
        "branch": branch,
        "base": base_ref,
        "copied": copy_runtime_files(primary, wt),
    }


def _find_stash(primary: Path, message: str) -> tuple[str, str] | None:
    """Return (ref, subject) of the newest stash whose subject contains message."""
    res = _git(["stash", "list", "--format=%gd%x09%gs"], primary)
    if res.returncode != 0:
        return None
    for line in res.stdout.splitlines():
        ref, _, subject = line.partition("	")
        if message in subject:
            return ref, subject
    return None


def stash_apply(worktree: Path, message: str) -> dict:
    if not is_linked_worktree(worktree):
        raise FeatureWorktreeError(f"{worktree} is not a linked worktree")
    primary = primary_checkout(worktree)
    found = _find_stash(primary, message)
    if not found:
        raise FeatureWorktreeError(f"no stash whose subject contains {message!r}")
    ref, subject = found
    # --index keeps staged changes staged. It aborts the whole apply when the
    # index cannot be rebuilt, so fall back to a plain apply, which leaves
    # conflict markers the user can resolve. The stash is never dropped here.
    index_ok = _git(["stash", "apply", "--index", ref], worktree).returncode == 0
    plain_ok = index_ok
    if not index_ok:
        plain_ok = _git(["stash", "apply", ref], worktree).returncode == 0
    unmerged = _unmerged_paths(worktree)
    if unmerged:
        return {
            "status": "conflict",
            "stash": subject,
            "worktree": str(worktree),
            "conflicted": unmerged,
            "next": f"git -C {worktree} status, then resolve; the stash is kept",
        }
    if index_ok or plain_ok:
        return {
            "status": "applied",
            "stash": subject,
            "worktree": str(worktree),
            "index_restored": index_ok,
        }
    raise FeatureWorktreeError(
        f"stash apply failed in {worktree}; stash {subject!r} is kept"
    )


def _unmerged_paths(worktree: Path) -> list[str]:
    res = _git(["diff", "--name-only", "--diff-filter=U"], worktree)
    return [ln for ln in res.stdout.splitlines() if ln.strip()]


def stash_drop(primary: Path, message: str) -> dict:
    found = _find_stash(primary, message)
    if not found:
        raise FeatureWorktreeError(f"no stash whose subject contains {message!r}; nothing dropped")
    ref, subject = found
    res = _git(["stash", "drop", ref], primary)
    if res.returncode != 0:
        raise FeatureWorktreeError(f"git stash drop failed: {res.stderr.strip()}")
    return {"status": "dropped", "stash": subject}


def _dirty_paths(worktree: Path) -> list[str]:
    """Paths with real changes, ignoring the runtime files this helper copies in.

    The allowlist files are untracked by design, so counting them would make
    every worktree look dirty and block removal.
    """
    res = _git(["status", "--porcelain", "--untracked-files=all"], worktree)
    dirty: list[str] = []
    for line in res.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip().strip('"')
        if line[:2] == "??" and path in RUNTIME_FILE_ALLOWLIST:
            continue
        if line[:2] == "??" and any(path.startswith(f"{name}/") for name in RUNTIME_FILE_ALLOWLIST):
            continue
        dirty.append(path)
    return dirty


def remove_worktree(path: Path, force: bool = False) -> dict:
    wt = path.resolve()
    if not is_linked_worktree(wt):
        raise FeatureWorktreeError(f"{wt} is not a linked worktree")
    primary = primary_checkout(wt)
    mash_root = (primary / ".mash").resolve()
    if mash_root not in wt.parents:
        raise FeatureWorktreeError(f"refusing to remove {wt}: only worktrees under .mash/ are eligible")
    dirty = _dirty_paths(wt)
    if dirty and not force:
        raise FeatureWorktreeError(
            f"{wt} has uncommitted changes; commit them or pass --force"
        )
    # git refuses to remove a worktree holding untracked files, and the copied
    # runtime allowlist always leaves some. When nothing beyond those is dirty,
    # forcing discards only copies the helper can recreate.
    git_force = force or not dirty
    res = _git(["worktree", "remove"] + (["--force"] if git_force else []) + [str(wt)], primary)
    if res.returncode != 0:
        _git(["worktree", "unlock", str(wt)], primary)
        res = _git(["worktree", "remove"] + (["--force"] if git_force else []) + [str(wt)], primary)
    if res.returncode != 0:
        raise FeatureWorktreeError(f"git worktree remove failed: {res.stderr.strip()}")
    return {"status": "removed", "worktree": str(wt)}


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="feature_worktree.py", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create", help="create or reuse .mash/worktrees/<slug>")
    c.add_argument("slug")
    c.add_argument("--repo", default=".", help="any directory inside the target repo (default: cwd)")
    b = sub.add_parser("copy-back", help="copy .mash artifacts into the primary checkout")
    b.add_argument("worktree")
    b.add_argument("--plan", default=None, help="repo-relative plan path under .mash/plans/")
    b.add_argument("--qa-run", default=None, help="QA run id under .mash/qa/")

    r = sub.add_parser("review-create", help="detached review worktree for mash-qa")
    r.add_argument("sha")
    r.add_argument("--run-id", required=True)
    r.add_argument("--repo", default=".")

    s = sub.add_parser("ship-create", help="feature worktree from a base ref for mash-pr")
    s.add_argument("slug")
    s.add_argument("--base", required=True, help="base ref, e.g. origin/develop or HEAD")
    s.add_argument("--repo", default=".")

    a = sub.add_parser("stash-apply", help="apply a mash-pr stash inside a worktree")
    a.add_argument("worktree")
    a.add_argument("--message", required=True)

    d = sub.add_parser("stash-drop", help="drop a mash-pr stash after a successful commit")
    d.add_argument("--message", required=True)
    d.add_argument("--repo", default=".")

    rm = sub.add_parser("remove", help="remove a worktree under .mash/")
    rm.add_argument("path")
    rm.add_argument("--force", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.cmd == "create":
            out = create(primary_checkout(Path(args.repo)), args.slug)
        elif args.cmd == "review-create":
            out = review_create(primary_checkout(Path(args.repo)), args.sha, args.run_id)
        elif args.cmd == "ship-create":
            out = ship_create(primary_checkout(Path(args.repo)), args.slug, args.base)
        elif args.cmd == "stash-apply":
            out = stash_apply(Path(args.worktree), args.message)
        elif args.cmd == "stash-drop":
            out = stash_drop(primary_checkout(Path(args.repo)), args.message)
        elif args.cmd == "remove":
            out = remove_worktree(Path(args.path), args.force)
        else:
            out = copy_back(Path(args.worktree), args.plan, args.qa_run)
    except FeatureWorktreeError as exc:
        print(json.dumps({"status": "blocked", "blocker": str(exc)}, indent=2))
        return 2
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
