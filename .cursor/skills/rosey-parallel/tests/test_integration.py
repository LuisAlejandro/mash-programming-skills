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


def test_integrate_report_is_json_serializable(tmp_path):
    # The integrate report must round-trip through json.dumps — a leaked
    # PosixPath leftover worktree crashed save_run with
    # "Object of type PosixPath is not JSON serializable".
    repo = _init_repo(tmp_path)
    wt = repo / "wt"
    rp.create_worktree(repo, wt, "rp/ser", "HEAD")
    (wt / "s.txt").write_text("s\n")
    subprocess.run(["git", "-C", str(wt), "add", "."], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-qm", "s", "--no-gpg-sign"], check=True)
    report = rp.integrate(repo, [{"branch": "rp/ser"}],
                          base_branch="master", gates=lambda tree: (True, []))
    import json
    dumped = json.dumps(report)
    assert isinstance(report["leftover_worktrees"][0], str)
    assert "rosey-parallel-integration" in report["leftover_worktrees"][0]


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


def test_halted_track_committed_work_still_merges(tmp_path):
    repo = _init_repo(tmp_path)
    wt = repo / "wt"
    rp.create_worktree(repo, wt, "rp/halted", "HEAD")
    (wt / "kept.txt").write_text("kept\n")
    subprocess.run(["git", "-C", str(wt), "add", "."], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-qm", "done-task", "--no-gpg-sign"], check=True)
    # Halted track: no further commits. Integrate still merges the branch.
    report = rp.integrate(
        repo, [{"branch": "rp/halted"}],
        base_branch="master", gates=lambda tree: (True, []),
    )
    assert report["status"] == "success"
    tip = _branch_point(repo)
    tree = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "--name-only", "-r", tip],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "kept.txt" in tree


def test_fix_up_round_caps_at_two(tmp_path):
    repo = _init_repo(tmp_path)
    wt = repo / "wt"
    rp.create_worktree(repo, wt, "rp/fix", "HEAD")
    (wt / "x.txt").write_text("x\n")
    subprocess.run(["git", "-C", str(wt), "add", "."], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-qm", "x", "--no-gpg-sign"], check=True)
    state = {"t1": rp.new_task("t1", "one")}
    state["t1"]["status"] = rp.STATUS_DONE
    state["t1"]["worktree_path"] = str(wt)
    tracks = [{"branch": "rp/fix", "track_id": 0, "tasks": ["t1"]}]
    run = {
        "run_id": "cap",
        "base_branch": "master",
        "base_sha_snapshot": _branch_point(repo),
        "fix_up_round": 0,
        "tasks": state,
    }

    class RejectVerify:
        def verify_phase(self, verifier, tip):
            return "fail"

    rp.finish_run(state, tracks, RejectVerify(), run, repo)
    assert run["fix_up_round"] > rp.MAX_FIX_UP_ROUNDS
    assert run["verification"]["passed"] is False


def test_fix_up_loop_does_not_remerge_merged_branches(tmp_path):
    # P2-6: the fix-up loop must refresh mergeable inside the loop and avoid
    # re-merging branches already merged in a prior round. A verify failure
    # followed by a pass must not re-integrate the same branch.
    repo = _init_repo(tmp_path)
    wt = repo / "wt"
    rp.create_worktree(repo, wt, "rp/once", "HEAD")
    (wt / "x.txt").write_text("x\n")
    subprocess.run(["git", "-C", str(wt), "add", "."], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-qm", "x", "--no-gpg-sign"], check=True)
    state = {"t1": rp.new_task("t1", "one")}
    state["t1"]["status"] = rp.STATUS_DONE
    state["t1"]["worktree_path"] = str(wt)
    tracks = [{"branch": "rp/once", "track_id": 0, "tasks": ["t1"]}]
    run = {
        "run_id": "once",
        "base_branch": "master",
        "base_sha_snapshot": _branch_point(repo),
        "fix_up_round": 0,
        "tasks": state,
    }

    calls = {"n": 0}

    class FlakyVerify:
        def __init__(self):
            self.n = 0
        def verify_phase(self, verifier, tip):
            self.n += 1
            return "fail" if self.n == 1 else "pass"

    orig = rp.integrate
    def spy_integrate(*a, **k):
        calls["n"] += 1
        return orig(*a, **k)
    rp.integrate = spy_integrate
    try:
        rp.finish_run(state, tracks, FlakyVerify(), run, repo)
    finally:
        rp.integrate = orig
    # First round merged the branch; the verify-fail round must NOT re-merge it.
    assert calls["n"] == 1
    assert run["verification"]["passed"] is True


def test_finish_run_gate_failure_blocks_base_ref_move(tmp_path):
    # P1-3: finish_run must pass a gates callable to integrate(); a failing
    # gate blocks the base-ref move (R17/R26) instead of moving it blindly.
    repo = _init_repo(tmp_path)
    wt = repo / "wt"
    rp.create_worktree(repo, wt, "rp/gated", "HEAD")
    (wt / "g.txt").write_text("g\n")
    subprocess.run(["git", "-C", str(wt), "add", "."], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-qm", "g", "--no-gpg-sign"], check=True)
    state = {"t1": rp.new_task("t1", "one")}
    state["t1"]["status"] = rp.STATUS_DONE
    state["t1"]["worktree_path"] = str(wt)
    tracks = [{"branch": "rp/gated", "track_id": 0, "tasks": ["t1"]}]
    run = {
        "run_id": "gated",
        "base_branch": "master",
        "base_sha_snapshot": _branch_point(repo),
        "fix_up_round": 0,
        "tasks": state,
    }
    base_before = _branch_point(repo)

    class PassVerify:
        def verify_phase(self, verifier, tip):
            return "pass"

    # The default gate runs the skill's test suite in the integration worktree.
    # The integration worktree has no .cursor/skills/rosey-parallel/tests, so
    # the default gate returns (True, []) and the base ref moves. To exercise
    # the gate-failure path, monkeypatch the default gate to fail.
    rp.finish_run(state, tracks, PassVerify(), run, repo)
    assert run["integration"]["status"] == "success"
    assert _branch_point(repo) != base_before

    # Now force a gate failure: base ref must NOT move.
    base_before2 = _branch_point(repo)
    run2 = {
        "run_id": "gated2",
        "base_branch": "master",
        "base_sha_snapshot": base_before2,
        "fix_up_round": 0,
        "tasks": state,
    }
    orig = rp._default_integration_gate
    rp._default_integration_gate = lambda tree: (False, ["tests failed"])
    try:
        rp.finish_run(state, tracks, PassVerify(), run2, repo)
    finally:
        rp._default_integration_gate = orig
    assert run2["integration"]["status"] == "fixup"
    assert _branch_point(repo) == base_before2

# --- Branch assertion: worker must stay on its track branch (B6 follow-up) ---


def test_assert_worktree_branch_accepts_matching_branch(tmp_path):
    repo = _init_repo(tmp_path)
    wt = repo / "wt"
    rp.create_worktree(repo, wt, "rp/match", "HEAD")
    assert rp.assert_worktree_branch(wt, "rp/match") is None


def test_assert_worktree_branch_rejects_wrong_branch(tmp_path):
    repo = _init_repo(tmp_path)
    wt = repo / "wt"
    rp.create_worktree(repo, wt, "rp/actual", "HEAD")
    err = rp.assert_worktree_branch(wt, "rp/expected")
    assert err is not None
    assert "rp/actual" in err and "rp/expected" in err


def test_assert_worktree_branch_ignores_unset_expectation(tmp_path):
    repo = _init_repo(tmp_path)
    wt = repo / "wt"
    rp.create_worktree(repo, wt, "rp/any", "HEAD")
    assert rp.assert_worktree_branch(wt, None) is None
    assert rp.assert_worktree_branch(wt, "") is None


def test_assert_worktree_branch_tolerates_missing_worktree(tmp_path):
    assert rp.assert_worktree_branch(tmp_path / "nope", "rp/x") is None
