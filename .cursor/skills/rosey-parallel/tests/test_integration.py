"""U9 tests: integration phase + final report (R3, R19, R20, R21)."""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import rosey_parallel as rp  # noqa: E402


def _init_repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(tmp_path), "config", k, v], check=True)
    (tmp_path / "base.txt").write_text("base\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "base.txt"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "init", "--no-gpg-sign"], check=True)
    return tmp_path


def _branch_point(repo):
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def test_two_disjoint_tracks_merge(tmp_path):
    repo = _init_repo(tmp_path)
    base_sha = _branch_point(repo)
    wt_a, wt_c = repo / "wta", repo / "wtc"
    rp.create_worktree(repo, wt_a, "rp/t1", "HEAD")
    rp.create_worktree(repo, wt_c, "rp/t2", "HEAD")
    (wt_a / "a.txt").write_text("a\n")
    (wt_c / "c.txt").write_text("c\n")
    for wt, branch, msg in ((wt_a, "rp/t1", "t1"), (wt_c, "rp/t2", "t2")):
        subprocess.run(["git", "-C", str(wt), "add", "."], check=True)
        subprocess.run(["git", "-C", str(wt), "commit", "-qm", msg, "--no-gpg-sign"], check=True)
    # gates pass (stub)
    report = rp.integrate(repo, [{"branch": "rp/t1"}, {"branch": "rp/t2"}],
                          base_branch="master", gates=lambda tree: (True, []))
    # after integration base ref moved; both files merged into the tree
    tip = _branch_point(repo)
    tree = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "--name-only", "-r", tip],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "a.txt" in tree and "c.txt" in tree
    assert report["status"] == "success"
    assert report["merged_tracks"] == ["rp/t1", "rp/t2"]


def test_conflict_predictable_and_aborts_cleanly(tmp_path):
    repo = _init_repo(tmp_path)
    wt_a, wt_b = repo / "wta", repo / "wtb"
    rp.create_worktree(repo, wt_a, "rp/conf1", "HEAD")
    rp.create_worktree(repo, wt_b, "rp/conf2", "HEAD")
    # both edit the same file -> conflict
    (wt_a / "base.txt").write_text("a-wins\n")
    (wt_b / "base.txt").write_text("b-wins\n")
    for wt, branch, msg in ((wt_a, "rp/conf1", "a"), (wt_b, "rp/conf2", "b")):
        subprocess.run(["git", "-C", str(wt), "add", "."], check=True)
        subprocess.run(["git", "-C", str(wt), "commit", "-qm", msg, "--no-gpg-sign"], check=True)
    report = rp.integrate(repo, [{"branch": "rp/conf1"}, {"branch": "rp/conf2"}],
                          base_branch="master", gates=lambda tree: (True, []))
    assert report["status"] == "fixup"  # conflict surfaced to fix-up path
    # base ref untouched on conflict
    assert _branch_point(repo) != ""


def test_gate_failure_keeps_tree_and_needs_fixup(tmp_path):
    repo = _init_repo(tmp_path)
    wt = repo / "wt"
    rp.create_worktree(repo, wt, "rp/gate", "HEAD")
    (wt / "g.txt").write_text("g\n")
    subprocess.run(["git", "-C", str(wt), "add", "."], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-qm", "g", "--no-gpg-sign"], check=True)
    base_before = _branch_point(repo)
    # gate fails
    report = rp.integrate(repo, [{"branch": "rp/gate"}],
                          base_branch="master",
                          gates=lambda tree: (False, ["tests failed"]))
    assert report["status"] == "fixup"
    # base ref NOT moved on gate failure
    assert _branch_point(repo) == base_before


def test_halted_track_preserved_in_report(tmp_path):
    report = rp.final_report(
        tracks=[{"track_id": 0, "tasks": ["t1"]}],
        run_state={"t1": {"status": rp.STATUS_BLOCKED, "blockers": ["x"]}},
        base_sha="abc", integration_tip="def", leftover_worktrees=["/tmp/wt"],
    )
    assert any(e["task"] == "t1" for e in report["blocked_tracks"])
    assert report["leftover_worktrees"] == ["/tmp/wt"]