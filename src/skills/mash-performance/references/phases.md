# Performance phases

Required read before Phase 0. Bands live in `references/web-vitals.md`. The k6 command lives in `references/k6-smoke.md`.

## Phase 0: Safety and report

Follow `../mash-project-review/references/safety.md`. Refuse production before Lighthouse and before k6. A refusal runs neither tool.

Create the temp directory when this invocation is not already inside an orchestrated run:

```bash
mktemp -d "${TMPDIR:-/tmp}/mash-project-review-XXXXXX"
```

Create or open the report from `../mash-project-review/references/report-template.md`. Rows start at `Pending`. Leave the manual checklist section as "Not in this run."

## Phase 1: Serve

Follow the serve rules in `../mash-project-review/references/safety.md`. Both checks need the resolved origin. If serve fails, set `perf.lighthouse.scan` and `perf.k6.smoke` to `Blocked (needs human verify)` and stop the tool phases.

The page URL is the origin plus the first `path:` token, or the origin itself when no path was given.

## Phase 2: Lighthouse

Read the chrome-devtools skill and follow it. Request one Lighthouse performance category for that page URL. Navigation on that server exists only to reach the audit URL. Do not click or fill.

Read `references/web-vitals.md` and file the rows it names.

- The chrome-devtools MCP server is missing, or that skill stops: `perf.lighthouse.scan`, `perf.lighthouse.lcp`, `perf.lighthouse.inp`, and `perf.lighthouse.cls` are `Blocked (needs human verify)`. Remediation: install Chrome DevTools MCP through the Mash Programming Skills installer. Do not run a second Lighthouse binary. Do not call `npx lighthouse`.
- The audit returns: `perf.lighthouse.scan` is `Pass`, meaning the category was retrieved. Record the performance score in the note. A score is a signal, not a certification.

Paste an evidence block for a `Fail` and for a blocked scan: the command and the metric excerpt or the stderr tail.

## Phase 3: k6

Read `references/k6-smoke.md` and follow it. Run it after Lighthouse so the smoke is not mixed into the lab audit.

- `k6` is not on `PATH`: `perf.k6.smoke` is `Blocked (needs human verify)` with that file's install link. Do not mark it `Skipped`.
- k6 finishes and its thresholds hold: `perf.k6.smoke` is `Pass`. Record the `http_req_failed` rate and the p95 duration from the summary.
- A threshold fails: `perf.k6.smoke` is `Fail`. Failed requests are `P1`. A duration miss with no failed requests is `P2`.

Paste the k6 command and the summary excerpt.

## Phase 4: Write the report

Update the report after each terminal row. Fill Failures, Blocked and skipped, and Final status.

A pass on a vital or on the smoke means that check's band held. It does not certify the app. Release the lease when this invocation acquired it. Stop.
