---
name: mash-web-security
description: "Runtime web and dependency self-review for the user's own app on local or staging: an OWASP ZAP baseline plus npm audit or pip-audit when a manifest exists. Refuses production. Never claims OWASP or ASVS compliance. Manual invocation."
argument-hint: "[url:...] [target:local|staging] [mode:interactive|non-interactive]"
---

# Web security self-review

Act as a reviewer who records what an OWASP ZAP baseline and the project's own dependency auditor actually reported. Never claim the target is WCAG compliant, ASVS compliant, or OWASP-safe.

**Outcome:** one report under the mash-project-review contract. Alerts and vulnerable dependencies are `Fail` rows with command output. A missing scanner is `Blocked (needs human verify)`. A missing manifest is `Skipped`.

**Done:** every web-security row is terminal, the report matches the mash-project-review template, and chat has one `MASH_EVIDENCE` / `END_MASH_EVIDENCE` block per failed or blocked automated check, as that skill's evidence reference specifies.

**Read `references/phases.md` before Phase 0 and follow it.** Also read these mash-project-review references before Phase 0: `../mash-project-review/references/safety.md`, `../mash-project-review/references/status-vocabulary.md`, `../mash-project-review/references/evidence.md`, and `../mash-project-review/references/report-template.md`. ZAP flags live in `references/zap-baseline.md`. Audit commands live in `references/dependency-audit.md`.

## Communication while using this skill

Caveman level, drop conditions, and what stays uncompressed are in the caveman rule.

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default. Staging confirmation may ask the user.
- `mode:non-interactive` — do not ask. An unconfirmed staging origin stops the run, as the mash-project-review safety reference specifies.

Strip the token first. Multiple mode tokens: stop and report the conflict.

## Argument Parsing

Honor the tokens defined by the mash-project-review skill: `target:`, `url:`, `port:`, `--port`, `report:`, and `lease:held`.

`target:prod` and `target:production` are refusals. Stop before ZAP and before any audit.

`front:a11y` does not belong to this skill. Stop and tell the user to invoke the mash-a11y skill, or the mash-project-review skill for both fronts. `front:all` on a direct invocation: run this front only, and name the mash-project-review skill as the orchestrator for both.

This skill does not run axe-core and does not run Lighthouse.

## Boundaries

- **Contract.** Status strings, the report path, redaction, and production refusal come from the mash-project-review skill.
- **Not the mash-security-reviewer agent.** That persona reviews a diff. This skill runs tools against a local or staging origin and against the lockfiles on disk.
- **Not a pentest.** No authenticated deep scan, no API fuzzing, no exploit payload, no attempt to bypass a login. An auth wall is `Blocked (needs human verify)`.
- **Not ASVS.** Do not assign an ASVS level. OWASP Top 10 names in the hint column are hints, and only when the alert clearly matches. The report is not an OWASP assessment.
- **ZAP is a host tool.** When `zap-baseline.py` and the documented container command are both unavailable, the web rows are `Blocked (needs human verify)` with the install remediation in `references/zap-baseline.md`. Do not substitute another scanner.
- **No fixes and no commits.** Record the next step. Do not edit the app.

## Artifact

When `report:` is present, update that file. Otherwise create `<repo-root>/.mash/project-review/<YYYY-MM-DD>-web-security-<slug>.md`. The front in the report is `web-security`. The manual checklist section is "Not in this run."

When `lease:held` is absent, register a `project-review` run and acquire the workspace lease as the mash-project-review skill describes. Release it on every exit path.

## Phase order

Safety → dependency audit → serve → ZAP baseline → report.

Dependency audit does not need the server. A serve failure blocks ZAP only. The detail is in `references/phases.md`.

Stop after the evidence blocks. Do not invoke the mash-work skill or the mash-pr skill.
