---
name: mash-performance
description: "Runtime performance self-review for the user's own app on local or staging: one Lighthouse performance category through the chrome-devtools skill, plus a light k6 smoke when k6 is installed. Refuses production. Never claims a performance certification. Manual invocation."
argument-hint: "[url:...] [target:local|staging] [path:/route] [mode:interactive|non-interactive]"
---

# Performance self-review

Act as a reviewer who records what one Lighthouse performance category and one light k6 smoke actually measured. Never claim the target is WCAG compliant, ASVS compliant, or OWASP-safe.

**Outcome:** one report under the mash-project-review contract. A metric or a threshold that missed its stated band is a `Fail` row with the command and its real output. A missing tool is `Blocked (needs human verify)`.

**Done:** every performance row is terminal, the report matches the mash-project-review template, and chat has one `MASH_EVIDENCE` / `END_MASH_EVIDENCE` block per failed or blocked automated check, as that skill's evidence reference specifies.

**Read `references/phases.md` before Phase 0 and follow it.** Also read these mash-project-review references before Phase 0: `../mash-project-review/references/safety.md`, `../mash-project-review/references/status-vocabulary.md`, `../mash-project-review/references/evidence.md`, and `../mash-project-review/references/report-template.md`. Web-vital bands live in `references/web-vitals.md`. The k6 command lives in `references/k6-smoke.md`.

## Communication while using this skill

Caveman level, drop conditions, and what stays uncompressed are in the caveman rule.

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default. Staging confirmation may ask the user.
- `mode:non-interactive` — do not ask. An unconfirmed staging origin stops the run, as the mash-project-review safety reference specifies.

Strip the token first. Multiple mode tokens: stop and report the conflict.

## Argument Parsing

Honor the tokens defined by the mash-project-review skill: `target:`, `url:`, `port:`, `--port`, `path:`, `report:`, and `lease:held`.

`target:prod` and `target:production` are refusals. Stop before Lighthouse and before k6.

`front:a11y`, `front:web-security`, and `front:api-security` do not belong to this skill. Stop and tell the user to invoke that skill, or the mash-project-review skill for every front. `front:all` on a direct invocation: run this front only, and name the mash-project-review skill as the orchestrator.

This skill does not run axe-core, ZAP, or the API probe.

## Boundaries

- **Contract.** Status strings, the report path, redaction, and production refusal come from the mash-project-review skill.
- **Not the mash-performance-reviewer agent.** That persona reviews a diff for query and concurrency cost. This skill does not restate that persona and does not review the diff. A code-level performance question stays with that agent, invoked from the mash-qa skill.
- **Lighthouse.** One performance category, through the chrome-devtools skill. Do not drive the page with that server. Do not start a second Lighthouse binary.
- **k6 is a host tool.** One smoke of 2 virtual users for 10 seconds. When `k6` is not on `PATH`, `perf.k6.smoke` is `Blocked (needs human verify)` with the install link in `references/k6-smoke.md`. Do not substitute another load generator and do not download a binary into the app.
- **Not a capacity test.** Do not raise the virtual users or the duration. A request for a stress test or a soak is declined. The light smoke still runs.
- **No fixes and no commits.** Record the next step. Do not edit the app.

## Artifact

When `report:` is present, update that file. Otherwise create `<repo-root>/.mash/project-review/<YYYY-MM-DD>-performance-<slug>.md`. The front in the report is `performance`. The manual checklist section is "Not in this run."

When `lease:held` is absent, register a `project-review` run and acquire the workspace lease as the mash-project-review skill describes. Release it on every exit path.

## Phase order

Safety → serve → Lighthouse → k6 → report.

The detail is in `references/phases.md`.

Stop after the evidence blocks. Do not invoke the mash-work skill or the mash-pr skill.
