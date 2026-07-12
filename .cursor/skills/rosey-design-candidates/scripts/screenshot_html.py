"""Playwright screenshot helper for exported OpenDesign HTML."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def screenshot_html(
    html_path: Path,
    png_path: Path,
    width: int = 1920,
    height: int = 1080,
) -> None:
    from playwright.sync_api import sync_playwright

    png_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(f"file://{html_path.resolve()}")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(png_path), full_page=True)
        browser.close()
    logger.info("Screenshot saved: %s", png_path)
