---
name: mash-a11y
description: "Runtime accessibility self-review for the user's own app on local or staging: axe-core plus a keyboard and screen-reader checklist and an optional Lighthouse accessibility signal. Refuses production. Never claims WCAG compliance. Manual invocation."
argument-hint: "[url:...] [target:local|staging] [path:/route] [mode:interactive|non-interactive]"
---

# Accessibility self-review

Act as a reviewer who records what axe-core, a person, and an optional Lighthouse accessibility score actually showed. Never claim the target is WCAG compliant, ASVS compliant, or OWASP-safe.

**Outcome:** one report under the mash-project-review contract. Automated violations are `Fail` rows with command output. Checks a person has not judged are `Blocked (needs human verify)`.

**Done:** every a11y row is terminal, the report matches the mash-project-review template, and chat has one `MASH_EVIDENCE` / `END_MASH_EVIDENCE` block per failed or blocked automated check, as that skill's evidence reference specifies.

**Read `references/phases.md` before Phase 0 and follow it.** Also read these mash-project-review references before Phase 0: `../mash-project-review/references/safety.md`, `../mash-project-review/references/status-vocabulary.md`, `../mash-project-review/references/evidence.md`, and `../mash-project-review/references/report-template.md`.

## Communication while using this skill

Caveman level, drop conditions, and what stays uncompressed are in the caveman rule.

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default. The manual checklist asks the person.
- `mode:non-interactive` — do not ask. Manual rows are `Blocked (needs human verify)`.

Strip the token first. Multiple mode tokens: stop and report the conflict.

## Argument Parsing

Honor the tokens defined by the mash-project-review skill: `target:`, `url:`, `port:`, `--port`, `path:`, `report:`, and `lease:held`.

`target:prod` and `target:production` are refusals. Stop before any browser or axe process.

`front:web-security`, `front:api-security`, and `front:performance` do not belong to this skill. Stop and tell the user to invoke that skill, or the mash-project-review skill for every front. `front:all` on a direct invocation: run this front only, and name the mash-project-review skill as the orchestrator.

This skill does not run ZAP and does not run a dependency audit.

## Boundaries

- **Contract.** Status strings, the report path, redaction, and production refusal come from the mash-project-review skill. Do not invent a second vocabulary.
- **Not mash-dogfood.** Dogfood's matrix may note focus, labels, and keyboard on a shipped journey. This skill is the tool-backed audit. Do not copy a dogfood report over this one.
- **Not a certification.** axe impact, a checklist note, and a Lighthouse accessibility score are signals. Never claim the target is WCAG compliant.
- **Browser.** Invoke the agent-browser skill for the page. Do not shell out to `npx` as a browser. Do not attach to the human's default Chrome profile.
- **Lighthouse.** One accessibility category, optional, through the chrome-devtools skill. Do not drive the page with that server. Do not start a second Lighthouse binary.
- **No fixes and no commits.** Record the next step. Do not edit the app.

## Artifact

When `report:` is present, update that file. Otherwise create `<repo-root>/.mash/project-review/<YYYY-MM-DD>-a11y-<slug>.md` using the mash-project-review filename rules. The front in the report is `a11y`.

When `lease:held` is absent, register a `project-review` run and acquire the workspace lease as the mash-project-review skill describes. Release it on every exit path. When `lease:held` is present, do not take another workspace lease.

## Phase order

Safety → prerequisites → serve → URL list → axe → optional Lighthouse → manual checklist → report.

The detail is in `references/phases.md`. The manual items are in `references/manual-checklist.md`.

Stop after the evidence blocks. Do not invoke the mash-work skill or the mash-pr skill.
