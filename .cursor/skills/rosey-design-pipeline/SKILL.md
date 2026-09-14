---
name: rosey-design-pipeline
description: Orchestrate the full local OpenDesign design pipeline — candidates, human winner pick, catalog, implement, visual iterator, lint, and PR. Discord-free. Pauses after candidates until winner vN is provided.
---

# Rosey Design Pipeline

## Communication while using this skill

**Caveman lite** for assistant status prose while this skill runs: strip filler and hedging; keep articles and full sentences; stay professional and tight. Technical accuracy unchanged; quoted errors and code unchanged. Drop lite for security warnings, irreversible confirmations, ambiguous multi-step instructions, user confusion, or when the user asks for normal or long-form wording.

**Artifact boundary:** Caveman lite applies to chat/status prose, not handoff blocks, HTML, screenshots, or PR URLs.

## Overview

End-to-end local pipeline (OpenClaw DesignCandidates + DesignPromote without Discord):

```text
candidates → [STOP: pick winner] → source/ → catalog → implement → iterator → lint → pr
```

This skill **orchestrates** existing skills. It does not reimplement OpenDesign or UI coding.

**Working directory:** when running a skill's scripts, cwd is that skill's directory (the folder that contains its `SKILL.md`).

## Interaction Mode

Parse `$ARGUMENTS` for at most one:

- `mode:interactive` — default. Ask for brief / pageSlug / winner when missing.
- `mode:non-interactive` — require `brief` (or briefFile), `pageSlug`, and either:
  - `winner:vN` / `winnerVariation` up front (full run), **or**
  - resume after candidates with only `pageSlug` + `winner:vN` (promote stages only).

If `mode:non-interactive` and candidates are not yet generated and winner is missing, stop with a blocker asking for `winner:vN` after candidates (do not auto-pick).

## Inputs

- `brief` / `briefFile`, `pageSlug` — required for candidates stage
- `winner:v1|v2|v3` or `winnerVariation:1|2|3` — required before promote stages
- Optional: `issue` (GitHub URL or `#n`), `model`, `skipCandidates` (reuse existing candidates), `skipPr`

## Hard pick gate

After `rosey-design-candidates` succeeds:

1. Show V1/V2/V3 HTML + PNG paths.
2. **Do not** run catalog/implement until a winner is chosen.
3. Interactive: ask which variation wins.
4. Non-interactive: require `winner:vN` in args; if absent, emit pipeline handoff with `BLOCKERS: waiting for winner:vN` and stop.

**Never auto-pick** a variation.

## Stages

### Stage A — Candidates

Invoke **`rosey-design-candidates`** with the same mode token and brief/pageSlug.

Wait for `DESIGN_CANDIDATES_HANDOFF` with `SUCCESS: true`.

### Stage B — Select winner

```bash
# cwd is the `rosey-design-candidates` skill directory (the folder that contains that skill's SKILL.md).
REPO="$(git rev-parse --show-toplevel)"
.venv/bin/python scripts/select_winner.py \
  --repo-root "${REPO}" \
  --page-slug "<page-slug>" \
  --variation N
```

Confirm `rosey/designs/<page-slug>/source/index.html` exists.

### Stage C — Catalog

Invoke **`rosey-design-catalog`** with `mode:non-interactive`:

- `htmlPath`: `rosey/designs/<page-slug>/source/index.html`
- `pageSlug`: same slug

Do not implement UI in this stage.

### Stage D — Implement

Invoke **`rosey-implement-design`** with `mode:non-interactive`:

- Same `htmlPath` / `pageSlug`
- Leave app dev server running for iterator
- Require `DESIGN_IMPLEMENT_HANDOFF` with `SUCCESS: true` and `TARGET_URL`

### Stage E — Iterator

Invoke agent `rosey-design-iterator` with `mode:non-interactive`, `PAGE_SLUG`, `TARGET_URL`, and HTML path. Stop servers when done. Accept `iterator-report.json` status `aligned` or `needs-targeted-pass`.

### Stage F — Lint

Invoke **`rosey-lint`** with `mode:non-interactive`. Require `LINT_HANDOFF` with `LINT_STATUS: pass`.

### Stage G — PR

Unless `skipPr` is set, invoke **`rosey-pr`** with `mode:non-interactive`. Treat this as approval to branch/commit/push/PR. Include `rosey/designs/<page-slug>/` artifacts in the commit.

## Final handoff

```text
DESIGN_PIPELINE_HANDOFF
SUCCESS: true|false
PAGE_SLUG: <page-slug>
WINNER_VARIATION: 1|2|3|
SOURCE_HTML: rosey/designs/<page-slug>/source/index.html
STAGES: candidates=pass|fail|skipped; pick=pass|waiting; catalog=...; implement=...; iterator=...; lint=...; pr=...
PR_URL: <url or none>
BLOCKERS: none | <reason>
END_DESIGN_PIPELINE_HANDOFF
```

## Prerequisites

Same as `rosey-design-candidates` (OpenDesign daemon, Playwright) plus:

In the `rosey-design-catalog` skill directory:

```bash
npm install
```

In the `rosey-implement-design` skill directory:

```bash
npm install
```

## Out of scope

- Discord voting / OpenClaw cron
- Auto-picking winners
- Full product behavior (use `rosey-brainstorm` after visual shell)
