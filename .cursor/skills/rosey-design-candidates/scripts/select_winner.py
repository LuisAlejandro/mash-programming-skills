#!/usr/bin/env python3
"""Copy a winning candidate variation into rosey/designs/<slug>/source/."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path

from paths import (
    NUM_VARIATIONS,
    candidate_html_path,
    candidate_preview_path,
    candidates_json_path,
    rel_to_repo,
    source_dir,
    source_html_path,
    source_preview_path,
)

logger = logging.getLogger("select_winner")


def select_winner(
    repo_root: Path,
    page_slug: str,
    variation: int,
) -> dict:
    n = int(variation)
    if n < 1 or n > NUM_VARIATIONS:
        raise ValueError(f"variation must be 1..{NUM_VARIATIONS}, got {variation}")

    html_src = candidate_html_path(repo_root, page_slug, n)
    if not html_src.is_file():
        raise FileNotFoundError(f"Missing candidate HTML: {html_src}")

    dest_dir = source_dir(repo_root, page_slug)
    dest_dir.mkdir(parents=True, exist_ok=True)
    html_dest = source_html_path(repo_root, page_slug)
    shutil.copy2(html_src, html_dest)

    png_src = candidate_preview_path(repo_root, page_slug, n)
    png_dest = None
    if png_src.is_file():
        png_dest = source_preview_path(repo_root, page_slug)
        shutil.copy2(png_src, png_dest)

    meta_path = candidates_json_path(repo_root, page_slug)
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["winnerVariation"] = n
        meta["sourceHtml"] = rel_to_repo(repo_root, html_dest)
        if png_dest:
            meta["sourcePreview"] = rel_to_repo(repo_root, png_dest)
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return {
        "variation": n,
        "html": html_dest,
        "png": png_dest,
        "candidates_json": meta_path if meta_path.is_file() else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Select design candidate winner")
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--page-slug", required=True)
    parser.add_argument("--variation", required=True, type=int)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    repo_root = args.repo_root.resolve()
    try:
        result = select_winner(repo_root, args.page_slug, args.variation)
    except Exception as exc:
        logger.error("%s", exc)
        return 1

    print(f"WINNER_VARIATION={result['variation']}")
    print(f"SOURCE_HTML={result['html']}")
    if result.get("png"):
        print(f"SOURCE_PNG={result['png']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
