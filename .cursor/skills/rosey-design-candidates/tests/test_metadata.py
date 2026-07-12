"""Tests for candidates metadata helpers and path layout."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from paths import (  # noqa: E402
    candidate_html_path,
    candidates_dir,
    candidates_json_path,
    source_html_path,
)


def test_path_layout(tmp_path: Path):
    slug = "pricing"
    assert candidates_dir(tmp_path, slug) == tmp_path / "rosey" / "designs" / slug / "candidates"
    assert candidate_html_path(tmp_path, slug, 2).name == "index.html"
    assert "v2" in str(candidate_html_path(tmp_path, slug, 2))
    assert source_html_path(tmp_path, slug) == (
        tmp_path / "rosey" / "designs" / slug / "source" / "index.html"
    )
    assert candidates_json_path(tmp_path, slug).name == "candidates.json"
