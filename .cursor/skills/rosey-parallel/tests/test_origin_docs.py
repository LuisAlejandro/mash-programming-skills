"""Origin projection path shape and existing-brainstorm wins."""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import rosey_parallel as rp  # noqa: E402


def test_projected_path_is_under_parallel_origins():
    assert (
        rp.task_origin_doc_path("Auth Flow")
        == "rosey/parallel/origins/auth-flow-requirements.md"
    )


def test_write_projects_when_no_brainstorm(tmp_path):
    tasks = {"auth": {"goal": "Add auth", "deps": []}}
    out = rp.write_task_origin_docs(tmp_path, tasks)
    rel = "rosey/parallel/origins/auth-requirements.md"
    assert out == {"auth": rel}
    dest = tmp_path / rel
    assert dest.is_file()
    assert "Add auth" in dest.read_text()
    brainstorms = tmp_path / "rosey" / "brainstorms"
    assert not brainstorms.exists() or not list(brainstorms.glob("*-requirements.md"))


def test_existing_brainstorm_wins_exact_slug(tmp_path):
    brainstorms = tmp_path / "rosey" / "brainstorms"
    brainstorms.mkdir(parents=True)
    (brainstorms / "auth-requirements.md").write_text("# real brainstorm\n")
    tasks = {"auth": {"goal": "Add auth", "deps": []}}
    out = rp.write_task_origin_docs(tmp_path, tasks)
    assert out == {"auth": "rosey/brainstorms/auth-requirements.md"}
    projected = tmp_path / "rosey/parallel/origins/auth-requirements.md"
    assert not projected.exists()


def test_existing_brainstorm_wins_dated_slug(tmp_path):
    brainstorms = tmp_path / "rosey" / "brainstorms"
    brainstorms.mkdir(parents=True)
    (brainstorms / "2026-01-15-auth-requirements.md").write_text(
        "# dated brainstorm\n"
    )
    tasks = {"auth": {"goal": "Add auth", "deps": []}}
    out = rp.write_task_origin_docs(tmp_path, tasks)
    assert out == {"auth": "rosey/brainstorms/2026-01-15-auth-requirements.md"}
    assert not (tmp_path / "rosey/parallel/origins/auth-requirements.md").exists()


def test_does_not_overwrite_existing_projection(tmp_path):
    rel = "rosey/parallel/origins/auth-requirements.md"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True)
    dest.write_text("# keep me\n")
    tasks = {"auth": {"goal": "Add auth", "deps": []}}
    out = rp.write_task_origin_docs(tmp_path, tasks)
    assert out == {"auth": rel}
    assert dest.read_text() == "# keep me\n"


def test_scratch_is_not_a_search_root(tmp_path):
    scratch = tmp_path / "rosey" / "brainstorms" / "scratch"
    scratch.mkdir(parents=True)
    (scratch / "auth-requirements.md").write_text("# scout junk\n")
    tasks = {"auth": {"goal": "Add auth", "deps": []}}
    out = rp.write_task_origin_docs(tmp_path, tasks)
    assert out == {"auth": "rosey/parallel/origins/auth-requirements.md"}
