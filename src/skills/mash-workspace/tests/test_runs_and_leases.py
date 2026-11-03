"""U1 tests: run registry and leases (origin R1, R2, R5, R7, R20).

Concurrency is exercised with real OS processes, not threads (origin R22).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
SCRIPT = SCRIPTS / "workspace.py"
sys.path.insert(0, str(SCRIPTS))

import workspace as ws


def cli(*args, repo=None):
    """Invoke the helper as a separate process; return (exit_code, payload)."""
    cmd = [sys.executable, str(SCRIPT), *args]
    if repo is not None:
        cmd += ["--repo", str(repo)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"stdout": proc.stdout, "stderr": proc.stderr}
    return proc.returncode, payload


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    return root


def start_run(repo, workflow="work"):
    code, payload = cli("run", "start", "--workflow", workflow, repo=repo)
    assert code == 0, payload
    return payload["run_id"]


# --- run identity (R1, R2) -------------------------------------------------


def test_run_ids_are_distinct_within_one_timestamp_second(monkeypatch):
    monkeypatch.setattr(ws, "utc_now_compact", lambda: "20261103-150000")
    assert ws.new_run_id() != ws.new_run_id()


def test_run_start_registers_durable_record(repo):
    run_id = start_run(repo, workflow="brainstorm")
    record = json.loads((repo / ".mash" / "runs" / run_id / "run.json").read_text())
    assert record["run_id"] == run_id
    assert record["workflow"] == "brainstorm"
    assert record["owner"]["pid"] > 0
    assert record["owner"]["host"]
    assert record["status"] == "active"
    assert record["heartbeat"]


def test_duplicate_run_registration_is_refused(repo):
    run_id = start_run(repo)
    with pytest.raises(ws.WorkspaceError, match="already registered"):
        ws.register_run(repo, workflow="work", run_id=run_id)


def test_two_processes_registering_concurrently_get_distinct_runs(repo):
    procs = [
        subprocess.Popen(
            [sys.executable, str(SCRIPT), "run", "start", "--workflow", "work",
             "--repo", str(repo)],
            stdout=subprocess.PIPE, text=True,
        )
        for _ in range(8)
    ]
    ids = {json.loads(p.communicate()[0])["run_id"] for p in procs}
    assert len(ids) == 8
    assert len(list((repo / ".mash" / "runs").iterdir())) == 8


# --- lease exclusivity (R5) ------------------------------------------------


def test_only_one_process_acquires_a_contended_lease(repo):
    runs = [start_run(repo) for _ in range(6)]
    procs = [
        subprocess.Popen(
            [sys.executable, str(SCRIPT), "lease", "acquire", "--run", rid,
             "--kind", "workspace", "--key", "/srv/checkout", "--repo", str(repo)],
            stdout=subprocess.PIPE, text=True,
        )
        for rid in runs
    ]
    results = [json.loads(p.communicate()[0]) for p in procs]
    acquired = [r for r in results if r["status"] == "acquired"]
    blocked = [r for r in results if r["status"] == "blocked"]
    assert len(acquired) == 1
    assert len(blocked) == 5
    assert all(b["holder"]["run_id"] == acquired[0]["run_id"] for b in blocked)


def test_blocked_acquire_exits_two_and_names_recovery(repo):
    first, second = start_run(repo), start_run(repo)
    cli("lease", "acquire", "--run", first, "--kind", "workspace", "--key", "w", repo=repo)
    code, payload = cli("lease", "acquire", "--run", second, "--kind", "workspace",
                        "--key", "w", repo=repo)
    assert code == 2
    assert payload["status"] == "blocked"
    assert payload["holder"]["run_id"] == first
    assert payload["holder"]["pid"] > 0
    assert payload["recovery"]


def test_reacquire_by_same_run_is_idempotent(repo):
    run_id = start_run(repo)
    first = ws.acquire_lease(repo, run_id, "workspace", "w")
    second = ws.acquire_lease(repo, run_id, "workspace", "w")
    assert first["status"] == "acquired"
    assert second["status"] == "held"


# --- ownership on release (R7) ---------------------------------------------


def test_release_by_non_owner_is_refused_and_lease_survives(repo):
    owner, other = start_run(repo), start_run(repo)
    ws.acquire_lease(repo, owner, "workspace", "w")
    code, payload = cli("lease", "release", "--run", other, "--kind", "workspace",
                        "--key", "w", repo=repo)
    assert code == 2
    assert payload["status"] == "blocked"
    assert ws.read_lease(repo, "workspace", "w")["run_id"] == owner


def test_release_by_owner_frees_the_lease(repo):
    owner, other = start_run(repo), start_run(repo)
    ws.acquire_lease(repo, owner, "workspace", "w")
    assert ws.release_lease(repo, owner, "workspace", "w")["status"] == "released"
    assert ws.acquire_lease(repo, other, "workspace", "w")["status"] == "acquired"


def test_release_of_absent_lease_is_idempotent(repo):
    run_id = start_run(repo)
    assert ws.release_lease(repo, run_id, "workspace", "w")["status"] == "absent"


# --- stale reclaim (R20) ---------------------------------------------------


def _write_lease(repo, **overrides):
    record = {
        "run_id": "ghost", "kind": "workspace", "key": "w",
        "pid": 999999, "host": ws.hostname(), "agent": "test",
        "acquired_at": "2000-01-01T00:00:00Z", "heartbeat": "2000-01-01T00:00:00Z",
    }
    record.update(overrides)
    path = ws.lease_path(repo, record["kind"], record["key"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record))
    return record


def test_dead_owner_past_stale_window_is_reclaimed(repo):
    _write_lease(repo)
    run_id = start_run(repo)
    result = ws.acquire_lease(repo, run_id, "workspace", "w")
    assert result["status"] == "acquired"
    assert result["reclaimed_from"]["run_id"] == "ghost"


# Contention raises rather than returning a status, so a caller that forgets to
# inspect the result cannot proceed as though it holds the lease.


def test_live_owner_is_never_reclaimed(repo):
    _write_lease(repo, pid=os.getpid(), heartbeat="2000-01-01T00:00:00Z")
    run_id = start_run(repo)
    with pytest.raises(ws.Blocked) as caught:
        ws.acquire_lease(repo, run_id, "workspace", "w")
    assert "still alive" in caught.value.payload["blocker"]
    assert caught.value.payload["holder"]["run_id"] == "ghost"


def test_dead_owner_inside_stale_window_is_not_reclaimed(repo):
    _write_lease(repo, heartbeat=ws.utc_now_iso())
    run_id = start_run(repo)
    with pytest.raises(ws.Blocked) as caught:
        ws.acquire_lease(repo, run_id, "workspace", "w")
    assert "heartbeat" in caught.value.payload["blocker"]


def test_foreign_host_owner_is_never_reclaimed(repo):
    _write_lease(repo, host="another-machine.invalid")
    run_id = start_run(repo)
    with pytest.raises(ws.Blocked) as caught:
        ws.acquire_lease(repo, run_id, "workspace", "w")
    assert "another host" in caught.value.payload["blocker"]


# --- run end (R7, R17) -----------------------------------------------------


def test_run_end_releases_only_its_own_leases(repo):
    mine, theirs = start_run(repo), start_run(repo)
    ws.acquire_lease(repo, mine, "workspace", "mine")
    ws.acquire_lease(repo, mine, "port", "3000")
    ws.acquire_lease(repo, theirs, "workspace", "theirs")

    code, payload = cli("run", "end", "--run", mine, repo=repo)
    assert code == 0
    assert sorted(payload["released"]) == ["port:3000", "workspace:mine"]
    assert ws.read_lease(repo, "workspace", "mine") is None
    assert ws.read_lease(repo, "port", "3000") is None
    assert ws.read_lease(repo, "workspace", "theirs")["run_id"] == theirs
    assert json.loads((repo / ".mash" / "runs" / mine / "run.json").read_text())["status"] == "finished"


def test_heartbeat_advances_lease_and_run_records(repo):
    run_id = start_run(repo)
    ws.acquire_lease(repo, run_id, "workspace", "w")
    before = ws.read_lease(repo, "workspace", "w")["heartbeat"]
    ws.heartbeat(repo, run_id, now="2099-01-01T00:00:00Z")
    assert ws.read_lease(repo, "workspace", "w")["heartbeat"] == "2099-01-01T00:00:00Z"
    assert before != "2099-01-01T00:00:00Z"


# --- key handling ----------------------------------------------------------


def test_distinct_keys_never_share_a_lease_file(repo):
    a, b = start_run(repo), start_run(repo)
    assert ws.acquire_lease(repo, a, "workspace", "/srv/one")["status"] == "acquired"
    assert ws.acquire_lease(repo, b, "workspace", "/srv/two")["status"] == "acquired"


def test_keys_differing_only_in_punctuation_do_not_collide(repo):
    a, b = start_run(repo), start_run(repo)
    assert ws.acquire_lease(repo, a, "workspace", "a/b")["status"] == "acquired"
    assert ws.acquire_lease(repo, b, "workspace", "a-b")["status"] == "acquired"


def test_unknown_run_is_refused(repo):
    code, payload = cli("lease", "acquire", "--run", "does-not-exist", "--kind",
                        "workspace", "--key", "w", repo=repo)
    assert code == 2
    assert "unknown run" in payload["blocker"]
