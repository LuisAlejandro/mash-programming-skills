"""U2 tests: atomic, grouped artifact publication (origin R9, R10).

Concurrency is exercised with real OS processes (origin R22).
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


@pytest.fixture
def run_id(repo):
    return ws.register_run(repo, workflow="plan")["run_id"]


def source(tmp_path, name, body):
    path = tmp_path / name
    path.write_text(body)
    return path


# --- single-file publication ----------------------------------------------


def test_publishes_and_records_a_receipt(repo, run_id, tmp_path):
    src = source(tmp_path, "a.md", "plan body\n")
    dest = repo / ".mash" / "plans"
    result = ws.publish_group(repo, run_id, [(src, ".md")], dest, "2026-11-03-001-feat-x-plan")

    assert result["stem"] == "2026-11-03-001-feat-x-plan"
    assert result["files"]["2026-11-03-001-feat-x-plan.md"] == "published"
    assert (dest / "2026-11-03-001-feat-x-plan.md").read_text() == "plan body\n"

    receipts = ws.load_run(repo, run_id)["receipts"]
    assert str(dest / "2026-11-03-001-feat-x-plan.md") in receipts


def test_identical_content_is_reported_unchanged_not_republished(repo, run_id, tmp_path):
    src = source(tmp_path, "a.md", "same\n")
    dest = repo / ".mash" / "plans"
    ws.publish_group(repo, run_id, [(src, ".md")], dest, "doc")
    again = ws.publish_group(repo, run_id, [(src, ".md")], dest, "doc")
    assert again["stem"] == "doc"
    assert again["files"]["doc.md"] == "unchanged"


def test_different_content_never_overwrites_and_takes_the_next_name(repo, run_id, tmp_path):
    dest = repo / ".mash" / "plans"
    dest.mkdir(parents=True)
    (dest / "doc.md").write_text("theirs\n")
    result = ws.publish_group(repo, run_id, [(source(tmp_path, "a.md", "mine\n"), ".md")], dest, "doc")
    assert result["stem"] == "doc-2"
    assert (dest / "doc.md").read_text() == "theirs\n"
    assert (dest / "doc-2.md").read_text() == "mine\n"


def test_plan_sequence_bumps_by_number(repo, run_id, tmp_path):
    dest = repo / ".mash" / "plans"
    dest.mkdir(parents=True)
    (dest / "2026-11-03-001-feat-x-plan.md").write_text("theirs\n")
    result = ws.publish_group(
        repo, run_id, [(source(tmp_path, "a.md", "mine\n"), ".md")], dest,
        "2026-11-03-001-feat-x-plan",
    )
    assert result["stem"] == "2026-11-03-002-feat-x-plan"


# --- groups ----------------------------------------------------------------


def test_group_lands_under_one_shared_stem(repo, run_id, tmp_path):
    entries = [
        (source(tmp_path, "p.md", "plan\n"), ".md"),
        (source(tmp_path, "p.topology.json", "{}\n"), ".topology.json"),
    ]
    dest = repo / ".mash" / "plans"
    result = ws.publish_group(repo, run_id, entries, dest, "plan-x")
    assert result["stem"] == "plan-x"
    assert (dest / "plan-x.md").exists()
    assert (dest / "plan-x.topology.json").exists()


def test_group_moves_together_when_one_sibling_collides(repo, run_id, tmp_path):
    dest = repo / ".mash" / "plans"
    dest.mkdir(parents=True)
    (dest / "plan-x.topology.json").write_text("someone else\n")
    entries = [
        (source(tmp_path, "p.md", "plan\n"), ".md"),
        (source(tmp_path, "p.topology.json", "{}\n"), ".topology.json"),
    ]
    result = ws.publish_group(repo, run_id, entries, dest, "plan-x")
    assert result["stem"] == "plan-x-2"
    # The main document must not be stranded under the original stem.
    assert not (dest / "plan-x.md").exists()
    assert (dest / "plan-x-2.md").read_text() == "plan\n"
    assert (dest / "plan-x-2.topology.json").read_text() == "{}\n"
    assert (dest / "plan-x.topology.json").read_text() == "someone else\n"


def test_no_temporary_files_are_left_behind(repo, run_id, tmp_path):
    dest = repo / ".mash" / "plans"
    ws.publish_group(repo, run_id, [(source(tmp_path, "a.md", "x\n"), ".md")], dest, "doc")
    assert [p.name for p in dest.iterdir()] == ["doc.md"]


# --- concurrency -----------------------------------------------------------


def test_concurrent_publishers_never_overwrite_each_other(repo, tmp_path):
    """Each writer's content must survive, under a name only it owns."""
    dest = repo / ".mash" / "plans"
    writers = 6
    procs = []
    for index in range(writers):
        run = ws.register_run(repo, workflow="plan")["run_id"]
        src = source(tmp_path, f"src-{index}.md", f"content-{index}\n")
        procs.append(subprocess.Popen(
            [sys.executable, str(SCRIPT), "publish", "--run", run,
             "--dest-dir", str(dest), "--stem", "shared",
             "--file", f"{src}:.md", "--repo", str(repo)],
            stdout=subprocess.PIPE, text=True,
        ))
    results = [json.loads(p.communicate()[0]) for p in procs]

    stems = [r["stem"] for r in results]
    assert len(set(stems)) == writers, f"stems collided: {stems}"

    landed = sorted(p.read_text() for p in dest.iterdir())
    assert landed == sorted(f"content-{i}\n" for i in range(writers))


def test_concurrent_publishers_of_identical_content_converge(repo, tmp_path):
    """Identical content is not a conflict: it must not fan out into copies."""
    dest = repo / ".mash" / "plans"
    src = source(tmp_path, "same.md", "identical\n")
    procs = []
    for _ in range(4):
        run = ws.register_run(repo, workflow="plan")["run_id"]
        procs.append(subprocess.Popen(
            [sys.executable, str(SCRIPT), "publish", "--run", run,
             "--dest-dir", str(dest), "--stem", "same",
             "--file", f"{src}:.md", "--repo", str(repo)],
            stdout=subprocess.PIPE, text=True,
        ))
    results = [json.loads(p.communicate()[0]) for p in procs]
    assert {r["stem"] for r in results} == {"same"}
    assert [p.name for p in dest.iterdir()] == ["same.md"]


# --- failures --------------------------------------------------------------


def test_missing_source_is_refused(repo, run_id, tmp_path):
    with pytest.raises(ws.WorkspaceError, match="not a readable file"):
        ws.publish_group(repo, run_id, [(tmp_path / "ghost.md", ".md")], repo / "out", "doc")


def test_unknown_run_is_refused(repo, tmp_path):
    with pytest.raises(ws.WorkspaceError, match="unknown run"):
        ws.publish_group(repo, "nope", [(source(tmp_path, "a.md", "x"), ".md")], repo / "out", "doc")
