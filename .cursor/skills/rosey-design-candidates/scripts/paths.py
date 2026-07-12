"""Repo-local path helpers mirroring rosey-paths.js candidates/source layout."""

from __future__ import annotations

from pathlib import Path

DESIGNS_DIR = Path("rosey") / "designs"
NUM_VARIATIONS = 3


def designs_root(repo_root: Path) -> Path:
    return repo_root / DESIGNS_DIR


def design_system_manifest_path(repo_root: Path) -> Path:
    return designs_root(repo_root) / "design-system.json"


def design_system_design_md(repo_root: Path) -> Path:
    return repo_root / "rosey" / "design-system" / "DESIGN.md"


def page_dir(repo_root: Path, page_slug: str) -> Path:
    return designs_root(repo_root) / page_slug


def candidates_dir(repo_root: Path, page_slug: str) -> Path:
    return page_dir(repo_root, page_slug) / "candidates"


def candidates_json_path(repo_root: Path, page_slug: str) -> Path:
    return candidates_dir(repo_root, page_slug) / "candidates.json"


def variation_plan_path(repo_root: Path, page_slug: str) -> Path:
    return candidates_dir(repo_root, page_slug) / "variation-plan.json"


def candidate_variation_dir(repo_root: Path, page_slug: str, variation: int) -> Path:
    n = int(variation)
    if n < 1:
        raise ValueError(f"Invalid variation number: {variation}")
    return candidates_dir(repo_root, page_slug) / f"v{n}"


def candidate_html_path(repo_root: Path, page_slug: str, variation: int) -> Path:
    return candidate_variation_dir(repo_root, page_slug, variation) / "index.html"


def candidate_preview_path(repo_root: Path, page_slug: str, variation: int) -> Path:
    return candidate_variation_dir(repo_root, page_slug, variation) / "preview.png"


def candidate_project_meta_path(repo_root: Path, page_slug: str, variation: int) -> Path:
    return candidate_variation_dir(repo_root, page_slug, variation) / "project-meta.json"


def source_dir(repo_root: Path, page_slug: str) -> Path:
    return page_dir(repo_root, page_slug) / "source"


def source_html_path(repo_root: Path, page_slug: str) -> Path:
    return source_dir(repo_root, page_slug) / "index.html"


def source_preview_path(repo_root: Path, page_slug: str) -> Path:
    return source_dir(repo_root, page_slug) / "preview.png"


def rel_to_repo(repo_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)
