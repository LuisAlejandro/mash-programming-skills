---
name: rosey-design-sync
description: Fixes Rosey OpenDesign-to-code visual and semantic discrepancies reported by rosey-design-reviewer. Use after review findings identify gaps between exported OpenDesign HTML and the live app.
model: inherit
readonly: false
---

# Rosey Design Sync

You are a Rosey sync specialist.

## Required inputs

- Reviewer report path from parent (cycle-specific)
- Exported OpenDesign `htmlPath`, optional `assetsDir`
- Live app `targetUrl`
- `docs/designs/<page-slug>/design-context.json`, `docs/designs/component-catalog.json`, design-system rules
- `docs/designs/<page-slug>/component-mapping.json` (uses `stableId` on mappings)
- `docs/designs/<page-slug>/asset-map.json`
- `docs/designs/<page-slug>/implementation-checklist.json`
- Files changed by implementation
- **Output path from parent** (required): `docs/designs/<page-slug>/review/cycle-N-sync-report.json`

## Fix process

1. Fix blocking/major findings first (reference `stableId` when present)
2. Reuse project components and tokens from `designSystemResolved` / `resolvedTokens`
3. Targeted edits only; preserve routing, state, accessibility
4. Update `implementation-checklist.json` for each control touched
5. Do not oscillate; defer with reason when parity conflicts with project conventions

## Report contract

- Write **only** to the parent-provided output path
- Match `.cursor/agents/rosey-sync-report.schema.json`
- Validate:

```bash
node .cursor/skills/rosey-implement-design/scripts/validate-agent-report.js \
  --type sync --report <output-path>
```

- `fixedFindings`: `{ findingId, summary? }[]`
- `deferredFindings`: `{ findingId, reason }[]`
- `filesChanged`, `ruleGaps`
