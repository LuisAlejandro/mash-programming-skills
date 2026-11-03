"""U4 tests: integration ownership and base fidelity (origin R11, R12, R13)."""

import subprocess
import sys
import threading
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import mash_parallel as rp


def git(repo, *args, check=True):
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=check).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@t")
    git(root, "config", "user.name", "t")
    (root / "base.txt").write_text("base\n")
    git(root, "add", "base.txt")
    git(root, "commit", "-qm", "init", "--no-gpg-sign")
    git(root, "branch", "develop")
    for name in ("a", "b"):
        git(root, "switch", "-qc", f"track/{name}", "develop")
        (root / f"{name}.txt").write_text(f"{name}\n")
        git(root, "add", f"{name}.txt")
        git(root, "commit", "-qm", f"track {name}", "--no-gpg-sign")
    git(root, "switch", "-q", "main")
    return root


def ok_gate(_tree):
    return True, []


# --- run-owned integration workspace (R11) ---------------------------------


def test_integration_uses_a_run_owned_path(repo):
    result = rp.integrate(repo, [{"branch": "track/a"}], "develop", ok_gate, run_id="run-one")
    assert result["status"] == "success"
    assert "run-one" in result["workspace"]


def test_a_second_run_never_deletes_the_first_runs_workspace(repo):
    """The reproduced hazard: B's cleanup removed A's live integration tree."""
    inside, proceed = threading.Event(), threading.Event()
    first_path = {}

    def slow_gate(tree):
        first_path["path"] = Path(tree)
        inside.set()
        assert proceed.wait(timeout=15)
        return True, []

    outcome = {}

    def run_first():
        outcome["first"] = rp.integrate(repo, [{"branch": "track/a"}], "develop",
                                        slow_gate, run_id="run-one")

    worker = threading.Thread(target=run_first)
    worker.start()
    try:
        assert inside.wait(timeout=10)
        assert first_path["path"].is_dir()
        second = rp.integrate(repo, [{"branch": "track/b"}], "develop", ok_gate, run_id="run-two")
        assert first_path["path"].is_dir(), "second run removed the first run's workspace"
        assert second["status"] == "success"
    finally:
        proceed.set()
        worker.join(timeout=15)
    # The first run verified an older base, so it is told to re-integrate
    # rather than overwriting the publication that landed while it worked.
    assert outcome["first"]["status"] == "fixup"
    assert "moved" in outcome["first"]["reason"]
    assert git(repo, "cat-file", "-e", "develop:b.txt", check=False) == ""


# --- base fidelity and compare-and-swap (R12) ------------------------------


def test_integration_builds_from_the_target_base_not_the_primary_head(repo):
    """The primary checkout sits on `main`; the target base is `develop`."""
    git(repo, "switch", "-q", "main")
    (repo / "unrelated.txt").write_text("only on main\n")
    git(repo, "add", "unrelated.txt")
    git(repo, "commit", "-qm", "main drifts", "--no-gpg-sign")

    result = rp.integrate(repo, [{"branch": "track/a"}], "develop", ok_gate, run_id="r1")
    assert result["status"] == "success"
    assert git(repo, "cat-file", "-e", f"{result['integrated_tip']}:unrelated.txt",
               check=False) == ""
    merged = subprocess.run(["git", "-C", str(repo), "cat-file", "-e",
                             f"{result['integrated_tip']}:unrelated.txt"],
                            capture_output=True, check=False)
    assert merged.returncode != 0, "main-only work leaked into the develop integration"


def test_sequential_integrations_keep_the_earlier_result(repo):
    """The reproduced hazard: the second publish dropped the first."""
    first = rp.integrate(repo, [{"branch": "track/a"}], "develop", ok_gate, run_id="r1")
    second = rp.integrate(repo, [{"branch": "track/b"}], "develop", ok_gate, run_id="r2")
    assert first["status"] == "success"
    assert second["status"] == "success"
    assert subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor",
         first["integrated_tip"], "develop"], check=False,
    ).returncode == 0, "the first accepted integration is no longer on develop"
    assert git(repo, "cat-file", "-e", "develop:a.txt", check=False) == ""
    assert git(repo, "cat-file", "-e", "develop:b.txt", check=False) == ""


def test_base_moving_after_verification_refuses_to_publish(repo):
    """Compare-and-swap: a base that advanced mid-run is never overwritten."""
    def gate_that_moves_the_base(_tree):
        git(repo, "switch", "-q", "develop")
        (repo / "someone-else.txt").write_text("concurrent\n")
        git(repo, "add", "someone-else.txt")
        git(repo, "commit", "-qm", "another run published", "--no-gpg-sign")
        git(repo, "switch", "-q", "main")
        return True, []

    result = rp.integrate(repo, [{"branch": "track/a"}], "develop",
                          gate_that_moves_the_base, run_id="r1")
    assert result["status"] == "fixup"
    assert "moved" in result["reason"]
    assert git(repo, "cat-file", "-e", "develop:someone-else.txt", check=False) == ""


def test_checked_out_base_moves_its_working_tree_with_the_ref(repo):
    """The reproduced hazard: develop's files no longer matched its HEAD."""
    git(repo, "switch", "-q", "develop")
    result = rp.integrate(repo, [{"branch": "track/a"}], "develop", ok_gate, run_id="r1")
    assert result["status"] == "success"
    assert git(repo, "rev-parse", "HEAD") == result["integrated_tip"]
    assert (repo / "a.txt").exists(), "the ref moved but the working tree did not"
    assert git(repo, "status", "--porcelain") == ""


def test_publication_never_overwrites_uncommitted_work_on_the_base(repo):
    """A track that touches the same file as uncommitted local work is refused."""
    git(repo, "switch", "-qc", "track/d", "develop")
    (repo / "base.txt").write_text("changed by the track\n")
    git(repo, "add", "base.txt")
    git(repo, "commit", "-qm", "track d", "--no-gpg-sign")

    git(repo, "switch", "-q", "develop")
    (repo / "base.txt").write_text("uncommitted local work\n")
    before = git(repo, "rev-parse", "develop")

    result = rp.integrate(repo, [{"branch": "track/d"}], "develop", ok_gate, run_id="r1")
    assert result["status"] == "fixup"
    assert "uncommitted" in result["reason"]
    assert git(repo, "rev-parse", "develop") == before
    assert (repo / "base.txt").read_text() == "uncommitted local work\n"


def test_an_absent_base_is_created_once(repo):
    """Creation is also a compare-and-swap: the second creator is refused."""
    first = rp.integrate(repo, [{"branch": "track/a"}], "fresh", ok_gate, run_id="r1")
    assert first["status"] == "success"
    assert git(repo, "rev-parse", "fresh") == first["integrated_tip"]

    second = rp.integrate(repo, [{"branch": "track/b"}], "fresh", ok_gate, run_id="r2")
    assert second["status"] == "success"
    assert subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor",
         first["integrated_tip"], "fresh"], check=False,
    ).returncode == 0


# --- cleanup ---------------------------------------------------------------


def test_successful_integration_cleans_up_its_own_workspace(repo):
    result = rp.integrate(repo, [{"branch": "track/a"}], "develop", ok_gate, run_id="r1")
    assert not Path(result["workspace"]).exists()


def test_conflict_aborts_without_publishing(repo):
    git(repo, "switch", "-qc", "track/c", "develop")
    (repo / "a.txt").write_text("conflicting\n")
    git(repo, "add", "a.txt")
    git(repo, "commit", "-qm", "conflict", "--no-gpg-sign")
    git(repo, "switch", "-q", "main")
    before = git(repo, "rev-parse", "develop")
    result = rp.integrate(repo, [{"branch": "track/a"}, {"branch": "track/c"}],
                          "develop", ok_gate, run_id="r1")
    assert result["status"] == "fixup"
    assert git(repo, "rev-parse", "develop") == before
