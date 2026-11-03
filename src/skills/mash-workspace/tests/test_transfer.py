"""U6 tests: stash-free transfer of a declared file set (origin R16, R17).

`git stash` is a single shared stack in the shared checkout: concurrent runs
pushed and popped each other's entries. Transfer names its files instead.
"""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
SCRIPT = SCRIPTS / "workspace.py"
sys.path.insert(0, str(SCRIPTS))

import workspace as ws


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@t")
    git(root, "config", "user.name", "t")
    (root / "tracked.py").write_text("original\n")
    git(root, "add", "tracked.py")
    git(root, "commit", "-qm", "base", "--no-gpg-sign")
    return root


@pytest.fixture
def ship(repo, tmp_path):
    target = tmp_path / "ship"
    git(repo, "worktree", "add", "-q", str(target), "-b", "feature/ship")
    return target


# --- carrying work forward -------------------------------------------------


def test_modified_tracked_file_arrives_in_the_target(repo, ship):
    (repo / "tracked.py").write_text("edited\n")
    result = ws.transfer(repo, ship, ["tracked.py"])
    assert result["files"]["tracked.py"] == "replaced"
    assert (ship / "tracked.py").read_text() == "edited\n"


def test_untracked_file_arrives_with_its_directories(repo, ship):
    new = repo / "src" / "deep" / "new.py"
    new.parent.mkdir(parents=True)
    new.write_text("brand new\n")
    ws.transfer(repo, ship, ["src/deep/new.py"])
    assert (ship / "src" / "deep" / "new.py").read_text() == "brand new\n"


def test_file_mode_is_preserved(repo, ship):
    script = repo / "run.sh"
    script.write_text("#!/bin/sh\n")
    script.chmod(0o755)
    ws.transfer(repo, ship, ["run.sh"])
    assert (ship / "run.sh").stat().st_mode & 0o111


def test_the_source_checkout_is_never_modified(repo, ship):
    """The whole point: the user's tree is not disturbed to ship from it."""
    (repo / "tracked.py").write_text("edited\n")
    (repo / "untracked.txt").write_text("scratch\n")
    before = git(repo, "status", "--porcelain", "--untracked-files=all")
    ws.transfer(repo, ship, ["tracked.py", "untracked.txt"])
    assert git(repo, "status", "--porcelain", "--untracked-files=all") == before
    assert (repo / "tracked.py").read_text() == "edited\n"
    assert (repo / "untracked.txt").read_text() == "scratch\n"


def test_unlisted_changes_stay_behind(repo, ship):
    """Only the declared set travels, so unrelated dirty work is not shipped."""
    (repo / "tracked.py").write_text("mine\n")
    (repo / "someone-elses.txt").write_text("not mine\n")
    ws.transfer(repo, ship, ["tracked.py"])
    assert not (ship / "someone-elses.txt").exists()


# --- refusals --------------------------------------------------------------


def test_missing_file_is_refused_before_anything_is_copied(repo, ship):
    (repo / "tracked.py").write_text("edited\n")
    with pytest.raises(ws.WorkspaceError, match="does not exist"):
        ws.transfer(repo, ship, ["tracked.py", "ghost.py"])
    assert (ship / "tracked.py").read_text() == "original\n", "partial transfer"


def test_path_escaping_the_source_is_refused(repo, ship, tmp_path):
    (tmp_path / "outside.txt").write_text("secret\n")
    with pytest.raises(ws.WorkspaceError, match="outside"):
        ws.transfer(repo, ship, ["../outside.txt"])
    assert not (ship / "outside.txt").exists()


def test_absolute_path_is_refused(repo, ship):
    with pytest.raises(ws.WorkspaceError, match="relative"):
        ws.transfer(repo, ship, ["/etc/hostname"])


def test_empty_file_set_is_refused(repo, ship):
    with pytest.raises(ws.WorkspaceError, match="no files"):
        ws.transfer(repo, ship, [])


# --- concurrency -----------------------------------------------------------


def test_two_runs_shipping_at_once_do_not_cross_contaminate(repo, tmp_path):
    """The reproduced hazard: one run's stash was applied by the other."""
    first = tmp_path / "ship-a"
    second = tmp_path / "ship-b"
    git(repo, "worktree", "add", "-q", str(first), "-b", "feature/a")
    git(repo, "worktree", "add", "-q", str(second), "-b", "feature/b")
    (repo / "a.txt").write_text("run a work\n")
    (repo / "b.txt").write_text("run b work\n")

    procs = [
        subprocess.Popen([sys.executable, str(SCRIPT), "transfer", "--from", str(repo),
                          "--to", str(target), "--file", name, "--repo", str(repo)],
                         stdout=subprocess.PIPE, text=True)
        for target, name in ((first, "a.txt"), (second, "b.txt"))
    ]
    for proc in procs:
        assert proc.wait(timeout=30) == 0

    assert (first / "a.txt").read_text() == "run a work\n"
    assert not (first / "b.txt").exists()
    assert (second / "b.txt").read_text() == "run b work\n"
    assert not (second / "a.txt").exists()


def test_symlink_in_the_target_is_refused(repo, ship, tmp_path):
    """The destination side is confined too: a symlinked dir is not written through."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (ship / "docs").symlink_to(outside, target_is_directory=True)
    (repo / "docs").mkdir()
    (repo / "docs" / "x.md").write_text("payload\n")
    with pytest.raises(ws.WorkspaceError, match="outside|symlink"):
        ws.transfer(repo, ship, ["docs/x.md"])
    assert list(outside.iterdir()) == []


def test_replaced_content_is_reported_not_silent(repo, ship):
    """Shipping a tracked edit replaces the base copy, and says so."""
    (repo / "tracked.py").write_text("edited\n")
    result = ws.transfer(repo, ship, ["tracked.py"])
    assert result["files"]["tracked.py"] == "replaced"
    assert ws.transfer(repo, ship, ["tracked.py"])["files"]["tracked.py"] == "unchanged"
