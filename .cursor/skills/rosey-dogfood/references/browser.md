# Browser

Required read before the first Phase 4 navigation. Drive a real browser through the **host's browser tools**. Never `agent-browser`, never `npx` for browser control, never Chrome DevTools MCP under another product name when the host already exposes a browser tool.

## Host contract

Match by capability, not by a host-specific name: navigate, lock/focus, accessibility snapshot, click, fill, screenshot, console/network inspection.

On Cursor, that is `cursor-ide-browser`. Discover the schema (`GetDynamicTools` / the host equivalent) before the first call. Typical loop:

1. `browser_tabs` list — reuse an open tab when it is already the app
2. `browser_navigate` to the scenario's URL
3. `browser_lock` with `action: "lock"` before a stretch of interactions
4. `browser_snapshot` for refs
5. `browser_click` / `browser_fill` / `browser_press_key` / `browser_select_option` as the journey requires
6. `browser_take_screenshot` into the OS temp dir from Phase 4
7. Console / network: host CDP or equivalent (`browser_cdp` `Runtime.evaluate` / log/network) — record errors in the report
8. `browser_lock` with `action: "unlock"` when Phase 4 is finished for this run, not after every scenario

If the host has no browser tool, stop and say this skill cannot run here. Do not shell out to Playwright or a downloaded CLI.

## Screenshot temp

Create one scratch directory per run:

```bash
mktemp -d "${TMPDIR:-/tmp}/rosey-dogfood-XXXXXX"
```

Write screenshots there. Never write them under the repo root. Copy a file into `rosey/dogfood/` only when embedding it in the report, and use a repo-relative path in the report.

## One scenario at a time

For each matrix row:

1. Navigate from a known entry URL (origin + route), not from leftover page state, unless the journey *is* a continuation (back button, re-entry).
2. Snapshot before each click/fill so refs are current.
3. Follow the flowchart to the true end state, including click-through from an in-app notification. External legs (OAuth, real email, payments, SMS) stop at `Blocked (needs human verify)`.
4. Judge Pass / Fail / Skipped / Blocked. Update the report before starting the next row.
5. Do not retry a Blocked scenario on this run.

Iframe content is not reachable through snapshot refs. If the journey lives inside an iframe the tool cannot see, mark the scenario `Blocked (needs human verify)` with that reason.

## Failures

A functional miss is `Fail`. Capture a screenshot in temp, copy it in only if it earns its place in the report, and fill the Failures section (symptom, expected, actual, evidence, suggested follow-up). Then continue the matrix.

Do not edit application code. Do not commit.
