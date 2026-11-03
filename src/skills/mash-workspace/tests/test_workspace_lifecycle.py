"""U3 tests: workspace ownership and safe cleanup (origin R6, R18, R19).

A workspace is owned by a run, not by a name. Cleanup never discards work that
was never published.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
SCRIPT = SCRIPTS / "workspace.py"
sys.path.insert(0, str(SCRIPTS))

import workspace as ws


def test_runtime_allowlist_matches_mash_parallel():
    """mash-parallel keeps its own copy; drift would isolate different files."""
    sys.path.insert(0, str(SCRIPTS.parent.parent / "mash-parallel" / "scripts"))
    import mash_parallel

    assert ws.RUNTIME_FILE_ALLOWLIST == mash_parallel.RUNTIME_FILE_ALLOWLIST


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
    (root / ".gitignore").write_text(".mash/\n")
    (root / "code.py").write_text("baseline\n")
    git(root, "add", "code.py", ".gitignore")
    git(root, "commit", "-qm", "baseline", "--no-gpg-sign")
    return root


def start(repo, workflow="work"):
    return ws.register_run(repo, workflow=workflow)["run_id"]


# --- create: identity is the run, not the slug (R6) ------------------------


def test_same_slug_twice_yields_distinct_owned_workspaces(repo):
    first = ws.create_workspace(repo, start(repo), "shared-topic")
    second = ws.create_workspace(repo, start(repo), "shared-topic")
    assert first["workspace"] != second["workspace"]
    assert first["branch"] != second["branch"]
    for result in (first, second):
        assert Path(result["workspace"]).is_dir()


def test_create_takes_the_workspace_lease_for_its_run(repo):
    run_id = start(repo)
    created = ws.create_workspace(repo, run_id, "topic")
    lease = ws.read_lease(repo, "workspace", created["workspace"])
    assert lease["run_id"] == run_id
    assert created["workspace"] in ws.load_run(repo, run_id)["leases"][0]


def test_create_records_copied_runtime_files_for_later_verification(repo):
    (repo / "AGENTS.md").write_text("conventions\n")
    created = ws.create_workspace(repo, start(repo), "topic")
    assert "AGENTS.md" in created["copied"]
    assert (Path(created["workspace"]) / "AGENTS.md").read_text() == "conventions\n"


# --- adopt and resume ------------------------------------------------------


def test_adopt_claims_an_existing_checkout(repo):
    run_id = start(repo)
    assert ws.adopt_workspace(repo, run_id, repo)["status"] == "adopted"
    assert ws.read_lease(repo, "workspace", str(repo.resolve()))["run_id"] == run_id


def test_second_run_cannot_adopt_a_held_checkout(repo):
    ws.adopt_workspace(repo, start(repo), repo)
    with pytest.raises(ws.Blocked):
        ws.adopt_workspace(repo, start(repo), repo)


def test_resume_by_a_different_live_run_is_refused(repo):
    owner = start(repo)
    created = ws.create_workspace(repo, owner, "topic")
    with pytest.raises(ws.Blocked):
        ws.resume_workspace(repo, start(repo), created["workspace"])


def test_resume_after_owner_release_succeeds(repo):
    owner = start(repo)
    created = ws.create_workspace(repo, owner, "topic")
    ws.end_run(repo, owner)
    successor = start(repo)
    resumed = ws.resume_workspace(repo, successor, created["workspace"])
    assert resumed["status"] == "resumed"
    assert ws.read_lease(repo, "workspace", created["workspace"])["run_id"] == successor


# --- remove: never discard unpublished work (R18, R19) ---------------------


def test_remove_refuses_a_workspace_held_by_another_run(repo):
    owner = start(repo)
    created = ws.create_workspace(repo, owner, "topic")
    with pytest.raises(ws.Blocked):
        ws.remove_workspace(repo, start(repo), created["workspace"])
    assert Path(created["workspace"]).is_dir()


def test_remove_refuses_uncommitted_tracked_changes(repo):
    run_id = start(repo)
    created = ws.create_workspace(repo, run_id, "topic")
    (Path(created["workspace"]) / "code.py").write_text("work in progress\n")
    with pytest.raises(ws.WorkspaceError, match="uncommitted"):
        ws.remove_workspace(repo, run_id, created["workspace"])
    assert Path(created["workspace"]).is_dir()


def test_remove_refuses_a_modified_copied_runtime_file(repo):
    (repo / "AGENTS.md").write_text("original\n")
    run_id = start(repo)
    created = ws.create_workspace(repo, run_id, "topic")
    (Path(created["workspace"]) / "AGENTS.md").write_text("edited in the workspace\n")
    with pytest.raises(ws.WorkspaceError, match="modified"):
        ws.remove_workspace(repo, run_id, created["workspace"])
    assert (Path(created["workspace"]) / "AGENTS.md").exists()


def test_remove_refuses_an_unpublished_artifact(repo):
    run_id = start(repo)
    created = ws.create_workspace(repo, run_id, "topic")
    plans = Path(created["workspace"]) / ".mash" / "plans"
    plans.mkdir(parents=True)
    (plans / "never-exported-plan.md").write_text("plan\n")
    with pytest.raises(ws.WorkspaceError, match="unpublished"):
        ws.remove_workspace(repo, run_id, created["workspace"])


def test_remove_accepts_a_published_artifact(repo):
    run_id = start(repo)
    created = ws.create_workspace(repo, run_id, "topic")
    plans = Path(created["workspace"]) / ".mash" / "plans"
    plans.mkdir(parents=True)
    artifact = plans / "exported-plan.md"
    artifact.write_text("plan\n")
    ws.publish_group(repo, run_id, [(artifact, ".md")], repo / ".mash" / "plans", "exported-plan")
    assert ws.remove_workspace(repo, run_id, created["workspace"])["status"] == "removed"
    assert not Path(created["workspace"]).exists()


def test_clean_owned_workspace_removes_and_frees_the_lease(repo):
    run_id = start(repo)
    created = ws.create_workspace(repo, run_id, "topic")
    assert ws.remove_workspace(repo, run_id, created["workspace"])["status"] == "removed"
    assert not Path(created["workspace"]).exists()
    assert ws.read_lease(repo, "workspace", created["workspace"]) is None
    assert created["branch"] in git(repo, "branch", "--list", created["branch"])


def test_force_discards_explicitly(repo):
    run_id = start(repo)
    created = ws.create_workspace(repo, run_id, "topic")
    (Path(created["workspace"]) / "code.py").write_text("abandoned\n")
    assert ws.remove_workspace(repo, run_id, created["workspace"], force=True)["status"] == "removed"
    assert not Path(created["workspace"]).exists()


def test_remove_refuses_a_path_outside_the_managed_root(repo, tmp_path):
    run_id = start(repo)
    outside = tmp_path / "elsewhere"
    git(repo, "worktree", "add", "-q", str(outside), "-b", "feature/outside")
    with pytest.raises(ws.WorkspaceError, match="outside"):
        ws.remove_workspace(repo, run_id, outside)
    assert outside.is_dir()


# --- CLI -------------------------------------------------------------------


def test_cli_remove_reports_blocker_and_exits_two(repo):
    run_id = start(repo)
    created = ws.create_workspace(repo, run_id, "topic")
    (Path(created["workspace"]) / "code.py").write_text("wip\n")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "workspace", "remove", "--run", run_id,
         "--path", created["workspace"], "--repo", str(repo)],
        capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 2
    assert json.loads(proc.stdout)["status"] == "blocked"
