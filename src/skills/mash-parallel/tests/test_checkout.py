"""U5 tests: orchestrator works from a primary checkout or a linked worktree."""

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import mash_parallel as rp


def _git(*args, cwd):
    return subprocess.run(
        ["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _primary(tmp_path):
    repo = tmp_path / "primary"
    repo.mkdir()
    _git("init", "-q", cwd=repo)
    _git("config", "user.email", "t@t", cwd=repo)
    _git("config", "user.name", "t", cwd=repo)
    (repo / "base.txt").write_text("base\n")
    _git("add", "base.txt", cwd=repo)
    _git("commit", "-qm", "init", "--no-gpg-sign", cwd=repo)
    return repo


def test_primary_checkout_is_identity_for_primary(tmp_path):
    repo = _primary(tmp_path)
    assert rp.primary_checkout(repo).resolve() == repo.resolve()


def test_primary_checkout_maps_linked_worktree_to_primary(tmp_path):
    repo = _primary(tmp_path)
    wt = tmp_path / "feature"
    _git("worktree", "add", "-q", str(wt), "-b", "feature/x", cwd=repo)
    assert (wt / ".git").is_file()
    assert rp.primary_checkout(wt).resolve() == repo.resolve()


def test_primary_checkout_outside_repo_falls_back(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert rp.primary_checkout(plain) == plain


def test_is_git_repo_accepts_linked_worktree_file(tmp_path):
    repo = _primary(tmp_path)
    wt = tmp_path / "feature"
    _git("worktree", "add", "-q", str(wt), "-b", "feature/y", cwd=repo)
    assert rp._is_git_repo(repo)
    assert rp._is_git_repo(wt)


def test_run_state_lands_in_primary_when_started_from_worktree(tmp_path):
    repo = _primary(tmp_path)
    wt = tmp_path / "feature"
    _git("worktree", "add", "-q", str(wt), "-b", "feature/z", cwd=repo)
    root = rp.primary_checkout(wt)
    run_id = "20260101-000000"
    rp.save_run(root, {"run_id": run_id, "tasks": {}})
    assert rp.state_path(repo, run_id).exists()
    assert not rp.state_path(wt, run_id).exists()


def test_origin_lookup_reads_primary_brainstorms(tmp_path):
    repo = _primary(tmp_path)
    brains = repo / ".mash" / "brainstorms"
    brains.mkdir(parents=True)
    (brains / "widgets-requirements.md").write_text("## Requirements\n")
    wt = tmp_path / "feature"
    _git("worktree", "add", "-q", str(wt), "-b", "feature/w", cwd=repo)
    root = rp.primary_checkout(wt)
    assert rp.existing_brainstorm_origin(root, "widgets") == ".mash/brainstorms/widgets-requirements.md"
