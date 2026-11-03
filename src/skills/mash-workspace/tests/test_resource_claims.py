"""U8 tests: exclusive claims on shared machine resources (origin R20, R21).

Ports, Compose projects, databases, browser profiles and the release pipeline
are machine-wide. Two runs using one of them silently corrupt each other.
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


# --- exclusivity -----------------------------------------------------------


@pytest.mark.parametrize("kind,key", [
    ("port", "3000"),
    ("compose", "myapp-dev"),
    ("db", "postgres://localhost/app_test"),
    ("browser", "agent-browser:default"),
    ("release", "mash-programming-skills"),
])
def test_a_claimed_resource_is_refused_to_a_second_run(repo, kind, key):
    ws.acquire_lease(repo, start(repo), kind, key)
    with pytest.raises(ws.Blocked) as excinfo:
        ws.acquire_lease(repo, start(repo), kind, key)
    assert key in str(excinfo.value)


def test_different_keys_of_the_same_kind_do_not_contend(repo):
    ws.acquire_lease(repo, start(repo), "port", "3000")
    assert ws.acquire_lease(repo, start(repo), "port", "3001")["status"] == "acquired"


def test_releasing_frees_the_resource_for_the_next_run(repo):
    first = start(repo)
    ws.acquire_lease(repo, first, "port", "8080")
    ws.release_lease(repo, first, "port", "8080")
    assert ws.acquire_lease(repo, start(repo), "port", "8080")["status"] == "acquired"


def test_ending_a_run_frees_everything_it_claimed(repo):
    """A finished run must not strand the machine's ports behind it."""
    run_id = start(repo)
    for key in ("5432", "6379"):
        ws.acquire_lease(repo, run_id, "port", key)
    ws.end_run(repo, run_id)
    for key in ("5432", "6379"):
        assert ws.read_lease(repo, "port", key) is None


def test_an_unknown_resource_kind_is_rejected(repo):
    with pytest.raises(ws.WorkspaceError, match="unknown lease kind"):
        ws.acquire_lease(repo, start(repo), "gpu", "0")


# --- blocker quality (R21) -------------------------------------------------


def test_a_refusal_names_the_holder_and_a_way_forward(repo):
    holder = start(repo)
    ws.acquire_lease(repo, holder, "port", "3000")
    try:
        ws.acquire_lease(repo, start(repo), "port", "3000")
    except ws.Blocked as blocked:
        payload = blocked.payload
    assert payload["holder"]["run_id"] == holder
    assert payload["holder"]["pid"] == __import__("os").getpid()
    assert payload["recovery"], "a blocker must say what to do next"
    assert "3000" in payload["blocker"]


def test_cli_refusal_exits_two_with_a_json_blocker(repo):
    ws.acquire_lease(repo, start(repo), "port", "3000")
    other = start(repo)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "lease", "acquire", "--run", other,
         "--kind", "port", "--key", "3000", "--repo", str(repo)],
        capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["status"] == "blocked"
    assert payload["kind"] == "port"


# --- concurrency -----------------------------------------------------------


def test_only_one_of_many_racing_processes_claims_a_port(repo):
    runs = [start(repo) for _ in range(8)]
    procs = [
        subprocess.Popen(
            [sys.executable, str(SCRIPT), "lease", "acquire", "--run", run_id,
             "--kind", "port", "--key", "4000", "--repo", str(repo)],
            stdout=subprocess.PIPE, text=True,
        )
        for run_id in runs
    ]
    outcomes = [json.loads(p.communicate()[0]) for p in procs]
    acquired = [o for o in outcomes if o.get("status") == "acquired"]
    blocked = [o for o in outcomes if o.get("status") == "blocked"]
    assert len(acquired) == 1, f"{len(acquired)} runs think they own port 4000"
    assert len(blocked) == len(runs) - 1
    assert ws.read_lease(repo, "port", "4000")["run_id"] == acquired[0]["run_id"]
