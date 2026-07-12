"""Tests for select_winner."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from select_winner import select_winner  # noqa: E402


def _seed_candidates(repo: Path, slug: str = "demo-page") -> None:
    for i in range(1, 4):
        d = repo / "rosey" / "designs" / slug / "candidates" / f"v{i}"
        d.mkdir(parents=True)
        (d / "index.html").write_text(f"<html>v{i}</html>", encoding="utf-8")
        (d / "preview.png").write_bytes(b"\x89PNG\r\n\x1a\n" + bytes([i]))
    meta = {
        "generatedAt": "2026-07-12T00:00:00",
        "pageSlug": slug,
        "brief": "test",
        "winnerVariation": None,
        "designSystem": {
            "designSystemId": "user:test",
            "designPath": "rosey/design-system/DESIGN.md",
            "checksum": "abc",
        },
        "variationPlanner": {"source": "agent", "surface": "test"},
        "variations": [
            {"variation": i, "title": f"V{i}", "html": f"rosey/designs/{slug}/candidates/v{i}/index.html"}
            for i in range(1, 4)
        ],
    }
    meta_path = repo / "rosey" / "designs" / slug / "candidates" / "candidates.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def test_select_winner_copies_html_and_png(tmp_path: Path):
    _seed_candidates(tmp_path)
    result = select_winner(tmp_path, "demo-page", 2)
    html = tmp_path / "rosey" / "designs" / "demo-page" / "source" / "index.html"
    png = tmp_path / "rosey" / "designs" / "demo-page" / "source" / "preview.png"
    assert html.read_text(encoding="utf-8") == "<html>v2</html>"
    assert png.is_file()
    assert result["variation"] == 2
    meta = json.loads(
        (tmp_path / "rosey" / "designs" / "demo-page" / "candidates" / "candidates.json").read_text()
    )
    assert meta["winnerVariation"] == 2
    assert meta["sourceHtml"].endswith("source/index.html")


def test_select_winner_rejects_missing(tmp_path: Path):
    _seed_candidates(tmp_path)
    (tmp_path / "rosey" / "designs" / "demo-page" / "candidates" / "v3" / "index.html").unlink()
    try:
        select_winner(tmp_path, "demo-page", 3)
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass
