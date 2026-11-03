"""U5 tests: parallel run identity and owner-checked resume (origin R14, R15)."""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS.parent.parent / "mash-workspace" / "scripts"))

import mash_parallel as rp
import workspace as ws


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for key, value in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(root), "config", key, value], check=True)
    (root / "base.txt").write_text("base\n")
    subprocess.run(["git", "-C", str(root), "add", "base.txt"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "init", "--no-gpg-sign"], check=True)
    return root


# --- identity (R14) --------------------------------------------------------


def test_run_ids_are_unique_within_the_same_second(repo):
    """The reproduced hazard: a one-second timestamp aliased two runs."""
    ids = [rp.new_run_id() for _ in range(200)]
    assert len(set(ids)) == len(ids)


def test_run_ids_group_chronologically(repo):
    """Uniqueness comes from entropy, so only the timestamp prefix orders runs."""
    prefixes = [rp.new_run_id()[:15] for _ in range(5)]
    assert prefixes == sorted(prefixes)
    assert all(len(p) == 15 and p[8] == "-" for p in prefixes)


def test_run_id_is_filesystem_safe(repo):
    for run_id in (rp.new_run_id() for _ in range(20)):
        assert "/" not in run_id and ".." not in run_id
        assert rp.run_dir(repo, run_id).name == run_id


def test_two_runs_never_share_a_run_directory(repo):
    first, second = rp.new_run_id(), rp.new_run_id()
    assert rp.run_dir(repo, first) != rp.run_dir(repo, second)


# --- owner-checked resume (R15) --------------------------------------------


def test_claiming_a_run_registers_an_owner(repo):
    run_id = rp.new_run_id()
    rp.claim_run(repo, run_id)
    assert ws.read_lease(repo, "run", run_id)["run_id"] == run_id


CLAIM_IN_SUBPROCESS = """
import json, sys
sys.path[:0] = [{scripts!r}, {ws_scripts!r}]
import mash_parallel as rp, workspace as ws
try:
    print(json.dumps(rp.claim_run({repo!r}, {run_id!r})))
except ws.Blocked as exc:
    print(json.dumps(exc.payload))
    sys.exit(2)
"""


def claim_elsewhere(repo, run_id, keep_alive=False):
    """Claim the run from a real second process."""
    code = CLAIM_IN_SUBPROCESS.format(
        scripts=str(SCRIPTS), ws_scripts=str(SCRIPTS.parent.parent / "mash-workspace" / "scripts"),
        repo=str(repo), run_id=run_id,
    )
    if keep_alive:
        code += "import time; time.sleep(30)\n"
        return subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)


def test_a_live_run_cannot_be_resumed_by_another_process(repo):
    """The reproduced hazard: two orchestrators drove one run directory."""
    run_id = rp.new_run_id()
    rp.claim_run(repo, run_id)
    result = claim_elsewhere(repo, run_id)
    assert result.returncode == 2, result.stdout
    assert "blocked" in result.stdout


def test_a_released_run_can_be_resumed(repo):
    run_id = rp.new_run_id()
    rp.claim_run(repo, run_id)
    rp.release_run(repo, run_id)
    assert claim_elsewhere(repo, run_id).returncode == 0


def test_resuming_an_abandoned_run_succeeds(repo):
    """A dead owner must not strand the run forever."""
    run_id = rp.new_run_id()
    holder = claim_elsewhere(repo, run_id, keep_alive=True)
    try:
        holder.stdout.readline()  # wait until the claim has landed
    finally:
        holder.kill()
        holder.wait(timeout=10)
    # The owner is gone; past the stale window the run is reclaimable.
    assert rp.claim_run(repo, run_id, stale_window_s=0)["status"] == "claimed"
