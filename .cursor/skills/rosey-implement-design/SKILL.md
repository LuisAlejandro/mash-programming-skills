---
name: rosey-implement-design
description: Translates OpenDesign exported HTML/CSS artifacts into UI-layer app components (dummy data only) and runs Cursor subagent review, sync, and iteration. Use when implementing OpenDesign visual output into a codebase. Do not implement full page or component functionality here — the user invokes rosey-brainstorm separately when they want remaining behavior built.
---

# Implement OpenDesign

## Communication while using this skill

**Caveman lite** for all assistant prose while this skill runs: strip filler and hedging; keep articles and full sentences; stay professional and tight. Technical accuracy unchanged; quoted errors and code unchanged. Drop lite only for security warnings, irreversible confirmations, ambiguous multi-step instructions, user confusion, or when the user asks for normal or long-form wording.

**Artifact boundary:** Caveman lite applies to chat and status prose, not generated app code, parity reports, review reports, DOM/CSS diffs, screenshots, or structured validation output.

## Overview

This skill translates OpenDesign exported HTML/CSS into **UI-layer** app code with visual parity. It does **not** implement full page or component functionality.

OpenDesign source is artifact-first. Do not assume MCP tools exist. Use exported HTML as the baseline and map it into the project's native components.

## Scope: UI Layer Only

**In scope:** layout, typography, colors, spacing, assets, responsive structure, accessibility markup, and visual interaction affordances (hover/focus states, disabled appearance) needed for parity.

**Out of scope:** real data fetching, API integration, auth, business logic, form submission, persistence, routing guards, error handling beyond placeholder UI, and any behavior that requires backend or domain logic.

**Data layer:** fill lists, tables, charts, forms, and detail views with **dummy/static data** — hardcoded fixtures, mock objects, or placeholder strings. Wire props and state shapes loosely enough that real data can replace them later, but do not connect to live services.

**Next step (user-driven):** when Step 5 passes (`status: aligned`), this skill is complete. Do not continue into functionality work. The **user** invokes **rosey-brainstorm** when they want the remaining behavior designed and built (data flow, APIs, validation, edge cases).

## Prerequisites

Install skill dependencies once per machine:

```bash
npm install --prefix .cursor/skills/rosey-implement-design
npm install --prefix .cursor/skills/rosey-design-catalog
```

## Workflow

### Step 1: Gather Inputs

Require `htmlPath` for exported OpenDesign HTML. Optional inputs:

- `pageSlug`: required when multiple pages exist in `docs/designs/latest.json`
- `assetsDir`: exported image/font assets (only if not colocated with HTML)
- `targetRoute` or target component path
- `targetFile`: file being edited (import path suggestions)

Read when present (from `rosey-design-catalog`):

- `docs/designs/latest.json` (`activePageSlug`, `pages.<slug>.*`)
- `docs/designs/<page-slug>/design-context.json` (embedded `serialized` DOM — do not re-serialize unless HTML checksum changed)
- `docs/designs/component-catalog.json`
- `.cursor/rules/rosey-design-system.mdc`

Token fields on `design-context.json` (prefer top-level):

- `designSystemResolved`
- `resolvedTokens`
- `failedTokens`

### Step 2: Prepare Implementation

```bash
node .cursor/skills/rosey-implement-design/scripts/prepare-implementation.js \
  --project-root <projectRoot> \
  [--target-file <targetFile>] \
  [--page-slug <pageSlug>]
```

Pass `--page-slug <pageSlug>` only when overriding `docs/designs/latest.json` `activePageSlug`.

The prep script writes:

- `docs/designs/<page-slug>/asset-map.json` (always created, may be `{}`)
- `docs/designs/<page-slug>/component-mapping.json`
- `docs/designs/<page-slug>/implementation-checklist.json` (one row per `controlInventory` item)

Mappings use `stableId` (preferred) and numeric `controlInventory[].id`.

When `pageSlug` differs from `latest.json` `activePageSlug`, re-run **rosey-design-catalog** for that page so `.cursor/rules/rosey-design-system.mdc` references the correct context.

### Step 3: Translate to Project Conventions (UI Only)

Convert mapped DOM into native framework code. Preserve semantics, accessibility, responsive behavior, assets, and visual interaction hints.

Use **dummy data** for all dynamic content — no API calls, no real stores, no database queries. Example: a user table renders from a local `const users = [...]` array; a form's `onSubmit` is a no-op or logs to console.

Defer functional behavior for a later **rosey-brainstorm** session (user invokes when ready). Mark non-visual controls (e.g. submit handlers, search filtering) as `deferred` in the checklist with a note like `"functionality — rosey-brainstorm"`.

Track progress in `implementation-checklist.json`: mark each control `implemented`, `deferred`, or `not-applicable` with notes.

### Step 4: Start Dev Server

Use `design-context.json` → `architecture.scripts` (e.g. `dev`, `start`) from detected `package.json` files. Start the server, wait for readiness, capture the live `targetUrl` (include route when implementing a page).

### Step 5: Review / Sync / Iterate (required)

Create `docs/designs/<page-slug>/review/`.

**Run only the iterator subagent** (it delegates to reviewer and sync each cycle):

```text
/rosey-design-iterator
```

Pass: `htmlPath`, `assetsDir`, `pageSlug`, `targetUrl`, viewports (`1440x900`, `1024x768`, `390x844`), changed files, paths to `design-context.json`, `component-mapping.json`, `asset-map.json`, `implementation-checklist.json`, review directory.

**CRITICAL:** Step 5 must always run. Do not stop after Step 3 implementation.

Iterator must pass final gates before `status: aligned`:

```bash
node .cursor/skills/rosey-implement-design/scripts/validate-implementation-state.js \
  --project-root <projectRoot> --page-slug <pageSlug> \
  --require-checklist-complete --require-aligned
```

### Done: UI layer complete

When the iterator reports `status: aligned`, stop. This skill does not invoke **rosey-brainstorm** automatically.

Leave the implementation ready for a future functionality pass:

- Dummy data and deferred checklist items document what still needs real behavior
- The user invokes **rosey-brainstorm** when they want APIs, validation, business logic, and other non-visual work implemented

## Debugging

Use these lower-level commands only when the prep script or catalog state needs investigation.

Copy assets manually:

```bash
node .cursor/skills/rosey-implement-design/scripts/copy-assets.js --project-root <projectRoot> --page-slug <pageSlug>
```

Run component mapping manually:

```bash
node .cursor/skills/rosey-implement-design/scripts/component-mapping.js \
  --project-root <projectRoot> \
  --page-slug <pageSlug> \
  [--target-file <targetFile>]
```

Rebuild catalog/context when HTML changed:

```bash
node .cursor/skills/rosey-design-catalog/scripts/generate-design-system.js --html <htmlPath> --project-root <projectRoot> --page-slug <pageSlug>
```

Run all viewport parity reports:

```bash
node .cursor/skills/rosey-implement-design/scripts/run-parity-viewports.js \
  --project-root <projectRoot> --page-slug <pageSlug> \
  --baseline-url <baselineUrl> --target-url <targetUrl>
```

Merge parity into reviewer-shaped findings:

```bash
node .cursor/skills/rosey-implement-design/scripts/merge-parity-report.js \
  --project-root <projectRoot> --page-slug <pageSlug> \
  --baseline-url <baselineUrl> --target-url <targetUrl>
```

Validate iteration cycle artifacts:

```bash
node .cursor/skills/rosey-implement-design/scripts/validate-iteration-cycle.js \
  --project-root <projectRoot> --page-slug <pageSlug> --cycle 1
```

Rendered DOM + pixel diff (recommended):

```bash
npm install --prefix .cursor/skills/rosey-implement-design
npx --prefix .cursor/skills/rosey-implement-design playwright install chromium
```

Stop baseline server:

```bash
node .cursor/skills/rosey-implement-design/scripts/stop-baseline-server.js \
  --pid-file docs/designs/<page-slug>/review/baseline-server.pid
```
