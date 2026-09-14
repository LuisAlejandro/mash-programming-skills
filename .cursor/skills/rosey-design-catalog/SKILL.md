---
name: rosey-design-catalog
description: Generates custom design system rules from OpenDesign exported HTML/CSS artifacts. Use when setting up OpenDesign-to-code workflows or mapping OpenDesign output to a project component system.
---

# Create OpenDesign Design System Rules

## Communication while using this skill

**Caveman full** for assistant status prose while this skill runs: drop articles, use fragments when clear, prefer short synonyms, and keep technical terms exact. Technical accuracy unchanged; quoted errors, code, and command output unchanged. Drop full for security warnings, irreversible confirmations, ambiguous multi-step instructions, user confusion, required input questions, or when the user asks for normal or long-form wording.

**Artifact boundary:** Caveman full applies to chat and status prose, not generated rules, catalog JSON, design context JSON, manifests, or validation output.

Generates design system rules mapping OpenDesign HTML/CSS into the app's framework, components, and tokens.

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default. May offer to invoke rosey-implement-design after Step 5.
- `mode:non-interactive` — scripted execution (for example DesignPromote). Strip the token before interpreting artifact inputs.

If multiple interaction mode tokens appear, stop and report the conflict.

### Non-Interactive Mode Rules

When `mode:non-interactive` is present (in `$ARGUMENTS` or the invoking prompt):

- Skip Step 6 (do not offer or invoke rosey-implement-design).
- End after Step 5 validation passes.
- Do not ask blocking questions; use conservative defaults for optional inputs.

## Overview

First skill in the OpenDesign-to-code flow. After completing in interactive mode, offer to invoke **rosey-implement-design**.

### Outputs

- the generated design-system rule in this IDE's rules tree — project conventions (includes active `pageSlug`; re-run when switching pages)
- `rosey/designs/component-catalog.json`
- `rosey/designs/<page-slug>/design-context.json`
- `rosey/designs/latest.json` — multi-page index (`pages`, `activePageSlug`)

## Prerequisites

**Working directory:** cwd is this skill's directory (the folder that contains this `SKILL.md`).

```bash
npm install
```

In the sibling `rosey-implement-design` skill directory:

```bash
npm install
```

## Workflow

### Step 1: Accept Artifact Inputs

- `htmlPath`: required exported OpenDesign HTML
- `pageSlug`: optional; derive from title or filename if absent
- `DESIGN.md`: required unless `--allow-missing-design` (debug). Auto-discover beside HTML, project root, or `rosey/design-system/DESIGN.md`
- `assetsDir`: optional; directory containing exported image/font assets (if not colocated with HTML)

If `rosey/designs/design-system.json` exists (from **rosey-design-system**), catalog warns when `DESIGN.md` changed since copy.

Do not call OpenDesign MCP tools unless descriptors are verified.

### Step 2: Analyze the Codebase

```bash
node scripts/scan-project-architecture.js --root <projectRoot>
```

### Step 3: Inspect OpenDesign Artifact

The generator runs token resolution, HTML serialization, and catalog building in one step. For debugging only:

- `rosey-token-resolution` with `--design`
- `rosey-implement-design/scripts/serialize-html.js --html <htmlPath>`

Serialized DOM lives in `design-context.json`; page-specific details live there, not in a page-specific rule file. Do not re-serialize unless HTML changed (checksum in context).

### Step 4: Generate Files

```bash
node scripts/generate-design-system.js \
  --html <htmlPath> --project-root <projectRoot> --page-slug <pageSlug> [--design <designPath>]
```

Optional: `--css <path[,path]>`, `--allow-missing-design`, `--assets-dir <assetsDir>`

Validate:

```bash
node scripts/validate-generated-files.js \
  --project-root <projectRoot> --page-slug <pageSlug>
```

Uses JSON schemas in `templates/rosey-*.schema.json`.

### Step 5: Component Catalog Contract

Catalog must follow `templates/rosey-component-catalog.schema.json`: path, exported name, `matches`, `props`. It is project-level at `rosey/designs/component-catalog.json`; per-page matching output is generated later by `rosey-implement-design`.

### Step 6: Offer rosey-implement-design

**Skip in `mode:non-interactive`.**

Ask whether to implement now. Pass `pageSlug`, `htmlPath`, and `assetsDir` (if applicable) to implement skill.
