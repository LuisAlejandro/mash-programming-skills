"""U1 tests: feature worktree create and copy-back (KTD2, KTD3, KTD4, KTD5)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
MP_SCRIPTS = HERE.parent.parent / "mash-parallel" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(MP_SCRIPTS))

import feature_worktree as fw
import mash_parallel as mp

PLAN_NAME = "2026-11-02-001-feat-widgets-plan.md"


def _git(*args, cwd):
    return subprocess.run(
        ["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def primary(tmp_path):
    repo = tmp_path / "primary"
    repo.mkdir()
    _git("init", "-q", cwd=repo)
    _git("config", "user.email", "t@t", cwd=repo)
    _git("config", "user.name", "t", cwd=repo)
    (repo / "base.txt").write_text("base\n")
    (repo / ".gitignore").write_text(".mash/\n")
    _git("add", "base.txt", ".gitignore", cwd=repo)
    _git("commit", "-qm", "init", "--no-gpg-sign", cwd=repo)
    (repo / "AGENTS.md").write_text("conventions\n")
    return repo


def _create(primary, slug="widgets"):
    return fw.create(fw.primary_checkout(primary), slug)


def test_allowlist_matches_mash_parallel():
    assert fw.RUNTIME_FILE_ALLOWLIST == mp.RUNTIME_FILE_ALLOWLIST


def test_create_makes_worktree_on_feature_branch_and_copies_runtime(primary):
    out = _create(primary)
    wt = Path(out["worktree"])
    assert out["status"] == "created"
    assert wt == primary / ".mash" / "worktrees" / "widgets"
    assert _git("rev-parse", "--abbrev-ref", "HEAD", cwd=wt) == "feature/widgets"
    assert (wt / "AGENTS.md").read_text() == "conventions\n"
    assert "AGENTS.md" in out["copied"]


def test_create_reuses_existing_worktree_on_same_branch(primary):
    _create(primary)
    out = _create(primary)
    assert out["status"] == "reused"


def test_create_refuses_branch_without_worktree(primary):
    _git("branch", "feature/widgets", cwd=primary)
    with pytest.raises(fw.FeatureWorktreeError, match="already exists"):
        _create(primary)


def test_create_refuses_path_on_other_branch(primary):
    _create(primary)
    _git("worktree", "remove", "--force", str(primary / ".mash" / "worktrees" / "widgets"), cwd=primary)
    (primary / ".mash" / "worktrees" / "widgets").mkdir(parents=True)
    with pytest.raises(fw.FeatureWorktreeError, match="not a worktree"):
        _create(primary)


def test_create_rejects_bad_slug(primary):
    with pytest.raises(fw.FeatureWorktreeError, match="invalid slug"):
        _create(primary, slug="Bad Slug")


def _seed_worktree_artifacts(wt: Path):
    (wt / ".mash" / "brainstorms").mkdir(parents=True)
    (wt / ".mash" / "brainstorms" / "2026-11-02-widgets-requirements.md").write_text("# req\n")
    (wt / ".mash" / "brainstorms" / "scratch" / "abc").mkdir(parents=True)
    (wt / ".mash" / "brainstorms" / "scratch" / "abc" / "grounding.md").write_text("dossier\n")
    (wt / ".mash" / "plans").mkdir(parents=True)
    (wt / ".mash" / "plans" / PLAN_NAME).write_text("---\ntitle: x\n---\n")
    stem = PLAN_NAME[: -len(".md")]
    (wt / ".mash" / "plans" / f"{stem}.topology.json").write_text("{}\n")
    (wt / ".mash" / "plans" / f"{stem}.sentrux-review-brief.json").write_text("{\"ok\":true}\n")


def test_copy_back_moves_requirements_and_plan_group(primary):
    wt = Path(_create(primary)["worktree"])
    _seed_worktree_artifacts(wt)
    out = fw.copy_back(wt, f".mash/plans/{PLAN_NAME}")
    assert out["status"] == "ok"
    main_b = primary / ".mash" / "brainstorms"
    main_p = primary / ".mash" / "plans"
    assert (main_b / "2026-11-02-widgets-requirements.md").read_text() == "# req\n"
    assert (main_p / PLAN_NAME).exists()
    stem = PLAN_NAME[: -len(".md")]
    assert (main_p / f"{stem}.topology.json").exists()
    assert (main_p / f"{stem}.sentrux-review-brief.json").exists()
    # scratch dossiers are not flat requirements and must not travel
    assert not (main_b / "scratch").exists()


def test_copy_back_is_idempotent(primary):
    wt = Path(_create(primary)["worktree"])
    _seed_worktree_artifacts(wt)
    fw.copy_back(wt, f".mash/plans/{PLAN_NAME}")
    again = fw.copy_back(wt, f".mash/plans/{PLAN_NAME}")
    statuses = {f: s for r in again["results"] for f, s in r["files"].items()}
    assert set(statuses.values()) == {"unchanged"}
    assert not list((primary / ".mash" / "plans").glob("*-002-*"))


def test_copy_back_never_overwrites_different_content(primary):
    wt = Path(_create(primary)["worktree"])
    _seed_worktree_artifacts(wt)
    main_p = primary / ".mash" / "plans"
    main_p.mkdir(parents=True)
    (main_p / PLAN_NAME).write_text("user edited, keep me\n")
    out = fw.copy_back(wt, f".mash/plans/{PLAN_NAME}")
    assert (main_p / PLAN_NAME).read_text() == "user edited, keep me\n"
    bumped = "2026-11-02-002-feat-widgets-plan"
    assert (main_p / f"{bumped}.md").exists()
    # siblings move together under the bumped stem, never under the old one
    assert (main_p / f"{bumped}.topology.json").exists()
    assert (main_p / f"{bumped}.sentrux-review-brief.json").exists()
    plan_result = next(r for r in out["results"] if r["kind"] == "plan")
    assert plan_result["stem"] == bumped


def test_copy_back_from_primary_is_noop(primary):
    out = fw.copy_back(primary, None)
    assert out["status"] == "noop"


def test_copy_back_rejects_plan_outside_plans_dir(primary):
    wt = Path(_create(primary)["worktree"])
    (wt / "README.md").write_text("x\n")
    with pytest.raises(fw.FeatureWorktreeError, match="not a file under .mash/plans"):
        fw.copy_back(wt, "README.md")


def test_cli_reports_blocker_as_json(primary, monkeypatch, capsys):
    monkeypatch.chdir(primary)
    assert fw.main(["create", "Bad Slug"]) == 2
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "blocked"
