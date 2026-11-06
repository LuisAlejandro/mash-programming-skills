---
name: mash-api-security
description: "Runtime API self-review for the user's own app on local or staging. Uses an OpenAPI document and two test accounts to check authentication, object access, mass assignment, rate limiting, verbose errors, and CORS, then npm audit or pip-audit. Refuses production. Never claims OWASP or ASVS compliance. Manual invocation."
argument-hint: "[url:...] [target:local|staging] [spec:<file>] [mode:interactive|non-interactive]"
---

# API security self-review

Act as a reviewer who records what an OpenAPI probe and the project's own dependency auditor actually reported. Never claim the target is WCAG compliant, ASVS compliant, or OWASP-safe.

**Outcome:** one report under the mash-project-review contract. Confirmed gaps are `Fail` rows with the command and its real output. A missing spec, account, or auditor is `Blocked (needs human verify)`. A check that does not apply is `Skipped`.

**Done:** every API row is terminal, the report matches the mash-project-review template, and chat has one `MASH_EVIDENCE` / `END_MASH_EVIDENCE` block per failed or blocked automated check, as that skill's evidence reference specifies.

**Read `references/phases.md` before Phase 0 and follow it.** Also read these mash-project-review references before Phase 0: `../mash-project-review/references/safety.md`, `../mash-project-review/references/status-vocabulary.md`, `../mash-project-review/references/evidence.md`, and `../mash-project-review/references/report-template.md`. Probe rules live in `references/checks.md`.

## Communication while using this skill

Caveman level, drop conditions, and what stays uncompressed are in the caveman rule.

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default. Staging confirmation may ask the user. Missing account variables: ask once for them to be exported in the shell, not pasted into chat.
- `mode:non-interactive` — do not ask. An unconfirmed staging origin stops the run. Missing account variables block only the checks that need them.

Strip the token first. Multiple mode tokens: stop and report the conflict.

## Argument Parsing

Honor the tokens defined by the mash-project-review skill: `target:`, `url:`, `port:`, `--port`, `spec:`, `report:`, and `lease:held`.

`target:prod` and `target:production` are refusals. Stop before the probe and before any audit.

`front:a11y`, `front:web-security`, and `front:performance` do not belong to this skill. Stop and tell the user to invoke that skill, or the mash-project-review skill for every front. `front:all` on a direct invocation: run this front only, and name the mash-project-review skill as the orchestrator.

This skill does not run axe-core, ZAP, Lighthouse, or k6.

## Boundaries

- **Contract.** Status strings, the report path, redaction, and production refusal come from the mash-project-review skill.
- **Not the mash-api-contract-reviewer agent.** That persona reviews a diff for breaking request and response changes. This skill does not restate that persona and does not review the diff. A contract question on a change stays with that agent, invoked from the mash-qa skill.
- **Not a pentest.** No password list, no injection string, no exploit payload, no attempt to bypass a login. The probe sends a missing credential, the other test user's id, documented extra JSON fields, one repeated request, a single malformed body, and one foreign `Origin`.
- **Not ASVS.** Do not assign an ASVS level. Names in the hint column are hints. The report is not an OWASP assessment.
- **Host tools only.** The probe script is skill-local Python. `npm audit` and `pip-audit` are the dependency auditors, using `../mash-web-security/references/dependency-audit.md`. Do not add a scanner binary. A missing auditor is `Blocked (needs human verify)` with the remediation in that file.
- **No fixes and no commits.** Record the next step. Do not edit the app.

## Artifact

When `report:` is present, update that file. Otherwise create `<repo-root>/.mash/project-review/<YYYY-MM-DD>-api-security-<slug>.md`. The front in the report is `api-security`. The manual checklist section is "Not in this run."

When `lease:held` is absent, register a `project-review` run and acquire the workspace lease as the mash-project-review skill describes. Release it on every exit path.

## Phase order

Safety → dependency audit → serve → OpenAPI probe → report.

Dependency audit does not need the server. A serve failure blocks the probe only. The detail is in `references/phases.md`.

Stop after the evidence blocks. Do not invoke the mash-work skill or the mash-pr skill.
