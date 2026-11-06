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

1. Invoke the agent-browser skill. Run `agent-browser --version` and stop the browser path if a reported token is not the pin that skill names. Load the version-matched core guide with `agent-browser skills get core`. The bare command `agent-browser skills get` exits with "No skill name provided" and is not a guide load. A missing binary, a pin mismatch, or a failed guide load: set `a11y.browser` to `Blocked (needs human verify)` and quote that skill's install remediation (`npm install -g agent-browser@<pin>` and then `agent-browser install`). Do not shell out to `npx` as a browser. Do not switch tools. Do not guess a command the core guide does not list.
2. The page scan is `agent-browser a11y --json` from that core guide. The skill-local runner is only the fallback in Phase 3. Resolve it when the guide has no `a11y` command. The skill directory is the directory that contains this skill's `SKILL.md`. Dependencies install to `node_modules` beside that file, symlinked by the Mash installer to `~/.config/mash/node_modules/mash-a11y/node_modules`.

```bash
node "<skill-dir>/scripts/run_axe.mjs" --self-check
```

If `node` is missing, or `node_modules/axe-core` is missing, or the self-check exits non-zero, the fallback runner is `Blocked (needs human verify)`. Remediation: re-run the Mash Programming Skills installer so the skill dependency is installed, or run `npm install` in the skill directory of a source checkout. Do not `npx` a different axe package, and do not add axe-core to the app under review. A failed self-check does not block `agent-browser a11y` when that command is in the loaded guide.

A blocked prerequisite does not skip the manual checklist. Continue to later phases and mark the blocked automated rows. Do not invent a pass.

## Phase 2: Serve and routes

Follow the serve rules in `../mash-project-review/references/safety.md`. Claim `port`, `compose`, and `browser` when `lease:held` is absent. When `lease:held` is present, the orchestrator already holds them; still do not start a second server.

Build the URL list from `path:` tokens on the resolved origin. No paths:

- Interactive: ask once for the routes. The default offer is the homepage plus any route the user names.
- Non-interactive: homepage only. Record that the route list was unreviewed.

Deduplicate. Every URL stays on the resolved origin. Drop and report any URL that does not.

## Phase 3: axe-core

The pinned core guide documents an embedded axe-core audit, `agent-browser a11y --json`. That audit runs in the browser session, so it sees layout, contrast, and the page's scripts. Use it as the scan. Do not shell out to `npx`. Do not fetch the URL with curl and treat the response body as the rendered page.

Open a named session. Refuse a profile named `Default` and refuse auto-connect.

For each URL, and for widths 390 and 1440:

1. `agent-browser --session <name> set viewport 390 844` or `agent-browser --session <name> set viewport 1440 900`. `set viewport` is the command in the core guide (`agent-browser skills get core --full`). Setting the viewport can leave the tab on `about:blank`.
2. `agent-browser --session <name> open <absolute url>` after the viewport change.
3. `agent-browser --session <name> a11y --json`

If the guide has no viewport command, audit once at the session default and mark the width that was not captured `Blocked (needs human verify)` on `a11y.manual.reflow-390` or `a11y.manual.reflow-1440`.

Parse the JSON object in stdout. Ignore log lines before the first `{`. Read `data.axeVersion`, `data.violations`, and `data.incomplete`.

- No JSON, or the `a11y` command is absent from the loaded guide: use the fallback runner below once. If that also fails, `a11y.axe.scan` is `Blocked (needs human verify)` with the stderr tail.
- JSON present: `a11y.axe.scan` is `Pass`, meaning the scan finished. Record `data.axeVersion` in metadata.
- Each object in `data.violations` is a `Fail` row `a11y.axe.<id>`. Severity comes from `references/status-vocabulary.md` in the mash-project-review skill (`critical` → `P0`, `serious` → `P1`, `moderate` → `P2`, `minor` → `P3`). One row per rule id. Name every viewport where it failed.
- `data.incomplete` is not a pass. One row `a11y.axe.incomplete`, status `Blocked (needs human verify)`, listing those rule ids.
- Pass counts are a count, not a list of conforming rules. Do not write one Pass row per passing rule.
- `tags` that start with `wcag` go in the hint column only.

### Fallback runner

Use this only when the loaded core guide has no `a11y` command. Export `document.documentElement.outerHTML` with `agent-browser eval`. The core guide says to prefer `eval --stdin` when the expression contains quotes. Save the HTML in the temp directory. `--url` is the absolute page URL.

```bash
node "<skill-dir>/scripts/run_axe.mjs" --html "$HTML" --url "$PAGE_URL"
```

The runner is Mash skill tooling. It is not an app start command. Read the JSON between `AXE_JSON` and `END_AXE_JSON`. Exit 1, or no JSON, blocks `a11y.axe.scan`. Exit 0 or 2 means the fallback scan finished. Map `violations` the same way. The runner disables `color-contrast` because jsdom has no canvas, so a missing contrast violation on this path is not a pass. The manual contrast row is the contrast check. `jsdomUndecided` (`landmark-one-main`, `page-has-heading-one`) is a note on the scan row, not a Fail and not a blocked row.

Paste an evidence block, per the mash-project-review evidence reference, for the scan command and for each Fail. Include the JSON excerpt for that rule. Do not paste the HTML document.

ponytail: the embedded `a11y` audit is the scan because jsdom cannot measure contrast. The fallback runner still disables `color-contrast`. Do not add a second browser to get contrast back.

## Phase 4: Lighthouse accessibility signal

Attempt one Lighthouse accessibility category through the chrome-devtools skill. Navigation on that server exists only to reach the audit URL. Do not click or fill. Do not use the result as a dogfood journey.

- Missing chrome-devtools MCP server: `a11y.lighthouse` is `Blocked (needs human verify)`. Remediation: install Chrome DevTools MCP through the Mash Programming Skills installer. Do not run a second Lighthouse binary.
- The audit returns: `a11y.lighthouse` is `Pass` when the category score was retrieved. Record the score in the note. A score is a signal, not a conformance result.
- An audit finding that is not already an `a11y.axe.<rule id>` row becomes `a11y.lighthouse.<audit id>` at `P2`, as a `Fail`, with the audit's own text in the evidence block.

## Phase 5: Manual checklist

Read `references/manual-checklist.md`.

- Interactive: ask the person to perform the checks. Record `Pass` or `Fail` only with their confirmation and their note. A decline is `Blocked (needs human verify)`. A reflow row already blocked because the viewport could not be set stays blocked until the person actually checks that width.
- Non-interactive: every manual row is `Blocked (needs human verify)`, reason "manual check needs a person".

Observe keyboard, focus, and motion with the core guide's `press` and `eval`, then ask the person to confirm:

- `agent-browser --session <name> press Tab`, then `eval` of `document.activeElement.id`. Repeat. Focus that stays on one control is `a11y.manual.no-trap` Fail at `P1`, and `a11y.manual.keyboard-path` Fail when the rest of the journey cannot be reached.
- `eval` of `getComputedStyle(document.activeElement).outlineStyle`. A value of `none` with no other visible indicator is `a11y.manual.focus-visible` Fail.
- `eval` of `getComputedStyle(document.querySelector("p")).animationName`. A running animation and no `prefers-reduced-motion` rule is `a11y.manual.reduced-motion` Fail. `none` is `Skipped`, reason "nothing animates".
- At each width, `eval` of `document.documentElement.scrollWidth` and `clientWidth`. A horizontal overflow that covers the primary action fails the matching reflow row.

Do not mark a screen-reader row `Pass` because the accessibility tree looked plausible. The person runs VoiceOver, NVDA, or Orca. If none of those is available, the row is `Blocked (needs human verify)` and the remediation is to run one of them. The page shows no field error: `a11y.manual.errors-associated` is `Skipped` with that reason.

## Phase 6: Write the report

Update the report after each terminal row, not only at the end. Fill Failures, Blocked and skipped, Manual checklist, and Final status using the mash-project-review status vocabulary.

Emit evidence blocks in chat for each failed or blocked automated check. Release the lease when this invocation acquired it. Stop.
