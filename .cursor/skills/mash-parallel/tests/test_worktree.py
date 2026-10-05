"""U5 tests: worktree manager (R4, R13, R19, R21, R23)."""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import mash_parallel as rp  # noqa: E402


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
    branch = rp.create_worktree(repo, wt_path, "mash-parallel/run1/t1", "HEAD")
    assert branch == "mash-parallel/run1/t1"
    assert (wt_path / "base.txt").exists()
    # porcelain lists it
    out = subprocess.run(
        ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert str(wt_path) in out
    assert "mash-parallel/run1/t1" in out
    rp._drop_worktree(repo, wt_path)
    assert not wt_path.exists()


def test_lock_honored_on_prune(tmp_path):
    repo = _init_repo(tmp_path)
    wt_path = repo / "wt1"
    rp.create_worktree(repo, wt_path, "mash-parallel/run1/lock", "HEAD")
    rp.lock_worktree(repo, wt_path)
    # prune --all would remove unlocked worktrees; locked one must survive
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "prune"],
        check=True, capture_output=True,
    )
    assert wt_path.exists()


def test_duplicate_branch_is_error(tmp_path):
    repo = _init_repo(tmp_path)
    rp.create_worktree(repo, repo / "w1", "mash-parallel/run1/dup", "HEAD")
    with pytest.raises(Exception):
        rp.create_worktree(repo, repo / "w2", "mash-parallel/run1/dup", "HEAD")


def test_reset_hard_returns_to_track_tip(tmp_path):
    repo = _init_repo(tmp_path)
    wt = repo / "track"
    rp.create_worktree(repo, wt, "mash-parallel/run1/track", "HEAD")
    # make a commit on the track branch
    (wt / "new.txt").write_text("new\n")
    subprocess.run(["git", "-C", str(wt), "add", "new.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(wt), "commit", "-qm", "track work", "--no-gpg-sign"],
        check=True,
    )
    # dirty the tree
    (wt / "base.txt").write_text("dirty\n")
    rp.reset_hard(wt, "mash-parallel/run1/track")
    # base.txt back to committed content, new.txt still present
    assert (wt / "base.txt").read_text().strip() == "base"
    assert (wt / "new.txt").exists()


def test_runtime_files_copied(tmp_path):
    repo = _init_repo(tmp_path)
    # simulate repo-local runtime files that worktrees need
    (repo / "AGENTS.md").write_text("conventions\n")
    (repo / ".env").write_text("SECRET=1\n")
    wt = repo / "wt"
    rp.create_worktree(repo, wt, "mash-parallel/run1/rf", "HEAD")
    # git never copies these into new worktrees automatically
    assert (wt / "AGENTS.md").exists() is False
    rp.copy_runtime_files(repo, wt)
    assert (wt / "AGENTS.md").read_text().strip() == "conventions"
    assert (wt / ".env").read_text().strip() == "SECRET=1"


def test_ensure_worktree_reuses_existing_path(tmp_path):
    repo = _init_repo(tmp_path)
    wt = repo / "w1"
    rp.create_worktree(repo, wt, "mash-parallel/run1/track-0", "HEAD")
    rp.ensure_task_worktree(repo, wt, "mash-parallel/run1/track-0", "HEAD")
    assert wt.exists()
    rp._drop_worktree(repo, wt)


def test_ensure_worktree_attaches_existing_branch(tmp_path):
    repo = _init_repo(tmp_path)
    wt1 = repo / "w1"
    rp.create_worktree(repo, wt1, "mash-parallel/run1/track-0", "HEAD")
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "remove", str(wt1)],
        check=True, capture_output=True, text=True,
    )
    wt2 = repo / "w2"
    rp.ensure_task_worktree(repo, wt2, "mash-parallel/run1/track-0", "HEAD")
    assert wt2.exists()
    rp._drop_worktree(repo, wt2)


def test_orchestrate_creates_worktrees_in_git_repo(tmp_path):
    class _Drv:
        def plan_task(self, tid):
            return "done"
        def work_phase(self, tid):
            return "done"
        def qa_phase(self, tid):
            return "done"
        def lint_phase(self, tid):
            return "done"

    repo = _init_repo(tmp_path)
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two")}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    run = rp.orchestrate_run(repo, tasks, footprints, _Drv(), gate=False)
    for t in run["tasks"].values():
        assert t["branch"]
        assert t.get("start_sha")
    listed = subprocess.run(
        ["git", "-C", str(repo), "worktree", "list"],
        capture_output=True, text=True, check=True,
    ).stdout
    # After integration, task worktrees are removed (R4).
    for t in run["tasks"].values():
        wt = t.get("worktree_path")
        if wt:
            assert wt not in listed
    assert run.get("integration", {}).get("status") == "success"


def test_resume_resets_reused_worktree_before_rerun(tmp_path):
    # P1-5: on resume, a re-run task's reused worktree is reset (reset_hard)
    # so leftover partial edits from an interrupted run don't leak into the
    # fresh work.
    seen_content = {}
    wt_path = {"path": None}

    class _Drv:
        def __init__(self):
            self.log = []
        def plan_task(self, tid):
            self.log.append(("plan", tid)); return "done"
        def work_phase(self, tid):
            self.log.append(("work", tid))
            # Capture the worktree content at the moment work runs (only on
            # the resume re-run, when the path is set).
            if wt_path["path"]:
                seen_content[tid] = (Path(wt_path["path"]) / "base.txt").read_text().strip()
            return "done"
        def qa_phase(self, tid):
            self.log.append(("qa", tid)); return "done"
        def lint_phase(self, tid):
            self.log.append(("lint", tid)); return "done"

    repo = _init_repo(tmp_path)
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    run = rp.orchestrate_run(repo, tasks, footprints, _Drv(), gate=False)
    # Interrupt mid-work: leave t1 WORKING. Recreate the worktree at the
    # resume path (finish_run dropped it after the first run) and dirty it.
    run_id = run["run_id"]
    branch = run["tasks"]["t1"]["branch"]
    wt = rp.run_dir(repo, run_id) / "worktrees" / "track-0"
    rp.ensure_task_worktree(repo, wt, branch, "HEAD")
    (wt / "base.txt").write_text("dirty leftover\n")
    wt_path["path"] = str(wt)
    resume = {**run}
    resume["tasks"]["t1"]["status"] = rp.STATUS_WORKING
    # Resume: t1 re-runs; its reused worktree must be reset to the branch tip
    # before work runs (P1-5).
    run2 = rp.orchestrate_run(repo, tasks, footprints, _Drv(), resume=resume, gate=False)
    assert run2["tasks"]["t1"]["status"] in (rp.STATUS_DONE, rp.STATUS_REPORTED)
    assert seen_content["t1"] == "base"  # reset, not dirty