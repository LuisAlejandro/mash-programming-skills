# Accessibility phases

Required read before Phase 0. The skill body owns the outcome, the boundaries, and the phase order. This file owns the steps.

## Phase 0: Safety and report

Follow `../mash-project-review/references/safety.md`. Refuse production before any tool runs. Resolve the origin and the slug.

Create the temp directory when this invocation is not already inside an orchestrated run that created one. Reuse the orchestrator's temp directory when it was passed in the conversation. Do not commit that directory.

```bash
mktemp -d "${TMPDIR:-/tmp}/mash-project-review-XXXXXX"
```

Create or open the report from `../mash-project-review/references/report-template.md`. Rows start at `Pending`.

## Phase 1: Prerequisites

1. Invoke the agent-browser skill. Run its version check (`agent-browser --version` must report the pin that skill names) and load its guide with `agent-browser skills get`. A missing binary or a pin mismatch: set `a11y.browser` to `Blocked (needs human verify)` and quote that skill's install remediation. Do not shell out to `npx` as a browser. Do not switch tools.
2. Resolve the axe runner. The skill directory is the directory that contains this skill's `SKILL.md` (the installed copy or the source checkout). Dependencies install to `node_modules` beside that file, symlinked by the Mash installer to `~/.config/mash/node_modules/mash-a11y/node_modules`.

```bash
node "<skill-dir>/scripts/run_axe.mjs" --self-check
```

If `node` is missing, or `node_modules/axe-core` is missing, or the self-check exits non-zero: set `a11y.axe.scan` to `Blocked (needs human verify)`. Remediation: re-run the Mash Programming Skills installer so the skill dependency is installed, or run `npm install` in the skill directory of a source checkout. Do not `npx` a different axe package, and do not add axe-core to the app under review.

A blocked prerequisite does not skip the manual checklist. Continue to later phases and mark the blocked automated rows. Do not invent a pass.

## Phase 2: Serve and routes

Follow the serve rules in `../mash-project-review/references/safety.md`. Claim `port`, `compose`, and `browser` when `lease:held` is absent. When `lease:held` is present, the orchestrator already holds them; still do not start a second server.

Build the URL list from `path:` tokens on the resolved origin. No paths:

- Interactive: ask once for the routes. The default offer is the homepage plus any route the user names.
- Non-interactive: homepage only. Record that the route list was unreviewed.

Deduplicate. Every URL stays on the resolved origin. Drop and report any URL that does not.

## Phase 3: axe-core

For each URL, invoke the agent-browser skill. Open a named session. Refuse a profile named `Default` and refuse auto-connect.

Set the viewport to 390px wide and capture, then to 1440px wide and capture, using the viewport command the pinned guide documents. If the guide has no viewport command, capture once at the session default and mark `a11y.manual.reflow-390` or `a11y.manual.reflow-1440` (the one not captured) `Blocked (needs human verify)`.

Export `document.documentElement.outerHTML` with the page-evaluation command the pinned guide documents. Save each capture in the temp directory. A guessed flag that the guide does not list is not a capture. If the guide has no evaluation command, mark `a11y.axe.scan` `Blocked (needs human verify)` and stop the automated axe phase. Do not fetch the URL with curl and treat the response body as the rendered page.

Run the runner on the captured file. `--url` is the absolute page URL, not a `file:` URL.

```bash
node "<skill-dir>/scripts/run_axe.mjs" --html "$HTML" --url "$PAGE_URL"
```

Read the JSON between `AXE_JSON` and `END_AXE_JSON`.

- The runner is Mash skill tooling. It is not an app start command. Do not install it inside the app.
- Exit 1, or no JSON: `a11y.axe.scan` is `Blocked (needs human verify)` with the stderr tail.
- Exit 0 or 2: `a11y.axe.scan` is `Pass`, meaning the scan finished. Record the axe version in metadata.
- Each object in `violations` is a `Fail` row `a11y.axe.<rule id>`. Severity comes from `references/status-vocabulary.md` in the mash-project-review skill (`critical` → `P0`, `serious` → `P1`, `moderate` → `P2`, `minor` → `P3`). One row per rule id. Name every viewport where it failed.
- `incomplete` is not a pass. One row `a11y.axe.incomplete`, status `Blocked (needs human verify)`, listing those rule ids.
- `jsdomUndecided` lists rules jsdom cannot decide even when the element is present (`landmark-one-main`, `page-has-heading-one`). Name them in the `a11y.axe.scan` note. They are not a Fail and they are not a blocked row. A real missing heading is still caught when axe reports it as a violation, and the manual checklist still covers the primary journey.
- `disabledRules` includes `color-contrast`. jsdom has no canvas, so the runner does not execute that rule and a missing contrast violation is not a pass. The manual contrast row is the contrast check.
- `passCount` is a count, not a list of conforming rules. Do not write one Pass row per passing rule.
- WCAG tags on a violation go in the hint column only.

Paste an evidence block, per the mash-project-review evidence reference, for the scan command and for each Fail. Include the runner command and the JSON excerpt for that rule. Do not paste the HTML document.

ponytail: the runner executes axe-core inside jsdom on HTML captured elsewhere. It does not layout, paint, or run the page's scripts, and it leaves `color-contrast` disabled. The upgrade path is a real-browser axe run still captured through the agent-browser skill, if incompletes or the disabled contrast rule hide defects the checklist cannot see.

## Phase 4: Lighthouse accessibility signal

Attempt one Lighthouse accessibility category through the chrome-devtools skill. Navigation on that server exists only to reach the audit URL. Do not click or fill. Do not use the result as a dogfood journey.

- Missing chrome-devtools MCP server: `a11y.lighthouse` is `Blocked (needs human verify)`. Remediation: install Chrome DevTools MCP through the Mash Programming Skills installer. Do not run a second Lighthouse binary.
- The audit returns: `a11y.lighthouse` is `Pass` when the category score was retrieved. Record the score in the note. A score is a signal, not a conformance result.
- An audit finding that is not already an `a11y.axe.<rule id>` row becomes `a11y.lighthouse.<audit id>` at `P2`, as a `Fail`, with the audit's own text in the evidence block.

## Phase 5: Manual checklist

Read `references/manual-checklist.md`.

- Interactive: ask the person to perform the checks. Record `Pass` or `Fail` only with their confirmation and their note. A decline is `Blocked (needs human verify)`. A reflow row already blocked because the viewport could not be set stays blocked until the person actually checks that width.
- Non-interactive: every manual row is `Blocked (needs human verify)`, reason "manual check needs a person".

Do not mark a screen-reader row `Pass` because the accessibility tree looked plausible. The person runs VoiceOver, NVDA, or Orca.

## Phase 6: Write the report

Update the report after each terminal row, not only at the end. Fill Failures, Blocked and skipped, Manual checklist, and Final status using the mash-project-review status vocabulary.

Emit evidence blocks in chat for each failed or blocked automated check. Release the lease when this invocation acquired it. Stop.
