---
name: rosey-design-candidates
description: Generate three OpenDesign HTML design variations from a brief (Discord-free). Writes candidates under rosey/designs/PAGE_SLUG/candidates/ and emits DESIGN_CANDIDATES_HANDOFF. Use before picking a winner and running rosey-design-catalog / rosey-design-pipeline.
---

# Rosey Design Candidates

## Communication while using this skill

**Caveman lite** for assistant status prose while this skill runs: strip filler and hedging; keep articles and full sentences; stay professional and tight. Technical accuracy unchanged; quoted errors and code unchanged. Drop lite for security warnings, irreversible confirmations, ambiguous multi-step instructions, user confusion, or when the user asks for normal or long-form wording.

**Artifact boundary:** Caveman lite applies to chat and status prose, not HTML exports, screenshots, `candidates.json`, or handoff blocks.

## Overview

Local replacement for OpenClaw DesignCandidates generation (no Discord).

1. Ensure design system exists (`rosey/design-system/DESIGN.md` + `rosey/designs/design-system.json`).
2. Plan exactly **3** variation directives (agent step).
3. Run OpenDesign `example-web-prototype` plugin create → run → export → screenshot via Python scripts.
4. Emit `DESIGN_CANDIDATES_HANDOFF`.

Does **not** implement app UI. Downstream: human pick → `select_winner.py` → `rosey-design-catalog` (or full `rosey-design-pipeline`).

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default. May ask for brief / pageSlug.
- `mode:non-interactive` — no blocking questions; require brief + pageSlug (and paths) in args.

Strip the mode token before resolving inputs. If no mode token is present, set `INTERACTION_MODE=interactive`.

## Inputs

- `brief` or `briefFile`: design brief text or path to a text/markdown file (required).
- `pageSlug`: kebab-case page id (required; derive from brief title if interactive and missing).
- `repoRoot`: optional; default git root / workspace root.
- `winnerVariation` / `winner:vN`: **not** used here — selection is `select_winner.py` or `rosey-design-pipeline`.
- Optional: `model`, `daemonUrl` (default `http://127.0.0.1:7456`), `opendesignBin` (default `opendesign`), `skipScreenshots`.

## Prerequisites

**Working directory:** cwd is this skill's directory (the folder that contains this `SKILL.md`).

`install.sh` already provides `.venv/` as a symlink to the machine-global skill virtualenv at `~/.config/rosey/venvs/rosey-design-candidates`, built from `requirements.txt` with the Chromium build Playwright needs. Re-run `install.sh` to refresh it; the commands below are only needed when the symlink is absent.

```bash
# OpenDesign CLI + daemon (start outside the git repo)
(cd "${TMPDIR:-/tmp}" && opendesign --no-open &)
curl -s http://127.0.0.1:7456/api/agents >/dev/null

# Skill Python deps (screenshots)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
```

Optional: copy `.env.example` to `.env` in this skill directory and set `CURSOR_API_KEY` if OpenDesign runs need it (loaded by `opendesign_client.py`; never commit `.env`).

Repo must already have a published design system, or run **`rosey-design-system`** first so:

- `rosey/design-system/DESIGN.md` exists
- `rosey/designs/design-system.json` contains `designSystemId`

## Artifact layout

```text
rosey/designs/<page-slug>/
  candidates/
    candidates.json
    variation-plan.json
    v1/index.html
    v1/preview.png
    v1/project-meta.json
    v2/...
    v3/...
```

## Workflow

### 0. Hindsight gate

Follow [`rosey-hindsight`](../rosey-hindsight/SKILL.md). Record `HINDSIGHT: available|unavailable`.

### 1. Ensure design system

If `rosey/design-system/DESIGN.md` or `rosey/designs/design-system.json` is missing, invoke **`rosey-design-system`** with `mode:non-interactive` and wait until both exist. Do **not** nest Cursor SDK bootstraps.

### 2. Plan variations (agent)

Using [`references/variation-planner-prompt.md`](references/variation-planner-prompt.md), write:

`rosey/designs/<page-slug>/candidates/variation-plan.json`

Exactly 3 variations with `title`, `directive`, `rationale`. Set `"source": "agent"`.

Also write the brief to a temp or page file, e.g. `rosey/designs/<page-slug>/candidates/brief.txt`.

### 3. Generate candidates (scripts)

```bash
REPO="$(git rev-parse --show-toplevel)"
PYTHON=".venv/bin/python"
# fallback: python3 if venv missing and deps installed

"${PYTHON}" scripts/generate_candidates.py \
  --repo-root "${REPO}" \
  --page-slug "<page-slug>" \
  --brief-file "${REPO}/rosey/designs/<page-slug>/candidates/brief.txt" \
  --variation-plan "${REPO}/rosey/designs/<page-slug>/candidates/variation-plan.json"
```

Expect ~minutes × 3 OpenDesign runs. On failure, surface the error; do not invent HTML.

### 4. Present results

Show paths to `v1`/`v2`/`v3` HTML and PNG. In interactive mode, offer next steps: pick a winner (`select_winner.py`) or continue with **`rosey-design-pipeline`**.

### 5. Emit handoff

Always emit:

```text
DESIGN_CANDIDATES_HANDOFF
SUCCESS: true|false
PAGE_SLUG: <page-slug>
CANDIDATES_JSON: rosey/designs/<page-slug>/candidates/candidates.json
V1_HTML: rosey/designs/<page-slug>/candidates/v1/index.html
V2_HTML: rosey/designs/<page-slug>/candidates/v2/index.html
V3_HTML: rosey/designs/<page-slug>/candidates/v3/index.html
BLOCKERS: none | <reason>
END_DESIGN_CANDIDATES_HANDOFF
```

## Select winner (helper)

After the user chooses `vN`:

```bash
"${PYTHON}" scripts/select_winner.py \
  --repo-root "${REPO}" \
  --page-slug "<page-slug>" \
  --variation N
```

Copies into `rosey/designs/<page-slug>/source/index.html` (and preview.png when present) and sets `winnerVariation` in `candidates.json`.

## Tests

```bash
.venv/bin/python -m pytest tests -q
```

## Downstream

- Full chain: **`rosey-design-pipeline`**
- Manual: `select_winner.py` → **`rosey-design-catalog`** (`htmlPath` = `source/index.html`) → **`rosey-implement-design`** → **`rosey-design-iterator`** → **`rosey-lint`** → **`rosey-pr`**
