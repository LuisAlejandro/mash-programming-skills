# Browser

Required read before the first Phase 4 navigation. Drive the page through agent-browser. Open a named session, use fresh refs, and record a screenshot plus console and network evidence.

If agent-browser is missing, mark the journey `Blocked` and give the install remediation. Do not shell out to `npx` as a browser. Do not use Chrome DevTools MCP or CUA Driver for the page. Do not attach to the human's default Chrome profile. Refuse a profile named `Default` and refuse auto-connect.

## Session

1. Start a named session. The unnamed session is the shared `default` session, so a forgotten name collides with every other agent.
2. Snapshot before each click or fill so refs are current.
3. Keep screenshot, console, and network evidence.
4. Credentials do not appear in prompts, reports, or repository files.

## Screenshot temp

Create one scratch directory per run:

```bash
mktemp -d "${TMPDIR:-/tmp}/mash-dogfood-XXXXXX"
```

Write screenshots there. Never write them under the repo root. Copy a file into `.mash/dogfood/` only when embedding it in the report, and use a repo-relative path in the report.

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
