"""U5 tests: worktree manager (R4, R13, R19, R21, R23)."""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import rosey_parallel as rp  # noqa: E402


def _init_repo(tmp_path):
    """Fresh git repo with an initial commit on 'main' and a base file."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "base.txt").write_text("base\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "base.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-qm", "init", "--no-gpg-sign"],
        check=True,
    )
    return tmp_path


def test_create_and_remove_worktree(tmp_path):
    repo = _init_repo(tmp_path)
    wt_path = repo / "wt1"
    branch = rp.create_worktree(repo, wt_path, "rosey-parallel/run1/t1", "HEAD")
    assert branch == "rosey-parallel/run1/t1"
    assert (wt_path / "base.txt").exists()
    # porcelain lists it
    out = subprocess.run(
        ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert str(wt_path) in out
    assert "rosey-parallel/run1/t1" in out
    rp.remove_worktree(repo, wt_path, branch)
    assert not wt_path.exists()
    # branch gone
    brs = subprocess.run(
        ["git", "-C", str(repo), "branch", "--list", "rosey-parallel/run1/t1"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "rosey-parallel/run1/t1" not in brs


def test_lock_honored_on_prune(tmp_path):
    repo = _init_repo(tmp_path)
    wt_path = repo / "wt1"
    rp.create_worktree(repo, wt_path, "rosey-parallel/run1/lock", "HEAD")
    rp.lock_worktree(repo, wt_path)
    # prune --all would remove unlocked worktrees; locked one must survive
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "prune"],
        check=True, capture_output=True,
    )
    assert wt_path.exists()


def test_duplicate_branch_is_error(tmp_path):
    repo = _init_repo(tmp_path)
    rp.create_worktree(repo, repo / "w1", "rosey-parallel/run1/dup", "HEAD")
    with pytest.raises(Exception):
        rp.create_worktree(repo, repo / "w2", "rosey-parallel/run1/dup", "HEAD")


def test_reset_hard_returns_to_track_tip(tmp_path):
    repo = _init_repo(tmp_path)
    wt = repo / "track"
    rp.create_worktree(repo, wt, "rosey-parallel/run1/track", "HEAD")
    # make a commit on the track branch
    (wt / "new.txt").write_text("new\n")
    subprocess.run(["git", "-C", str(wt), "add", "new.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(wt), "commit", "-qm", "track work", "--no-gpg-sign"],
        check=True,
    )
    # dirty the tree
    (wt / "base.txt").write_text("dirty\n")
    rp.reset_hard(wt, "rosey-parallel/run1/track")
    # base.txt back to committed content, new.txt still present
    assert (wt / "base.txt").read_text().strip() == "base"
    assert (wt / "new.txt").exists()


def test_runtime_files_copied(tmp_path):
    repo = _init_repo(tmp_path)
    # simulate repo-local runtime files that worktrees need
    (repo / "AGENTS.md").write_text("conventions\n")
    (repo / ".env").write_text("SECRET=1\n")
    wt = repo / "wt"
    rp.create_worktree(repo, wt, "rosey-parallel/run1/rf", "HEAD")
    # git never copies these into new worktrees automatically
    assert (wt / "AGENTS.md").exists() is False
    rp.copy_runtime_files(repo, wt)
    assert (wt / "AGENTS.md").read_text().strip() == "conventions"
    assert (wt / ".env").read_text().strip() == "SECRET=1"