"""Tests for OpenDesign client response parsing and mocked generate flow."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from generate_candidates import (  # noqa: E402
    generate_candidates,
    write_candidates_metadata,
)
from opendesign_client import (  # noqa: E402
    OpenDesignClient,
    parse_create_response,
    parse_run_start_response,
)
from variation_plan import load_and_validate_variation_plan  # noqa: E402

FIXTURE = SCRIPTS / "fixtures" / "variation-plan.json"


def test_parse_create_response_nested_project():
    stdout = json.dumps(
        {
            "project": {"id": "proj-1"},
            "conversation": {"id": "conv-1"},
        }
    )
    parsed = parse_create_response(stdout)
    assert parsed["project_id"] == "proj-1"
    assert parsed["conversation_id"] == "conv-1"


def test_parse_run_start_response():
    assert parse_run_start_response(json.dumps({"runId": "run-9"})) == "run-9"


def test_write_candidates_metadata(tmp_path: Path):
    design_ctx = {
        "design_system_id": "user:test-ds",
        "design_path": "rosey/design-system/DESIGN.md",
        "checksum": "deadbeef",
        "manifest": {"designSystemId": "user:test-ds"},
    }
    plan = load_and_validate_variation_plan(FIXTURE)
    html = tmp_path / "rosey" / "designs" / "page" / "candidates" / "v1" / "index.html"
    html.parent.mkdir(parents=True)
    html.write_text("<html></html>", encoding="utf-8")
    results = [
        {
            "variation": 1,
            "title": "Direct",
            "rationale": "r",
            "directive": "d",
            "html": html,
            "png": None,
            "project_id": "p1",
            "run_id": "r1",
            "project_metadata_path": str(html.parent / "project-meta.json"),
        }
    ]
    path = write_candidates_metadata(tmp_path, "page", "brief text", design_ctx, plan, results)
    meta = json.loads(path.read_text(encoding="utf-8"))
    assert meta["pageSlug"] == "page"
    assert meta["winnerVariation"] is None
    assert meta["variations"][0]["html"].endswith("v1/index.html")
    assert meta["designSystem"]["designSystemId"] == "user:test-ds"


def test_generate_candidates_with_mock_client(tmp_path: Path):
    # Seed design system
    ds_dir = tmp_path / "rosey" / "design-system"
    ds_dir.mkdir(parents=True)
    design_md = ds_dir / "DESIGN.md"
    design_md.write_text("# Design\n", encoding="utf-8")
    checksum = hashlib.sha256(b"# Design\n").hexdigest()
    manifest = {
        "designSystemId": "user:mock-ds",
        "designPath": "rosey/design-system/DESIGN.md",
        "designChecksum": checksum,
    }
    designs = tmp_path / "rosey" / "designs"
    designs.mkdir(parents=True)
    (designs / "design-system.json").write_text(json.dumps(manifest), encoding="utf-8")

    plan = load_and_validate_variation_plan(FIXTURE)
    calls: list[tuple] = []
    states = {"run-1": 0, "run-2": 0, "run-3": 0}

    def fake_run(*args: str) -> str:
        calls.append(args)
        if args[:2] == ("project", "create"):
            n = len([c for c in calls if c[:2] == ("project", "create")])
            return json.dumps(
                {"project": {"id": f"proj-{n}"}, "conversationId": f"conv-{n}"}
            )
        if args[:2] == ("run", "start"):
            n = len([c for c in calls if c[:2] == ("run", "start")])
            return json.dumps({"runId": f"run-{n}"})
        if args[:2] == ("run", "info"):
            run_id = args[2]
            states[run_id] = states.get(run_id, 0) + 1
            status = "completed" if states[run_id] >= 1 else "running"
            return json.dumps({"status": status})
        if args[:2] == ("files", "list"):
            return json.dumps({"files": [{"name": "index.html", "kind": "html"}]})
        if args[:2] == ("files", "read"):
            return f"<html><body>{args[1]}</body></html>"
        if args[:2] == ("project", "delete"):
            return json.dumps({"ok": True})
        raise AssertionError(f"unexpected args: {args}")

    client = OpenDesignClient(run_fn=fake_run, daemon_url="http://127.0.0.1:9")

    # Bypass real daemon preflight
    client.preflight = lambda: (True, "")  # type: ignore[method-assign]

    result = generate_candidates(
        tmp_path,
        "mock-page",
        "Build a simple hero",
        plan,
        client=client,
        pause_s=0,
        skip_screenshots=True,
        sleep_fn=lambda _s: None,
    )
    assert result["page_slug"] == "mock-page"
    assert len(result["results"]) == 3
    for i in range(1, 4):
        html = tmp_path / "rosey" / "designs" / "mock-page" / "candidates" / f"v{i}" / "index.html"
        assert html.is_file()
    meta = json.loads(result["candidates_json"].read_text(encoding="utf-8"))
    assert len(meta["variations"]) == 3
