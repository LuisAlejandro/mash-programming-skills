"""Regression tests for the hazards found in review of PR #4.

Each test here failed (or had no counterpart) before the fix, so the class of
bug cannot come back silently.
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


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    return root


def start(repo):
    return ws.register_run(repo, workflow="work")["run_id"]


# --- path containment (security review, findings 6 and 7) ------------------


@pytest.mark.parametrize("bad", ["..", ".", "a/b", "../x", "a\\b", "", "/abs"])
def test_a_run_id_can_never_escape_the_state_root(repo, bad):
    with pytest.raises(ws.WorkspaceError):
        ws.register_run(repo, workflow="w", run_id=bad)


def test_traversal_run_id_creates_nothing(repo, tmp_path):
    with pytest.raises(ws.WorkspaceError):
        ws.register_run(repo, workflow="w", run_id="../../escaped")
    assert not (tmp_path / "escaped").exists()


@pytest.mark.parametrize("bad", ["../escaped", "a/b", "..", "."])
def test_a_publish_stem_can_never_escape_the_destination(repo, tmp_path, bad):
    src = tmp_path / "s.md"
    src.write_text("x\n")
    dest = repo / ".mash" / "plans"
    dest.mkdir(parents=True)
    with pytest.raises(ws.WorkspaceError, match="filename component"):
        ws.publish_group(repo, None, [(src, ".md")], dest, bad)
    assert [p for p in dest.iterdir()] == []


@pytest.mark.parametrize("bad", ["/../x.md", ".md/..", "a/b"])
def test_a_publish_suffix_can_never_escape_the_destination(repo, tmp_path, bad):
    src = tmp_path / "s.md"
    src.write_text("x\n")
    dest = repo / ".mash" / "plans"
    dest.mkdir(parents=True)
    with pytest.raises(ws.WorkspaceError, match="filename component"):
        ws.publish_group(repo, None, [(src, bad)], dest, "doc")


def test_publication_leaves_nothing_outside_the_destination(repo, tmp_path):
    src = tmp_path / "s.md"
    src.write_text("x\n")
    dest = repo / ".mash" / "plans"
    ws.publish_group(repo, None, [(src, ".md")], dest, "doc")
    stray = [p for p in repo.rglob("*") if p.is_file() and p.parent != dest]
    assert stray == []


# --- transfer confinement (security review, finding 8) ---------------------


def test_transfer_refuses_a_symlinked_target_directory(repo, tmp_path):
    source = repo / "src"
    target = repo / "ship"
    outside = tmp_path / "outside"
    for path in (source, target, outside):
        path.mkdir()
    (source / "docs").mkdir()
    (source / "docs" / "x.md").write_text("payload\n")
    (target / "docs").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ws.WorkspaceError, match="outside|symlink"):
        ws.transfer(source, target, ["docs/x.md"])
    assert list(outside.iterdir()) == []


def test_transfer_refuses_a_symlinked_target_file(repo, tmp_path):
    source, target = repo / "src", repo / "ship"
    source.mkdir()
    target.mkdir()
    outside = tmp_path / "victim.md"
    outside.write_text("original\n")
    (source / "x.md").write_text("payload\n")
    (target / "x.md").symlink_to(outside)

    with pytest.raises(ws.WorkspaceError, match="outside|symlink"):
        ws.transfer(source, target, ["x.md"])
    assert outside.read_text() == "original\n"


# --- lease liveness (correctness, reliability, adversarial findings 2-4) ---


def test_a_stale_lease_is_never_taken_silently(repo):
    run = start(repo)
    ws.acquire_lease(repo, run, "workspace", "/w")
    lease = ws.read_lease(repo, "workspace", "/w")
    lease.update(pid=999999, owner_pid=999999, heartbeat="2000-01-01T00:00:00Z")
    ws.write_json_atomic(ws.lease_path(repo, "workspace", "/w"), lease)

    other = start(repo)
    with pytest.raises(ws.Blocked) as caught:
        ws.acquire_lease(repo, other, "workspace", "/w")
    assert caught.value.payload["stale"] is True
    assert ws.read_lease(repo, "workspace", "/w")["run_id"] == run


def test_reclaim_records_what_it_took(repo):
    run = start(repo)
    ws.acquire_lease(repo, run, "port", "3000")
    lease = ws.read_lease(repo, "port", "3000")
    lease.update(pid=999999, owner_pid=999999, heartbeat="2000-01-01T00:00:00Z")
    ws.write_json_atomic(ws.lease_path(repo, "port", "3000"), lease)

    other = start(repo)
    result = ws.reclaim_lease(repo, other, "port", "3000")
    assert result["reclaimed_from"]["run_id"] == run
    assert result["forced"] is False
    assert ws.acquire_lease(repo, other, "port", "3000")["status"] == "acquired"


def test_reclaim_is_atomic_between_two_recoverers(repo):
    run = start(repo)
    ws.acquire_lease(repo, run, "db", "shared")
    lease = ws.read_lease(repo, "db", "shared")
    lease.update(pid=999999, owner_pid=999999, heartbeat="2000-01-01T00:00:00Z")
    ws.write_json_atomic(ws.lease_path(repo, "db", "shared"), lease)

    runs = [start(repo) for _ in range(5)]
    procs = [
        subprocess.Popen(
            [sys.executable, str(SCRIPT), "lease", "reclaim", "--run", r,
             "--kind", "db", "--key", "shared", "--repo", str(repo)],
            stdout=subprocess.PIPE, text=True,
        )
        for r in runs
    ]
    outcomes = [json.loads(p.communicate()[0]) for p in procs]
    assert len([o for o in outcomes if o.get("status") == "reclaimed"]) == 1


def test_one_run_id_still_has_one_driver(repo):
    """Same process may re-enter; a different one must be refused."""
    run = start(repo)
    ws.acquire_lease(repo, run, "run", run)
    assert ws.acquire_lease(repo, run, "run", run)["status"] == "held"

    code = f"""
import sys
sys.path.insert(0, {str(SCRIPTS)!r})
import workspace as ws
try:
    ws.acquire_lease({str(repo)!r}, {run!r}, "run", {run!r})
    print("ACQUIRED")
except ws.Blocked:
    print("BLOCKED")
"""
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    assert "BLOCKED" in out.stdout


# --- cleanup safety (findings 5, 10, 14) ----------------------------------


def test_end_run_releases_the_rest_when_one_lease_was_taken(repo):
    run = start(repo)
    for key in ("/a", "/b", "/c"):
        ws.acquire_lease(repo, run, "workspace", key)
    stolen = ws.read_lease(repo, "workspace", "/b")
    stolen["run_id"] = "someone-else"
    ws.write_json_atomic(ws.lease_path(repo, "workspace", "/b"), stolen)

    result = ws.end_run(repo, run)
    assert result["kept"] == ["workspace:/b"]
    assert set(result["released"]) == {"workspace:/a", "workspace:/c"}
    assert ws.read_lease(repo, "workspace", "/a") is None


def test_receipts_are_matched_by_source_path_not_basename(repo, tmp_path):
    """A published `plans/x.md` must not vouch for an unpublished `qa/x.md`."""
    run = start(repo)
    primary = repo
    plans = primary / ".mash" / "plans"
    source = tmp_path / "x.md"
    source.write_text("plan\n")
    ws.publish_group(primary, run, [(source, ".md")], plans, "x")

    record = ws.load_run(primary, run)
    assert any(r["source"] == str(source.resolve()) for r in record["receipts"])

    workspace = primary / ".mash" / "worktrees" / "w"
    (workspace / ".mash" / "qa").mkdir(parents=True)
    (workspace / ".mash" / "qa" / "x.md").write_text("unpublished\n")
    pending = ws._unpublished_artifacts(primary, run, workspace)
    assert pending == [".mash/qa/x.md"]


def test_a_lost_publication_race_retries_instead_of_dropping(repo, tmp_path):
    """Losing one name must move to the next, not lose the artifact."""
    dest = repo / ".mash" / "plans"
    dest.mkdir(parents=True)
    (dest / "doc.md").write_text("theirs\n")
    src = tmp_path / "mine.md"
    src.write_text("mine\n")
    result = ws.publish_group(repo, None, [(src, ".md")], dest, "doc")
    assert result["status"] == "ok"
    assert result["stem"] == "doc-2"
    assert (dest / "doc.md").read_text() == "theirs\n"
    assert (dest / "doc-2.md").read_text() == "mine\n"
