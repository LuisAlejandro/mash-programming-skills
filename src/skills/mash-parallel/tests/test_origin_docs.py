"""Task origin resolution: only real brainstorm docs, never a fabrication.

C5: mash-plan requires an upstream requirements document and stops without one
(its 0.3b missing-origin gate). mash-parallel used to project a synthetic
`*-requirements.md` from each task goal so planning could proceed. That
laundered unvalidated scope past the very gate that exists to prevent inventing
product scope at plan time, so the projection is gone.
"""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import mash_parallel as rp  # noqa: E402


def test_slug_normalizes_task_id():
    assert rp.task_origin_slug("Auth Flow") == "auth-flow"
    assert rp.task_origin_slug("t1") == "t1"


def test_no_brainstorm_resolves_to_nothing_and_writes_nothing(tmp_path):
    tasks = {"auth": {"goal": "Add auth", "deps": []}}
    out = rp.resolve_task_origins(tmp_path, tasks)
    assert out == {}
    # No fabricated artifact anywhere on disk.
    assert not (tmp_path / ".mash" / "parallel" / "origins").exists()


def test_existing_brainstorm_wins_exact_slug(tmp_path):
    brainstorms = tmp_path / ".mash" / "brainstorms"
    brainstorms.mkdir(parents=True)
    (brainstorms / "auth-requirements.md").write_text("# real brainstorm\n")
    tasks = {"auth": {"goal": "Add auth", "deps": []}}
    out = rp.resolve_task_origins(tmp_path, tasks)
    assert out == {"auth": ".mash/brainstorms/auth-requirements.md"}


def test_existing_brainstorm_wins_dated_slug(tmp_path):
    brainstorms = tmp_path / ".mash" / "brainstorms"
    brainstorms.mkdir(parents=True)
    (brainstorms / "2026-01-15-auth-requirements.md").write_text(
        "# dated brainstorm\n"
    )
    tasks = {"auth": {"goal": "Add auth", "deps": []}}
    out = rp.resolve_task_origins(tmp_path, tasks)
    assert out == {"auth": ".mash/brainstorms/2026-01-15-auth-requirements.md"}


def test_scratch_is_not_a_search_root(tmp_path):
    scratch = tmp_path / ".mash" / "brainstorms" / "scratch"
    scratch.mkdir(parents=True)
    (scratch / "auth-requirements.md").write_text("# scout junk\n")
    tasks = {"auth": {"goal": "Add auth", "deps": []}}
    assert rp.resolve_task_origins(tmp_path, tasks) == {}


def test_only_matching_tasks_resolve(tmp_path):
    brainstorms = tmp_path / ".mash" / "brainstorms"
    brainstorms.mkdir(parents=True)
    (brainstorms / "auth-requirements.md").write_text("# real\n")
    tasks = {
        "auth": {"goal": "Add auth", "deps": []},
        "billing": {"goal": "Add billing", "deps": []},
    }
    out = rp.resolve_task_origins(tmp_path, tasks)
    assert out == {"auth": ".mash/brainstorms/auth-requirements.md"}


def test_projection_helper_is_gone():
    # The fabrication path must not come back under a new name.
    assert not hasattr(rp, "write_task_origin_docs")
    assert not hasattr(rp, "task_origin_doc_path")
