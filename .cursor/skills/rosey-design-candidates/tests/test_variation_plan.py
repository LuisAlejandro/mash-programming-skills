"""Tests for variation plan validation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from variation_plan import (  # noqa: E402
    extract_json_object,
    fallback_variation_plan,
    load_and_validate_variation_plan,
    validate_variation_plan,
)

FIXTURE = SCRIPTS / "fixtures" / "variation-plan.json"


def test_fixture_plan_validates():
    plan = load_and_validate_variation_plan(FIXTURE)
    assert len(plan["variations"]) == 3
    assert plan["variations"][0]["title"] == "Direct"


def test_extract_json_from_fenced_block():
    text = 'Here you go:\n```json\n{"surface": "x", "variations": []}\n```\n'
    data = extract_json_object(text)
    assert data["surface"] == "x"


def test_validate_rejects_wrong_count():
    assert validate_variation_plan({"variations": [{"title": "a", "directive": "b"}]}) is None


def test_validate_rejects_missing_directive():
    data = {
        "variations": [
            {"title": "a", "directive": "d1"},
            {"title": "b", "directive": "d2"},
            {"title": "c"},
        ]
    }
    assert validate_variation_plan(data) is None


def test_fallback_has_three_variations():
    plan = fallback_variation_plan("Build a pricing page")
    assert plan["source"] == "fallback"
    assert len(plan["variations"]) == 3
    assert all(v["directive"] for v in plan["variations"])
