#!/usr/bin/env python3
"""Generate OpenDesign HTML candidates into rosey/designs/<slug>/candidates/."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from opendesign_client import OUTPUT_CONTRACT, OpenDesignClient
from paths import (NUM_VARIATIONS, candidate_html_path, candidate_preview_path,
                   candidate_project_meta_path, candidate_variation_dir,
                   candidates_dir, candidates_json_path,
                   design_system_design_md, design_system_manifest_path,
                   rel_to_repo, variation_plan_path)
from screenshot_html import screenshot_html
from variation_plan import load_and_validate_variation_plan

logger = logging.getLogger("generate_candidates")

PAUSE_BETWEEN_VARIATIONS = 30
MAX_DESIGN_SYSTEM_PROMPT_CHARS = 12000


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def slugify_project_name(slug: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", slug.strip()).strip("-")
    return safe or "design"


def make_opendesign_project_name(slug: str, variation: int) -> str:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"RoseyCandidates-{slugify_project_name(slug)}-{ts}-V{variation}"


def load_design_system_context(repo_root: Path) -> dict:
    design_path = design_system_design_md(repo_root)
    manifest_path = design_system_manifest_path(repo_root)
    if not design_path.is_file():
        raise FileNotFoundError(
            f"Missing {design_path}. Run rosey-design-system before generating candidates."
        )
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Missing {manifest_path}. Run rosey-design-system before generating candidates."
        )
    content = design_path.read_text(encoding="utf-8")
    checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    design_system_id = manifest.get("designSystemId")
    if not design_system_id or not isinstance(design_system_id, str):
        raise RuntimeError(
            f"Missing designSystemId in {manifest_path}. Re-run rosey-design-system."
        )
    return {
        "design_path": str(design_path.relative_to(repo_root)),
        "checksum": checksum,
        "content": content,
        "manifest": manifest,
        "design_system_id": design_system_id.strip(),
    }


def format_design_system_prompt_section(ctx: dict) -> str:
    content = ctx["content"]
    truncated = len(content) > MAX_DESIGN_SYSTEM_PROMPT_CHARS
    body = content[:MAX_DESIGN_SYSTEM_PROMPT_CHARS] if truncated else content
    note = (
        f"\n[DESIGN.md truncated to {MAX_DESIGN_SYSTEM_PROMPT_CHARS} characters for prompt size; "
        "follow tokens and rules from the excerpt.]\n"
        if truncated
        else "\n"
    )
    ds_id = ctx["design_system_id"]
    return (
        "DESIGN SYSTEM CONSTRAINT (hard requirement — do not invent a new visual language):\n"
        f"- Repository design system path: {ctx['design_path']}\n"
        f"- OpenDesign design system id (attached to this project): {ds_id}\n"
        f"- Checksum: {ctx['checksum']}\n"
        "- The project is bound to this design system via --design-system; treat it as the primary source.\n"
        "- Respect tokens, typography, spacing, components, tone, and accessibility from DESIGN.md.\n"
        f"{note}\n"
        "<DESIGN.md>\n"
        f"{body}\n"
        "</DESIGN.md>\n"
    )


def write_variation_project_metadata(
    path: Path,
    *,
    variation: int,
    repo_root: Path,
    brief: str,
    design_ctx: dict,
    variation_item: dict,
    proj_name: str,
    variation_plan: dict,
    page_slug: str,
) -> None:
    meta = {
        "source": "rosey-design-candidates",
        "slug": page_slug,
        "variation": variation,
        "projectName": proj_name,
        "repoPath": str(repo_root),
        "instructionExcerpt": brief[:500],
        "designSystemId": design_ctx["design_system_id"],
        "designChecksum": design_ctx["checksum"],
        "designPath": design_ctx["design_path"],
        "variationTitle": variation_item.get("title"),
        "variationDirective": variation_item.get("directive"),
        "variationRationale": variation_item.get("rationale"),
        "variationPlanner": {
            "source": variation_plan.get("source"),
            "surface": variation_plan.get("surface"),
            "plannerAgent": variation_plan.get("plannerAgent"),
            "plannerModel": variation_plan.get("plannerModel"),
        },
        "skill": "web-prototype",
        "outputContract": "single index.html",
        "skipDiscoveryBrief": True,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def write_candidates_metadata(
    repo_root: Path,
    page_slug: str,
    brief: str,
    design_ctx: dict,
    variation_plan: dict,
    results: list[dict],
) -> Path:
    out_path = candidates_json_path(repo_root, page_slug)
    meta = {
        "generatedAt": datetime.now().isoformat(),
        "repoRoot": str(repo_root),
        "pageSlug": page_slug,
        "brief": brief,
        "winnerVariation": None,
        "designSystem": {
            "designSystemId": design_ctx["design_system_id"],
            "designPath": design_ctx["design_path"],
            "checksum": design_ctx["checksum"],
            "manifest": design_ctx.get("manifest") or {},
        },
        "variationPlanner": {
            "source": variation_plan.get("source"),
            "surface": variation_plan.get("surface"),
            "plannerAgent": variation_plan.get("plannerAgent"),
            "plannerModel": variation_plan.get("plannerModel"),
        },
        "variations": [
            {
                "variation": r["variation"],
                "title": r["title"],
                "rationale": r.get("rationale"),
                "directive": r.get("directive"),
                "html": rel_to_repo(repo_root, r["html"]),
                "png": rel_to_repo(repo_root, r["png"]) if r.get("png") else None,
                "projectId": r.get("project_id"),
                "runId": r.get("run_id"),
                "projectMetadataPath": (
                    rel_to_repo(repo_root, Path(r["project_metadata_path"]))
                    if r.get("project_metadata_path")
                    else None
                ),
            }
            for r in results
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    logger.info("Wrote candidates metadata: %s", out_path)
    return out_path


def generate_candidates(
    repo_root: Path,
    page_slug: str,
    brief: str,
    variation_plan: dict,
    *,
    client: OpenDesignClient,
    model: str | None = None,
    pause_s: float = PAUSE_BETWEEN_VARIATIONS,
    skip_screenshots: bool = False,
    sleep_fn=None,
) -> dict:
    sleep = sleep_fn or time.sleep
    design_ctx = load_design_system_context(repo_root)
    design_system_id = design_ctx["design_system_id"]

    cand_root = candidates_dir(repo_root, page_slug)
    cand_root.mkdir(parents=True, exist_ok=True)
    plan_path = variation_plan_path(repo_root, page_slug)
    plan_path.write_text(json.dumps(variation_plan, indent=2), encoding="utf-8")

    ok, reason = client.preflight()
    if not ok:
        raise RuntimeError(reason)

    base_prompt = brief.strip() + "\n\n" + format_design_system_prompt_section(design_ctx)
    planned = variation_plan["variations"]
    if len(planned) != NUM_VARIATIONS:
        raise ValueError(f"Expected {NUM_VARIATIONS} variations, got {len(planned)}")

    results: list[dict] = []
    created_ids: list[str] = []
    try:
        for i, variation_item in enumerate(planned, 1):
            directive = variation_item["directive"]
            title = variation_item["title"]
            proj_name = make_opendesign_project_name(page_slug, i)
            var_dir = candidate_variation_dir(repo_root, page_slug, i)
            var_dir.mkdir(parents=True, exist_ok=True)
            meta_path = candidate_project_meta_path(repo_root, page_slug, i)
            write_variation_project_metadata(
                meta_path,
                variation=i,
                repo_root=repo_root,
                brief=brief,
                design_ctx=design_ctx,
                variation_item=variation_item,
                proj_name=proj_name,
                variation_plan=variation_plan,
                page_slug=page_slug,
            )
            created = client.create_project(
                proj_name,
                design_system_id=design_system_id,
                metadata_json_path=meta_path,
            )
            pid = created["project_id"]
            created_ids.append(pid)
            conv_id = created.get("conversation_id")
            full_prompt = f"{base_prompt}\n\nDesign direction: {directive}\n\n{OUTPUT_CONTRACT}"
            run_id = client.run_until_complete(
                pid,
                full_prompt,
                conversation_id=conv_id,
                model=model,
                sleep_fn=sleep,
            )
            html_dest = candidate_html_path(repo_root, page_slug, i)
            client.export_html(pid, html_dest)
            png_dest = candidate_preview_path(repo_root, page_slug, i)
            if skip_screenshots:
                png_dest = None
            else:
                screenshot_html(html_dest, png_dest)

            results.append(
                {
                    "variation": i,
                    "title": title,
                    "rationale": variation_item.get("rationale"),
                    "directive": directive,
                    "project_id": pid,
                    "run_id": run_id,
                    "project_metadata_path": str(meta_path),
                    "html": html_dest,
                    "png": png_dest,
                }
            )
            if i < len(planned) and pause_s > 0:
                logger.info("Pausing %ss before next variation...", pause_s)
                sleep(pause_s)
    except Exception:
        for pid in created_ids:
            client.delete_project(pid)
        raise

    meta_path = write_candidates_metadata(
        repo_root, page_slug, brief, design_ctx, variation_plan, results
    )
    return {
        "candidates_json": meta_path,
        "results": results,
        "page_slug": page_slug,
        "design_system_id": design_system_id,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate OpenDesign design candidates")
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--page-slug", required=True)
    parser.add_argument("--brief-file", required=True, type=Path)
    parser.add_argument("--variation-plan", required=True, type=Path)
    parser.add_argument("--daemon-url", default="http://127.0.0.1:7456")
    parser.add_argument("--opendesign-bin", default="opendesign")
    parser.add_argument("--model", default=None)
    parser.add_argument("--pause-seconds", type=float, default=PAUSE_BETWEEN_VARIATIONS)
    parser.add_argument("--skip-screenshots", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    setup_logging(args.verbose)
    repo_root = args.repo_root.resolve()
    brief = args.brief_file.read_text(encoding="utf-8")
    variation_plan = load_and_validate_variation_plan(args.variation_plan)
    # Prefer agent source label when present
    if not variation_plan.get("source") or variation_plan["source"] == "planner":
        variation_plan["source"] = "agent"

    client = OpenDesignClient(
        opendesign_bin=args.opendesign_bin,
        daemon_url=args.daemon_url,
    )
    try:
        result = generate_candidates(
            repo_root,
            args.page_slug,
            brief,
            variation_plan,
            client=client,
            model=args.model,
            pause_s=args.pause_seconds,
            skip_screenshots=args.skip_screenshots,
        )
    except Exception as exc:
        logger.error("%s", exc)
        return 1

    print(f"CANDIDATES_JSON={result['candidates_json']}")
    for r in result["results"]:
        print(f"V{r['variation']}_HTML={r['html']}")
        if r.get("png"):
            print(f"V{r['variation']}_PNG={r['png']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
