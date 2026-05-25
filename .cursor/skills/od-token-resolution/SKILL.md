---
name: od-token-resolution
description: Extracts OpenDesign design tokens from exported HTML/CSS artifacts. Use for OpenDesign-to-code workflows before generating design-system rules or implementing HTML into app components.
---

# OpenDesign Token Resolution

## Overview

This skill resolves design tokens from OpenDesign exported artifacts. It is artifact-first: use an exported HTML file as source of truth, plus optional CSS/assets folders. Do not assume an OpenDesign MCP tool exists unless its schema has been verified in the current environment.

## Workflow

### 1. Inputs
Accept:
- `htmlPath`: required path to exported OpenDesign HTML.
- `cssPath` or `assetsDir`: optional supporting CSS/assets.
- `projectRoot`: optional target app root for token matching.

### 2. Extract
Run:

```bash
node .cursor/skills/od-token-resolution/scripts/resolve-tokens.js --html <htmlPath> --project-root <projectRoot> --css <cssPath> --assets-dir <assetsDir>
```

The script extracts:
- CSS custom properties.
- Colors, gradients, shadows.
- Font families, sizes, weights, line heights.
- Spacing values from inline styles, style blocks, and common utility classes.

### 3. Match
When `projectRoot` is provided, match extracted values to project CSS custom properties by exact normalized value. Utility classes and unresolved values remain in `failedTokens` for manual mapping in `.cursor/rules/od-design-system.mdc`.

Return `{ extractedTokens, resolvedTokens, failedTokens }` for `od-create-design-system` and `od-implement-design`.
