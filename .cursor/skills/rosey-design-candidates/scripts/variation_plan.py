"""Variation plan validation and fallbacks for rosey-design-candidates."""

from __future__ import annotations

import json
import re
from typing import Any

from paths import NUM_VARIATIONS

MAX_VARIATION_DIRECTIVE_CHARS = 2000

VARIATION_DIRECTIVE_SUFFIX = (
    "Stay on one polished screen. Output a single self-contained index.html. "
    "Respect the attached design system. No lorem ipsum."
)


def extract_json_object(text: str) -> dict | None:
    """Parse JSON from planner text, tolerating markdown fences."""
    raw = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL | re.IGNORECASE)
    if fenced:
        raw = fenced.group(1).strip()
    else:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            raw = raw[start : end + 1]
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def normalize_variation_item(item: object) -> dict | None:
    if not isinstance(item, dict):
        return None
    title = str(item.get("title", "")).strip()
    directive = str(item.get("directive", "")).strip()
    rationale = str(item.get("rationale", "")).strip()
    if not title or not directive:
        return None
    if len(directive) > MAX_VARIATION_DIRECTIVE_CHARS:
        directive = directive[:MAX_VARIATION_DIRECTIVE_CHARS].rstrip() + "..."
    if not rationale:
        rationale = "Explores an alternative composition or hierarchy for the brief."
    return {"title": title, "directive": directive, "rationale": rationale}


def validate_variation_plan(data: dict[str, Any]) -> dict | None:
    """Return normalized plan dict if valid, else None."""
    variations_raw = data.get("variations")
    if not isinstance(variations_raw, list) or len(variations_raw) != NUM_VARIATIONS:
        return None
    variations = []
    for item in variations_raw:
        normalized = normalize_variation_item(item)
        if not normalized:
            return None
        variations.append(normalized)
    surface = str(data.get("surface", "unknown")).strip() or "unknown"
    source = str(data.get("source", "planner")).strip() or "planner"
    return {
        "source": source,
        "surface": surface,
        "plannerAgent": data.get("plannerAgent"),
        "plannerModel": data.get("plannerModel"),
        "variations": variations,
    }


def load_and_validate_variation_plan(path: Any) -> dict:
    """Load JSON from path and validate; raise ValueError if invalid."""
    from pathlib import Path

    text = Path(path).read_text(encoding="utf-8")
    parsed = extract_json_object(text)
    if not parsed:
        raise ValueError(f"Could not parse variation plan JSON: {path}")
    validated = validate_variation_plan(parsed)
    if not validated:
        raise ValueError(
            f"Variation plan must have exactly {NUM_VARIATIONS} variations "
            f"with title and directive: {path}"
        )
    return validated


def fallback_variation_plan(brief: str) -> dict:
    excerpt = " ".join(brief.strip().split())[:280]
    return {
        "source": "fallback",
        "surface": "unknown",
        "plannerAgent": None,
        "plannerModel": None,
        "variations": [
            {
                "title": "Direct",
                "directive": (
                    f"Variation strategy: Direct, conservative interpretation of the brief.\n"
                    f"Brief context: {excerpt}\n\n"
                    f"Deliver a clear, balanced layout that satisfies the request literally. "
                    f"{VARIATION_DIRECTIVE_SUFFIX}"
                ),
                "rationale": "Baseline reading of the brief with minimal compositional risk.",
            },
            {
                "title": "Strong Hierarchy",
                "directive": (
                    f"Variation strategy: Stronger visual hierarchy and bolder composition.\n"
                    f"Brief context: {excerpt}\n\n"
                    f"Emphasize primary actions, headline structure, and scan path. "
                    f"{VARIATION_DIRECTIVE_SUFFIX}"
                ),
                "rationale": "Explores emphasis, contrast, and information priority.",
            },
            {
                "title": "Dense Interactive",
                "directive": (
                    f"Variation strategy: Denser, more data-forward or interactive composition.\n"
                    f"Brief context: {excerpt}\n\n"
                    f"Use tighter spacing, richer UI modules, and a more operational feel where appropriate. "
                    f"{VARIATION_DIRECTIVE_SUFFIX}"
                ),
                "rationale": "Explores density, utility, and power-user scan patterns.",
            },
        ],
    }
