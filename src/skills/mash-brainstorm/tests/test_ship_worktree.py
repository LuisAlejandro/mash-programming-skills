"""U1 (plan 002) tests: review, ship, and remove subcommands."""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import feature_worktree as fw


def _git(*args, cwd):
    return subprocess.run(
        ["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def primary(tmp_path):
    repo = tmp_path / "primary"
    repo.mkdir()
    _git("init", "-q", "-b", "develop", cwd=repo)
    _git("config", "user.email", "t@t", cwd=repo)
    _git("config", "user.name", "t", cwd=repo)
    (repo / "a.txt").write_text("a\n")
    (repo / "b.txt").write_text("b\n")
    (repo / ".gitignore").write_text(".mash/\n")
    _git("add", "a.txt", "b.txt", ".gitignore", cwd=repo)
    _git("commit", "-qm", "init", "--no-gpg-sign", cwd=repo)
    _git("update-ref", "refs/remotes/origin/develop", "HEAD", cwd=repo)
    return repo


# --- review-create ---------------------------------------------------------


def test_review_create_detached_at_sha_checked_out_elsewhere(primary):
    sha = _git("rev-parse", "HEAD", cwd=primary)
    out = fw.review_create(primary, sha, "run-1")
    wt = Path(out["worktree"])
    assert out["status"] == "created"
    assert wt == primary / ".mash" / "qa-worktrees" / "run-1"
    assert _git("rev-parse", "--abbrev-ref", "HEAD", cwd=wt) == "HEAD"
    assert _git("rev-parse", "HEAD", cwd=wt) == sha
    # primary branch is untouched and still checked out there
    assert _git("rev-parse", "--abbrev-ref", "HEAD", cwd=primary) == "develop"


def test_review_create_reuses_existing_worktree(primary):
    sha = _git("rev-parse", "HEAD", cwd=primary)
    fw.review_create(primary, sha, "run-1")
    assert fw.review_create(primary, sha, "run-1")["status"] == "reused"


def test_review_create_rejects_bad_run_id(primary):
    with pytest.raises(fw.FeatureWorktreeError, match="invalid run id"):
        fw.review_create(primary, "HEAD", "../escape")


# --- ship-create -----------------------------------------------------------


def test_ship_create_carries_unpushed_commit_primary_unchanged(primary):
    (primary / "a.txt").write_text("a\nlocal\n")
    _git("commit", "-qam", "local unpushed", cwd=primary)
    local_tip = _git("rev-parse", "HEAD", cwd=primary)
    out = fw.ship_create(primary, "widgets", "HEAD")
    wt = Path(out["worktree"])
    assert _git("rev-parse", "HEAD", cwd=wt) == local_tip
    assert _git("rev-parse", "--abbrev-ref", "HEAD", cwd=wt) == "feature/widgets"
    assert _git("rev-parse", "--abbrev-ref", "HEAD", cwd=primary) == "develop"


def test_ship_create_from_remote_base_excludes_unpushed(primary):
    (primary / "a.txt").write_text("a\nlocal\n")
    _git("commit", "-qam", "local unpushed", cwd=primary)
    out = fw.ship_create(primary, "widgets", "origin/develop")
    assert _git("rev-parse", "HEAD", cwd=Path(out["worktree"])) == _git(
        "rev-parse", "origin/develop", cwd=primary
    )


def test_ship_create_refuses_existing_branch(primary):
    _git("branch", "feature/widgets", cwd=primary)
    with pytest.raises(fw.FeatureWorktreeError, match="already exists"):
        fw.ship_create(primary, "widgets", "HEAD")


def test_ship_create_refuses_existing_worktree_path(primary):
    fw.ship_create(primary, "widgets", "HEAD")
    with pytest.raises(fw.FeatureWorktreeError, match="already exists"):
        fw.ship_create(primary, "widgets", "HEAD")


def test_ship_create_refuses_missing_base_ref(primary):
    with pytest.raises(fw.FeatureWorktreeError, match="does not resolve"):
        fw.ship_create(primary, "widgets", "origin/nope")


def _dirty_tree(primary):
    (primary / "a.txt").write_text("a\nstaged\n")
    _git("add", "a.txt", cwd=primary)
    (primary / "b.txt").write_text("b\nunstaged\n")
    (primary / "new.txt").write_text("new\n")







def test_remove_refuses_clean_primary_checkout(primary):
    with pytest.raises(fw.FeatureWorktreeError, match="not a linked worktree|only worktrees"):
        fw.remove_worktree(primary)


def test_remove_refuses_path_outside_mash(primary, tmp_path):
    outside = tmp_path / "outside"
    _git("worktree", "add", "-q", "-b", "feature/outside", str(outside), "HEAD", cwd=primary)
    with pytest.raises(fw.FeatureWorktreeError, match="only worktrees under .mash/"):
        fw.remove_worktree(outside)


def test_remove_allows_copied_runtime_files(primary):
    (primary / "AGENTS.md").write_text("conventions\n")
    wt = Path(fw.ship_create(primary, "widgets", "HEAD")["worktree"])
    assert (wt / "AGENTS.md").exists()  # untracked by design, copied by the helper
    assert fw.remove_worktree(wt)["status"] == "removed"
    assert not wt.exists()


def test_remove_refuses_dirty_without_force_then_removes(primary):
    wt = Path(fw.ship_create(primary, "widgets", "HEAD")["worktree"])
    (wt / "scratch.txt").write_text("wip\n")
    with pytest.raises(fw.FeatureWorktreeError, match="uncommitted changes"):
        fw.remove_worktree(wt)
    assert fw.remove_worktree(wt, force=True)["status"] == "removed"
    assert not wt.exists()
    # the branch survives for the report
    assert _git("rev-parse", "--verify", "feature/widgets", cwd=primary)


# --- copy-back --qa-run ----------------------------------------------------


def test_copy_back_qa_run_copies_artifacts_and_is_idempotent(primary):
    wt = Path(fw.ship_create(primary, "widgets", "HEAD")["worktree"])
    qa_dir = wt / ".mash" / "qa" / "run-1"
    (qa_dir / "nested").mkdir(parents=True)
    (qa_dir / "findings.json").write_text("{}\n")
    (qa_dir / "nested" / "a.json").write_text("{\"a\":1}\n")
    first = fw.copy_back(wt, None, qa_run="run-1")
    qa = next(r for r in first["results"] if r["kind"] == "qa")
    assert set(qa["files"].values()) == {"copied"}
    dest = primary / ".mash" / "qa" / "run-1"
    assert (dest / "findings.json").exists()
    assert (dest / "nested" / "a.json").exists()
    second = fw.copy_back(wt, None, qa_run="run-1")
    qa2 = next(r for r in second["results"] if r["kind"] == "qa")
    assert set(qa2["files"].values()) == {"unchanged"}


def test_copy_back_qa_run_refuses_different_content(primary):
    wt = Path(fw.ship_create(primary, "widgets", "HEAD")["worktree"])
    qa_dir = wt / ".mash" / "qa" / "run-1"
    qa_dir.mkdir(parents=True)
    (qa_dir / "findings.json").write_text("{}\n")
    dest = primary / ".mash" / "qa" / "run-1"
    dest.mkdir(parents=True)
    (dest / "findings.json").write_text("{\"user\":true}\n")
    with pytest.raises(fw.FeatureWorktreeError, match="different content"):
        fw.copy_back(wt, None, qa_run="run-1")
    assert (dest / "findings.json").read_text() == "{\"user\":true}\n"
