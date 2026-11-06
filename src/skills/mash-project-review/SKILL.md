---
name: mash-project-review
description: "Shared contract and orchestrator for a runtime self-review of the user's own app on local or staging. Parses the target, writes the report, and runs the mash-a11y and mash-web-security fronts. Refuses production. Never claims WCAG, ASVS, or OWASP compliance. Manual invocation."
argument-hint: "[front:all|a11y|web-security] [url:...] [target:local|staging] [path:/route] [mode:interactive|non-interactive]"
---

# Project review

Runtime self-review of the user's own app. This skill owns the shared contract. With `front:all` (the default) it runs both phase-1 fronts in one invocation and writes one report. Invoke the mash-a11y skill or the mash-web-security skill to run a single front.

**Outcome:** a durable report of observed checks and gaps. Tool output shows defects. It does not prove the absence of defects, and it is not a certification.

**Done:** every matrix row is `Pass`, `Fail`, `Skipped`, or `Blocked (needs human verify)`; the report matches `references/report-template.md`; chat carries a short verdict, the repo-relative report path, and one `MASH_EVIDENCE` / `END_MASH_EVIDENCE` block per failed or blocked automated check.

**Read `references/safety.md` before Phase 0 and follow it.** Safety, status strings, and evidence rules live in this skill's `references/` directory. Do not reconstruct them from memory.

## Communication while using this skill

Caveman level, drop conditions, and what stays uncompressed are in the caveman rule.

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default for direct chat invocation. Staging confirmation and the mash-a11y manual checklist may ask the user.
- `mode:non-interactive` — scripted or skill-to-skill execution. Do not ask blocking questions. A missing confirmation or a manual check becomes `Blocked (needs human verify)` or a stop, as `references/safety.md` specifies.

Strip the interaction mode token before interpreting remaining tokens. If no interaction mode token is present, set `INTERACTION_MODE=interactive`.

If multiple interaction mode tokens appear, stop and report the conflict.

## Argument Parsing

Parse `$ARGUMENTS` for these tokens. Strip each recognized token before interpreting the remainder.

| Token | Example | Effect |
| --- | --- | --- |
| `mode:interactive` | `mode:interactive` | Explicit default |
| `mode:non-interactive` | `mode:non-interactive` | No blocking questions |
| `front:all` | `front:all` | Run mash-a11y, then mash-web-security (default) |
| `front:a11y` | `front:a11y` | Run only the mash-a11y skill |
| `front:web-security` | `front:web-security` | Run only the mash-web-security skill |
| `target:local` | `target:local` | Local Make/Compose origin (default) |
| `target:staging` | `target:staging` | Explicit staging origin. Requires `url:` |
| `target:prod` | `target:prod` | Refused. Stop before any tool runs |
| `port:<n>` | `port:3000` | Local listen port |
| `--port PORT` | `--port 3000` | Same as `port:<n>` |
| `url:<http(s)://...>` | `url:https://staging.example.com` | Base URL |
| `path:<route>` | `path:/pricing` | Repeatable route for the mash-a11y skill. A path is a path on the origin, starting with `/` |

Conflicting `target:` tokens or conflicting `front:` tokens: stop and report the conflict. Any `target:prod` or `target:production` token: stop. Do not scan.

The remainder is not an intake window. Unrecognized tokens: ask once (interactive) or stop (non-interactive).

## Boundaries

- **This skill is the contract.** The mash-a11y skill and the mash-web-security skill follow it. They do not invent a second report format, status list, or evidence marker.
- **Not mash-qa.** Static review personas stay on diffs. This skill does not edit those agents and does not replace them.
- **Not mash-dogfood.** Dogfood is window-scoped journey QA of shipped pull requests. Do not copy a dogfood report into `.mash/project-review/`, and do not drive a week's pull requests from here.
- **No production target.** Phase 1 refuses production entirely. There is no read-mostly production mode.
- **No commits, pushes, or pull requests.** Findings are evidence for a later invocation of the mash-work skill. Do not patch the app to clear a row.
- **No second browser and no second Lighthouse.** Page capture goes through the agent-browser skill. The optional accessibility score goes through the chrome-devtools skill.
- **Missing tool.** The affected check is `Blocked (needs human verify)` with install remediation. Do not skip it silently and do not swap in an unapproved binary.

## Artifact Root

Reports live under `<repo-root>/.mash/project-review/`. Resolve `<repo-root>` with `git rev-parse --show-toplevel` the first time a report path is composed.

- **Filename:** `<YYYY-MM-DD>-<front>-<slug>.md`
- **Date:** the UTC date when the run starts.
- **Front:** `all`, `a11y`, or `web-security`.
- **Slug:** the base URL host, lowercased, with every run of non-alphanumeric characters collapsed to one `-`, trimmed. Before a URL exists, the slug is `local`.

Use repo-relative paths in the report. Do not also write `project-review-reports/` or `docs/`.

## Concurrent runs

Writing the report mutates the checkout. Register a run and hold the `workspace` lease before creating the report, per the mash-workspace skill. Release it on every exit path, including a refusal or a blocker. A refused lease stops the run; do not write the report anyway.

```bash
HELPER="<skills dir>/mash-workspace/scripts/workspace.py"
REPO="$(git rev-parse --show-toplevel)"
RUN=$(python3 "$HELPER" run start --workflow project-review --workspace "$REPO" --repo "$REPO" \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["run_id"])')
python3 "$HELPER" lease acquire --run "$RUN" --kind workspace --key "$REPO" --repo "$REPO"
```

Claim `port`, `compose`, and `browser` before using them, using the same helper and the same run id. Release with `run end` when the run finishes.

When this skill invokes a front, pass `lease:held` and `report:<repo-relative path>` so the front writes the orchestrated report and does not take a second workspace lease.

## Phase order

Safety → lease → checkpoint report → fronts → finalize → evidence in chat.

**Read a reference on phase entry.** `references/safety.md` before Phase 0. `references/report-template.md` before creating the report. `references/status-vocabulary.md` before judging a row. `references/evidence.md` before the chat handoff.

### Phase 0: Safety

Follow `references/safety.md`. Resolve target, origin, and slug. Refuse production before any request, scan, or audit. Interactive staging confirms the exact origin once. Create the temp directory:

```bash
mktemp -d "${TMPDIR:-/tmp}/mash-project-review-XXXXXX"
```

Screenshots, saved HTML, and scanner output stay in that directory. Do not commit it.

### Phase 1: Checkpoint

Instantiate `references/report-template.md` at the report path. Every planned row starts at `Pending`. Fill metadata and the safety banner before the first tool runs.

### Phase 2: Fronts

Pass the resolved tokens: interaction mode, `target:`, `url:` when known, `port:` when known, each `path:`, `lease:held`, and `report:<path>`.

- `front:all` — invoke the mash-a11y skill, wait until its rows are terminal, then invoke the mash-web-security skill.
- `front:a11y` — invoke only the mash-a11y skill.
- `front:web-security` — invoke only the mash-web-security skill.

A front that stops on a safety refusal stops the run. A front row that is `Blocked (needs human verify)` does not stop the other front.

### Phase 3: Finalize

Update the final status from `references/status-vocabulary.md`. A `P0` or `P1` Fail means `not ready`. Any other Fail, or any blocked row, means `ready with caveats`. All `Pass` or `Skipped` is still `ready with caveats`, because the matrix is non-exhaustive.

Never claim the target is WCAG compliant, ASVS compliant, or OWASP-safe.

Emit the verdict, the repo-relative report path, and the evidence blocks. Then release the workspace lease. Stop. Do not invoke the mash-work skill, the mash-qa skill, or the mash-pr skill.
