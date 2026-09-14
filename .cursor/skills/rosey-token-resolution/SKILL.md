---
name: rosey-token-resolution
description: Extracts OpenDesign design tokens from exported HTML/CSS artifacts. Use for OpenDesign-to-code workflows before generating design-system rules or implementing HTML into app components.
---

# OpenDesign Token Resolution

## Communication while using this skill

**Caveman ultra** for assistant status prose while this skill runs: abbreviate routine workflow words, strip conjunctions where safe, use arrows for causality, and keep one word when one word is enough. Technical accuracy unchanged; token names, CSS values, code symbols, quoted errors, JSON fields, and command output unchanged. Drop ultra for security warnings, ambiguous input requirements, user confusion, or when the user asks for normal or long-form wording.

**Output boundary:** Caveman ultra applies to chat/status prose, not extracted token JSON, design-system mappings, failed-token lists, or validation output.

## Overview

Resolves design tokens from OpenDesign exported artifacts. Artifact-first: exported HTML is source of truth. Do not assume OpenDesign MCP unless schema verified.

## Workflow

**Working directory:** cwd is this skill's directory (the folder that contains this `SKILL.md`).

### 1. Inputs

- `htmlPath`: required
- `designPath`: optional `DESIGN.md` (auto-inferred)
- `cssPath` or `assetsDir`: optional
- `projectRoot`: optional for project token matching

### 2. Extract

```bash
node scripts/resolve-tokens.js \
  --html <htmlPath> --project-root <projectRoot> [--design <designPath>] [--require-design] \
  --css <cssPath> --assets-dir <assetsDir>
```

### 3. Match

With `projectRoot`, match extracted values to project CSS variables. With `DESIGN.md`, map colors via `designSystemResolved` (`mapped` / `unmapped`).

Unresolved values go to `failedTokens` for the generated design-system rule in this IDE's rules tree.

Returns `{ extractedTokens, designSystem, designSystemResolved, resolvedTokens, failedTokens }`.

**rosey-design-catalog** copies these onto `design-context.json` as top-level `designSystemResolved`, `resolvedTokens`, and `failedTokens` (also nested under `tokens`).
