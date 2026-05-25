---
name: od-implement-design
description: Translates OpenDesign exported HTML/CSS artifacts into production-ready app components and runs Cursor subagent review, sync, and iteration. Use when implementing OpenDesign output into a codebase.
---

# Implement OpenDesign

## Overview

This skill translates OpenDesign exported HTML/CSS into production-ready app code with visual parity.

OpenDesign source is artifact-first. Do not assume MCP tools exist. Use exported HTML as the baseline and map it into the project's native components.

## Workflow

### Step 1: Gather Inputs
Require `htmlPath` for exported OpenDesign HTML. Optional inputs:
- `previewUrl`: OpenDesign preview URL.
- `assetsDir`: exported image/font assets.
- `targetRoute` or target component path.

Read `.cursor/od-design-context.json`, `.cursor/od-component-catalog.json`, and `.cursor/rules/od-design-system.mdc` when present.

### Step 2: Parse Artifact
Run:

```bash
node .cursor/skills/od-implement-design/scripts/serialize-html.js --html <htmlPath> --assets-dir <assetsDir> --out .cursor/od-serialized.json
```

Use the output as design context:
- normalized DOM tree
- style blocks and inline styles
- class inventory
- asset references
- control inventory

### Step 3: Component Mapping
Run:

```bash
node .cursor/skills/od-implement-design/scripts/component-mapping.js --serialized .cursor/od-serialized.json --project-root <projectRoot> --catalog .cursor/od-component-catalog.json --out .cursor/od-component-mapping.json
```

Mapping order:
1. Explicit catalog entries.
2. Semantic HTML tags and ARIA roles.
3. Project component names and prop interfaces.
4. Heuristics from class names and structure.

If confidence is low for a core component, ask the user before creating duplicate UI primitives.

### Step 4: Translate to Project Conventions
Convert mapped DOM into native framework code. Preserve semantics, accessibility attributes, responsive behavior, assets, and interaction hints. Reuse existing project components before creating new ones.

Before writing code, verify every item in the control inventory is planned. After writing code, mark each item implemented, deferred, or not applicable.

### Step 5: Start Dev Server
Ensure a local dev server is running and capture the live app URL.

### Step 6: Review, Sync, and Iterate
Create `.cursor/od-review/` for QA artifacts. If the parent does not already have a baseline URL, start the baseline server:

```bash
node .cursor/skills/od-implement-design/scripts/serve-artifact.js --html <htmlPath> --assets-dir <assetsDir> --port 0
```

Use the emitted `OD_ARTIFACT_URL` as the baseline. Compare it against the local app URL at default viewports `1440x900`, `1024x768`, and `390x844` unless the user specifies different viewports.

Use registered Cursor subagents from `.cursor/agents/`:
1. `/od-design-reviewer`: render the baseline HTML and target app, compare DOM/CSS and screenshots, report discrepancies.
2. `/od-design-sync`: apply targeted code fixes for reviewer findings.
3. `/od-design-iterator`: repeat review/sync up to 5 cycles or until aligned.

Pass each subagent the same protocol: `htmlPath`, optional `assetsDir`, target app URL, viewport list, changed files, `.cursor/od-serialized.json`, `.cursor/od-component-mapping.json`, and output report path under `.cursor/od-review/`.

**CRITICAL:** Steps 6 must always run. Do not stop after implementation.
