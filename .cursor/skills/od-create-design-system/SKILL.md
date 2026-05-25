---
name: od-create-design-system
description: Generates custom design system rules from OpenDesign exported HTML/CSS artifacts. Use when setting up OpenDesign-to-code workflows or mapping OpenDesign output to a project component system.
---

# Create OpenDesign Design System Rules

## Overview

This skill is the **first** in the OpenDesign-to-code flow. After completing it, **offer to invoke the od-implement-design skill**.

It generates design system rules tailored to the project. The workflow maps OpenDesign exported HTML/CSS into the app's framework, component library, and tokens.

### Rule Files
- `.cursor/rules/od-design-system.mdc`: Shared project conventions (framework, component paths, styling approach, OpenDesign integration flow).
- `.cursor/rules/od-ds-<page-slug>.mdc`: Page-specific overrides (color mapping, component mapping, font requirements, responsive strategy).
- `.cursor/od-component-catalog.json`: Component inventory and matching hints for HTML-to-component translation.
- `.cursor/od-design-context.json`: Extracted OpenDesign artifact context and token inventory.

## Workflow

### Step 1: Accept Artifact Inputs
Ask for or infer:
- `htmlPath`: required exported OpenDesign HTML file.
- `previewUrl`: optional OpenDesign preview URL.
- `assetsDir`: optional exported assets directory.
- `pageSlug`: optional name for page overlay; derive from HTML title or file name if absent.

Do not call OpenDesign MCP tools unless their descriptors have been verified.

### Step 2: Analyze the Codebase
Run `scripts/scan-project-architecture.js --root <projectRoot>` to detect framework, styling approach, component directories, token files, routing, and asset locations.

### Step 3: Inspect OpenDesign Artifact
Run:
- `od-token-resolution` on the HTML artifact.
- `scripts/extract-tokens.js --html <htmlPath>` for artifact-local colors, typography, shadows, spacing, and class names.
- `od-implement-design/scripts/serialize-html.js --html <htmlPath>` for DOM structure and control inventory.

### Step 4: Generate Files
Prefer the deterministic generator:

```bash
node .cursor/skills/od-create-design-system/scripts/generate-design-system.js --html <htmlPath> --project-root <projectRoot> --page-slug <pageSlug>
```

Optional flags: `--preview-url <url>`, `--assets-dir <dir>`, and `--css <path[,path]>`.

The generator writes:
- `.cursor/od-artifact.json`
- `.cursor/od-component-catalog.json`
- `.cursor/od-design-context.json`
- `.cursor/rules/od-design-system.mdc`
- `.cursor/rules/od-ds-<page-slug>.mdc`

Validate the output:

```bash
node .cursor/skills/od-create-design-system/scripts/validate-generated-files.js --project-root <projectRoot> --page-slug <pageSlug>
```

### Step 5: Component Catalog Contract
The component catalog must follow `templates/od-component-catalog.schema.json`. It includes component path, exported name, probable HTML matches, and prop hints. Use explicit catalog matches first during implementation; heuristics are fallback only.

### Step 6: Generate Rules
Write `.cursor/rules/od-design-system.mdc` and `.cursor/rules/od-ds-<page-slug>.mdc`. Rules must say:
- OpenDesign source is exported HTML/CSS.
- Prefer existing project components from `.cursor/od-component-catalog.json`.
- Preserve DOM semantics and accessibility attributes.
- Keep generated code idiomatic to the detected framework.
- Compare implementation against rendered baseline HTML, not a guessed MCP screenshot.

### Step 7: Offer to Invoke od-implement-design
Ask the user if they want to implement an OpenDesign element now that the rules are set.
